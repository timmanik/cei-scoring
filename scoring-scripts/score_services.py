"""
Score cloud services using AWS Bedrock models with tool use for supplemental documentation.

Supports multiple models:
- Claude Sonnet 4
- Claude Opus 4.1
- Claude Sonnet 4.5
- Llama 3.3 70B Instruct

Features:
- AWS Bedrock API with bearer token authentication
- Tool use for fetching documentation when model lacks confidence
- Multi-model scoring with separate output files
- Retry logic with exponential backoff
"""

import os
from dotenv import load_dotenv
import json
import time
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import custom utilities
from utils.model_config import get_model_config, get_all_model_names, get_file_safe_name
from utils.bedrock_client import BedrockClient
from utils.tool_definitions import get_tool_definitions, create_tool_result_message
from utils.tool_handlers import process_tool_use_requests, should_use_tools
from utils.response_parser import (
    parse_score_response,
    is_tool_use_response,
    get_response_message,
    extract_tool_requests
)

load_dotenv()


def load_ground_truth_examples(ground_truth_file):
    """Load and format ground truth examples for few-shot learning."""
    with open(ground_truth_file, 'r') as f:
        ground_truth = json.load(f)

    examples_text = "\n\n**Example Scores:**\n"

    # Group examples by category
    iaas_examples = []
    paas_examples = []
    saas_examples = []

    for service, data in ground_truth['ground_truth'].items():
        if data['category'] == 'IaaS':
            iaas_examples.append((service, data))
        elif data['category'] == 'PaaS':
            paas_examples.append((service, data))
        elif data['category'] in ['SaaS', 'High-PaaS/SaaS']:
            saas_examples.append((service, data))

    # Add IaaS examples
    examples_text += "\n**IaaS Examples (1.00-2.99):**\n"
    for service, data in iaas_examples[:2]:  # Take first 2
        avg_score = sum(data['expected_range']) / 2
        examples_text += f"- {service} ({data['provider']}): Expected score ~{avg_score:.1f}\n"
        examples_text += f"  Raw virtual machines/compute instances where user manages OS, applications, security\n"

    # Add PaaS examples
    examples_text += "\n**PaaS Examples (3.00-7.99):**\n"
    for service, data in paas_examples[:2]:  # Take first 2
        avg_score = sum(data['expected_range']) / 2
        examples_text += f"- {service} ({data['provider']}): Expected score ~{avg_score:.1f}\n"
        examples_text += f"  Managed database/platform services with shared responsibility\n"

    # Add SaaS examples
    examples_text += "\n**SaaS Examples (8.00-10.00):**\n"
    for service, data in saas_examples[:2]:  # Take first 2
        avg_score = sum(data['expected_range']) / 2
        examples_text += f"- {service} ({data['provider']}): Expected score ~{avg_score:.1f}\n"
        examples_text += f"  Fully managed API/application services requiring minimal technical setup\n"

    # Add output format
    examples_text += "\n\n**Required JSON Output Format:**\n```json\n"
    examples_text += """{
  "service_name": "ServiceName",
  "provider": "AWS|Azure|GCP",
  "category": "Brief service description",
  "properties": {
    "scores": {
      "infrastructure_management": {
        "score": 0.00
      },
      "operational_maintenance": {
        "score": 0.00
      },
      "technical_skills": {
        "score": 0.00
      },
      "pricing_model": {
        "score": 0.00
      },
      "security_compliance": {
        "score": 0.00
      },
      "scalability_control": {
        "score": 0.00
      },
      "business_continuity": {
        "score": 0.00
      }
    }
  },
  "summary": "Overall classification and reasoning"
}```"""

    return examples_text


def build_system_prompt():
    """Build system prompt for the scoring task."""
    return [{
        "text": (
            "You are a cloud architecture expert who scores cloud services on a "
            "Cloud Elevation Index from 1.00 (pure IaaS) to 10.00 (pure SaaS). "
            "Score each service across 7 criteria using two decimal places. "
            "Base your scores on the service's primary function and typical user experience. "
            "Always respond with valid JSON in the exact format shown in examples.\n\n"
            "If you are not confident about a service or lack detailed information, "
            "you can use the available tools to search official documentation. "
            "This is especially helpful for newer, less common, or recently updated services."
        )
    }]


def build_initial_user_message(prompt_file, ground_truth_file):
    """Build the initial user message with prompt and examples."""
    with open(prompt_file) as f:
        prompt_data = json.load(f)

    # Get the initial prompt text
    initial_text = prompt_data['contents'][0]['parts'][0]['text']

    # Add examples
    examples_text = load_ground_truth_examples(ground_truth_file)

    return initial_text + examples_text


