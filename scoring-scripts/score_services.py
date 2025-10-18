from portkey_ai import Portkey
import os
from dotenv import load_dotenv
import json
import time
import argparse
import logging
from datetime import datetime

load_dotenv()

# Initialize Portkey client
client = Portkey(
    api_key=os.getenv("PORTKEY_API_KEY"),
    virtual_key=os.getenv("PORTKEY_VIRTUAL_KEY_AWS"),
    aws_session_token=""
)

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

def load_conversation_history(prompt_file, ground_truth_file):
    """Load conversation history and inject ground truth examples."""
    with open(prompt_file) as f:
        prompt_data = json.load(f)
    
    # Load ground truth examples
    examples_text = load_ground_truth_examples(ground_truth_file)
    
    messages = []
    for content in prompt_data.get('contents', []):
        role = 'assistant' if content['role'] == 'model' else content['role']
        text = content['parts'][0]['text']
        
        # Inject examples into the first user message
        if role == 'user' and not messages:
            text += examples_text
        
        messages.append({"role": role, "content": text})
    
    return messages

def setup_logging(log_file):
    """Setup logging for raw LLM responses."""
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a'
    )
    return logging.getLogger(__name__)

def score_service(service_name, provider, conversation_history, logger, max_retries=3):
    """Score a single service with retry logic."""
    print(f"Scoring {service_name} ({provider})...")
    
    for attempt in range(max_retries):
        try:
            # Add new prompt to conversation
            messages = conversation_history + [{"role": "user", "content": f"Please score {service_name} for {provider}"}]
            
            # Get response from Claude via Portkey
            response = client.chat.completions.create(
                model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                max_tokens=8192,
                temperature=0.0,
                messages=messages
            )
            
            response_text = response.choices[0].message.content
            
            # Log raw response to file
            logger.info(f"=== SERVICE: {service_name} ({provider}) - ATTEMPT {attempt + 1} ===")
            logger.info(f"RAW RESPONSE:\n{response_text}")
            logger.info("=== END RAW RESPONSE ===\n")
            
            # Debug: Print raw response
            print(f"  → Attempt {attempt + 1}: Raw response length: {len(response_text) if response_text else 0}")
            
            if not response_text or len(response_text.strip()) == 0:
                raise Exception("Empty response from Portkey")
            
            # Parse JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                if json_end == -1:
                    json_text = response_text[json_start:].strip()
                else:
                    json_text = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON object in the response
                json_start = response_text.find('{')
                if json_start == -1:
                    raise Exception("No JSON object found in response")
                
                # Find the matching closing brace
                brace_count = 0
                json_end = json_start
                for i, char in enumerate(response_text[json_start:], json_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                json_text = response_text[json_start:json_end].strip()
            
            if not json_text:
                raise Exception("No JSON content found in response")
            
            score_data = json.loads(json_text)
            
            # Calculate average score
            if "properties" in score_data and "scores" in score_data["properties"]:
                scores = score_data["properties"]["scores"]
            elif "scores" in score_data:
                scores = score_data["scores"]
            else:
                raise Exception("Cannot find scores in response")
            
            # Extract scores, handling both with and without justification
            score_values = []
            for category in scores:
                if isinstance(scores[category], dict):
                    if 'score' in scores[category]:
                        score_values.append(float(scores[category]['score']))
                    else:
                        raise Exception(f"Missing 'score' field in category {category}")
                else:
                    # If it's just a number
                    score_values.append(float(scores[category]))
            
            if len(score_values) != 7:
                raise Exception(f"Expected 7 scores, got {len(score_values)}")
            
            final_score = round(sum(score_values) / len(score_values), 2)
            
            print(f"  → Score: {final_score}")
            return final_score
            
        except Exception as e:
            print(f"  → Attempt {attempt + 1} failed: {type(e).__name__}: {str(e)}")
            
            if attempt == max_retries - 1:  # Last attempt
                print(f"  → All {max_retries} attempts failed for {service_name}")
                # Print environment variables for debugging (without revealing sensitive data)
                print(f"  → PORTKEY_API_KEY set: {'Yes' if os.getenv('PORTKEY_API_KEY') else 'No'}")
                print(f"  → PORTKEY_VIRTUAL_KEY_AWS set: {'Yes' if os.getenv('PORTKEY_VIRTUAL_KEY_AWS') else 'No'}")
                return None
            else:
                print(f"  → Retrying in 2 seconds...")
                time.sleep(2)  # Wait before retry

def main():
    parser = argparse.ArgumentParser(description='Score cloud services using simplified prompt with ground truth examples')
    parser.add_argument('--input', default='config/extracted_services.ndjson', help='Input NDJSON file with services (default: config/extracted_services.ndjson)')
    parser.add_argument('--output', help='Output NDJSON file for scores (default: auto-generated with timestamp)')
    parser.add_argument('--prompt', default='config/simple_prompt.json', help='Prompt configuration file (default: config/simple_prompt.json)')
    parser.add_argument('--ground-truth', default='config/ground_truth.json', help='Ground truth examples file (default: config/ground_truth.json)')
    parser.add_argument('--log-file', help='Log file for raw LLM responses (default: auto-generated with timestamp)')
    
    args = parser.parse_args()
    
    # Generate timestamped output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        model_name = 'claude-3-5'
        args.output = f'scores/{timestamp}-{model_name}.ndjson'
    elif not args.output.startswith('scores/'):
        # Ensure output goes to scores directory
        args.output = f'scores/{os.path.basename(args.output)}'
    
    # Generate timestamped log filename if not provided
    if not args.log_file:
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        model_name = 'claude-3-5'
        args.log_file = f'scores/{timestamp}-{model_name}-responses.log'
    
    # Create scores directory if it doesn't exist
    os.makedirs('scores', exist_ok=True)
    
    # Setup logging
    logger = setup_logging(args.log_file)
    logger.info(f"=== SCORING SESSION STARTED: {datetime.now()} ===")
    logger.info(f"Input file: {args.input}")
    logger.info(f"Output file: {args.output}")
    logger.info(f"Prompt file: {args.prompt}")
    logger.info(f"Ground truth file: {args.ground_truth}")
    
    # Load conversation context with ground truth examples
    conversation_history = load_conversation_history(args.prompt, args.ground_truth)
    
    # Load services to score
    services = []
    with open(args.input, 'r') as f:
        for line in f:
            if line.strip():
                services.append(json.loads(line))
    
    print(f"Found {len(services)} services to score")
    print(f"Using ground truth examples from: {args.ground_truth}")
    print(f"Logging raw responses to: {args.log_file}")
    
    # Score each service
    results = []
    for i, service in enumerate(services, 1):
        print(f"\nProgress: {i}/{len(services)}")
        
        score = score_service(service['service_name'], service['provider'], conversation_history, logger)
        
        # Create result
        result = {
            "provider": service['provider'],
            "service_name": service['service_name'],
            "claude_3_5_score": score
        }
        if service.get('service_alias'):
            result["service_alias"] = service['service_alias']
        
        results.append(result)
        
        # Save progress every 10 services
        if i % 10 == 0:
            with open(args.output, 'w') as f:
                for r in results:
                    if r['claude_3_5_score'] is not None:
                        f.write(json.dumps(r) + '\n')
            print(f"Progress saved: {sum(1 for r in results if r['claude_3_5_score'] is not None)} scores")

        # Rate limiting
        time.sleep(1)
    
    # Final save
    with open(args.output, 'w') as f:
        for r in results:
            if r['claude_3_5_score'] is not None:
                f.write(json.dumps(r) + '\n')
    
    successful = sum(1 for r in results if r['claude_3_5_score'] is not None)
    print(f"\nCompleted! {successful}/{len(services)} services scored successfully")
    
    # Log session end
    logger.info(f"=== SCORING SESSION COMPLETED: {datetime.now()} ===")
    logger.info(f"Successfully scored: {successful}/{len(services)} services")
    print(f"Raw LLM responses logged to: {args.log_file}")

if __name__ == "__main__":
    main()