def setup_logging(log_file):
    """Setup logging for raw LLM responses."""
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a'
    )
    return logging.getLogger(__name__)


def score_service_with_tools(
    service_name: str,
    provider: str,
    model_id: str,
    model_config: Dict[str, Any],
    bedrock_client: BedrockClient,
    base_conversation: List[Dict[str, Any]],
    logger: logging.Logger,
    use_tools: bool = True,
    max_tool_iterations: int = 3,
    max_retries: int = 3
) -> Optional[float]:
    """
    Score a single service with tool use support and retry logic.

    Args:
        service_name: Name of the cloud service
        provider: Cloud provider (AWS, Azure, GCP)
        model_id: Bedrock model ID
        model_config: Model configuration dict
        bedrock_client: BedrockClient instance
        base_conversation: Base conversation history
        logger: Logger instance
        use_tools: Whether to enable tool use
        max_tool_iterations: Maximum tool use iterations
        max_retries: Maximum retry attempts

    Returns:
        float: Score (1.00-10.00) or None if all attempts fail
    """
    print(f"Scoring {service_name} ({provider})...")

    for attempt in range(max_retries):
        try:
            # Build request message
            user_prompt = f"Please score {service_name} for {provider}"

            # Initialize conversation with base messages
            messages = base_conversation.copy()
            messages.append({
                "role": "user",
                "content": [{"text": user_prompt}]
            })

            # Configure tools (only if model supports them)
            tool_config = None
            if use_tools and model_config.get('supports_tools', False) and should_use_tools(service_name, provider):
                tool_config = {"tools": get_tool_definitions()}
                logger.info(f"Tool config enabled for {service_name}")
            else:
                logger.info(f"Tool config disabled for {service_name} (use_tools={use_tools}, supports_tools={model_config.get('supports_tools', False)})")

            # Configure inference parameters
            inference_config = {
                "temperature": model_config['temperature'],
                "maxTokens": model_config['max_tokens']
            }

            # Tool use iteration loop
            tool_iterations = 0
            while tool_iterations < max_tool_iterations:
                # Call model
                response = bedrock_client.converse(
                    model_id=model_id,
                    messages=messages,
                    system=build_system_prompt(),
                    inference_config=inference_config,
                    tool_config=tool_config
                )

                # Log response
                logger.info(f"=== SERVICE: {service_name} ({provider}) - ATTEMPT {attempt + 1}, ITER {tool_iterations + 1} ===")
                logger.info(f"RESPONSE: {json.dumps(response, indent=2)}")
                logger.info("=== END RESPONSE ===\n")

                # Check if model wants to use tools
                if is_tool_use_response(response):
                    tool_iterations += 1
                    print(f"  → Tool use requested (iteration {tool_iterations}/{max_tool_iterations})")

                    # Add assistant's message to conversation
                    messages.append(get_response_message(response))

                    # Extract and execute tools
                    tool_requests = extract_tool_requests(response)
                    tool_results = process_tool_use_requests(tool_requests)

                    # Log tool execution
                    logger.info(f"Tool results: {json.dumps(tool_results, indent=2)}")

                    # Add tool results to conversation
                    messages.append(create_tool_result_message(tool_results))

                    # Continue loop to get final answer
                    continue

                # Got final answer - parse score
                score = parse_score_response(response)

                if score is None:
                    raise Exception("Failed to parse score from response")

                print(f"  → Score: {score}")
                return score

            # Max tool iterations reached
            raise Exception(f"Maximum tool use iterations ({max_tool_iterations}) reached")

        except Exception as e:
            print(f"  → Attempt {attempt + 1} failed: {type(e).__name__}: {str(e)}")

            if attempt == max_retries - 1:  # Last attempt
                print(f"  → All {max_retries} attempts failed for {service_name}")
                return None
            else:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"  → Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    return None


def main():
    parser = argparse.ArgumentParser(
        description='Score cloud services using AWS Bedrock models with tool use support'
    )
    parser.add_argument(
        '--input',
        default='../config/extracted_services.ndjson',
        help='Input NDJSON file with services (default: ../config/extracted_services.ndjson)'
    )
    parser.add_argument(
        '--output-dir',
        default='../results/scores',
        help='Output directory for score files (default: ../results/scores)'
    )
    parser.add_argument(
        '--prompt',
        default='../config/simple_prompt.json',
        help='Prompt configuration file (default: ../config/simple_prompt.json)'
    )
    parser.add_argument(
        '--ground-truth',
        default='../config/ground_truth.json',
        help='Ground truth examples file (default: ../config/ground_truth.json)'
    )
    parser.add_argument(
        '--models',
        nargs='+',
        default=['claude-sonnet-4.5'],
        choices=get_all_model_names() + ['all'],
        help='Models to use for scoring (default: claude-sonnet-4.5)'
    )
    parser.add_argument(
        '--use-tools',
        action='store_true',
        default=True,
        help='Enable tool use for documentation lookup (default: True)'
    )
    parser.add_argument(
        '--no-tools',
        dest='use_tools',
        action='store_false',
        help='Disable tool use'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )

    args = parser.parse_args()

    # Handle 'all' models selection
    if 'all' in args.models:
        selected_models = get_all_model_names()
    else:
        selected_models = args.models

    # Create output directories
    os.makedirs(args.output_dir, exist_ok=True)
    logs_dir = os.path.join(args.output_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Initialize Bedrock client
    try:
        bedrock_client = BedrockClient(region_name=args.region)
        print(f"✓ Bedrock client initialized (region: {args.region})")
    except ValueError as e:
        print(f"✗ Error: {e}")
        print("Please set AWS_BEARER_TOKEN_BEDROCK in your .env file")
        return

    # Build base conversation
    print(f"Loading prompt from: {args.prompt}")
    print(f"Loading examples from: {args.ground_truth}")

    initial_message = build_initial_user_message(args.prompt, args.ground_truth)
    base_conversation = [
        {
            "role": "user",
            "content": [{"text": initial_message}]
        },
        {
            "role": "assistant",
            "content": [{
                "text": (
                    "I understand. I'll score cloud services using those 7 criteria on a "
                    "1.00-10.00 scale, where lower scores indicate more user responsibility "
                    "(IaaS-like) and higher scores indicate more provider responsibility "
                    "(SaaS-like). I'm ready to score services accordingly. If I need more "
                    "information about a service, I'll use the available tools to search "
                    "official documentation."
                )
            }]
        }
    ]

    # Load services to score
    services = []
    with open(args.input, 'r') as f:
        for line in f:
            if line.strip():
                services.append(json.loads(line))

    print(f"\nFound {len(services)} services to score")
    print(f"Selected models: {', '.join(selected_models)}")
    print(f"Tool use: {'Enabled' if args.use_tools else 'Disabled'}\n")

    # Score with each model
    for model_name in selected_models:
        print(f"\n{'='*60}")
        print(f"Scoring with {model_name}")
        print(f"{'='*60}\n")

        # Get model configuration
        model_config = get_model_config(model_name)
        model_id = model_config['id']
        score_field = model_config['score_field']

        # Generate timestamped output filename
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        file_safe_model_name = get_file_safe_name(model_name)
        output_file = f'{args.output_dir}/{timestamp}-{file_safe_model_name}.ndjson'
        log_file = f'{logs_dir}/{timestamp}-{file_safe_model_name}-responses.log'

        # Setup logging
        logger = setup_logging(log_file)
        logger.info(f"=== SCORING SESSION STARTED: {datetime.now()} ===")
        logger.info(f"Model: {model_name} ({model_id})")
        logger.info(f"Input file: {args.input}")
        logger.info(f"Output file: {output_file}")
        logger.info(f"Tool use: {args.use_tools}")

        print(f"Output: {output_file}")
        print(f"Log: {log_file}\n")

        # Score each service
        results = []
        for i, service in enumerate(services, 1):
            print(f"Progress: {i}/{len(services)}")

            score = score_service_with_tools(
                service_name=service['service_name'],
                provider=service['provider'],
                model_id=model_id,
                model_config=model_config,
                bedrock_client=bedrock_client,
                base_conversation=base_conversation,
                logger=logger,
                use_tools=args.use_tools
            )

            # Create result
            result = {
                "provider": service['provider'],
                "service_name": service['service_name'],
                score_field: score
            }
            if service.get('service_alias'):
                result["service_alias"] = service['service_alias']

            results.append(result)

            # Save progress every 10 services
            if i % 10 == 0:
                with open(output_file, 'w') as f:
                    for r in results:
                        if r[score_field] is not None:
                            f.write(json.dumps(r) + '\n')
                successful = sum(1 for r in results if r[score_field] is not None)
                print(f"Progress saved: {successful} scores")

            # Rate limiting
            time.sleep(1)

        # Final save
        with open(output_file, 'w') as f:
            for r in results:
                if r[score_field] is not None:
                    f.write(json.dumps(r) + '\n')

        successful = sum(1 for r in results if r[score_field] is not None)
        print(f"\n{model_name}: {successful}/{len(services)} services scored successfully")

        # Log session end
        logger.info(f"=== SCORING SESSION COMPLETED: {datetime.now()} ===")
        logger.info(f"Successfully scored: {successful}/{len(services)} services")

    print(f"\n{'='*60}")
    print("All models completed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
