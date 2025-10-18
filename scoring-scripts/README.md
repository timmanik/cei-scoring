# Cloud Service Scoring with AWS Bedrock

Score cloud services using multiple AWS Bedrock foundation models with intelligent tool use for documentation lookup.

## Features

- **Multiple Model Support**: Score services using Claude Sonnet 4, Claude Opus 4.1, Claude Sonnet 4.5, and Llama 3.3 70B
- **AWS Bedrock Integration**: Direct API access via bearer token authentication
- **Intelligent Tool Use**: Models can automatically search official documentation when uncertain
- **Multi-Model Execution**: Run scoring with multiple models in a single command
- **Separate Outputs**: Each model generates its own timestamped NDJSON file
- **Retry Logic**: Automatic retry with exponential backoff for failed requests
- **Progress Tracking**: Saves progress every 10 services

## Setup

### 0. Set up python3virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 1. Install Dependencies

```bash
pip install boto3 duckduckgo-search python-dotenv
```

### 2. Configure Environment

Copy `.env.copy` to `.env` and add your AWS Bedrock API key:

```bash
cp ../.env.copy ../.env
```

Edit `.env`:

```bash
# AWS Bedrock Authentication
AWS_BEARER_TOKEN_BEDROCK="your-api-key-here"
AWS_REGION="us-east-1"
```

**Getting your API key:**
1. Visit [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to API Keys
3. Generate a new API key
4. Copy and paste into `.env`

### 3. Request Model Access

Before using models, you need to request access in the AWS Bedrock console:

1. Go to AWS Bedrock Console
2. Navigate to "Model access"
3. Request access for:
   - Anthropic Claude Sonnet 4
   - Anthropic Claude Opus 4.1
   - Anthropic Claude Sonnet 4.5
   - Meta Llama 3.3 70B Instruct

## Usage

### Basic Usage

Score services using the default model (Claude Sonnet 4.5):

```bash
python3 score_services.py
```

### Select Specific Models

Score with one model:

```bash
python3 score_services.py --models claude-opus-4.1
```

Score with multiple models:

```bash
python3 score_services.py --models claude-sonnet-4 claude-opus-4.1 llama-3.3-70b
```

Score with all available models:

```bash
python3 score_services.py --models all
```

### Model Options

Available models:
- `claude-sonnet-4` - Claude Sonnet 4
- `claude-opus-4.1` - Claude Opus 4.1 (most powerful)
- `claude-sonnet-4.5` - Claude Sonnet 4.5 (latest, most intelligent)
- `llama-3.3-70b` - Llama 3.3 70B Instruct

Model aliases:
- `sonnet-4` → `claude-sonnet-4`
- `opus` or `opus-4.1` → `claude-opus-4.1`
- `sonnet` or `sonnet-4.5` → `claude-sonnet-4.5`
- `llama` or `llama-3.3` → `llama-3.3-70b`

### Tool Use

Tool use is enabled by default. Models will automatically search documentation when they lack confidence.

Disable tool use:

```bash
python3 score_services.py --no-tools
```

### Advanced Options

```bash
python3 score_services.py \
  --input config/extracted_services.ndjson \
  --output-dir scores \
  --prompt config/simple_prompt.json \
  --ground-truth config/ground_truth.json \
  --models claude-sonnet-4.5 \
  --region us-east-1 \
  --use-tools
```

### Full Command Reference

```
python3score_services.py [OPTIONS]

Options:
  --input PATH              Input NDJSON file with services
                           (default: config/extracted_services.ndjson)

  --output-dir PATH        Output directory for score files
                           (default: scores/)

  --prompt PATH            Prompt configuration file
                           (default: config/simple_prompt.json)

  --ground-truth PATH      Ground truth examples file
                           (default: config/ground_truth.json)

  --models MODEL [MODEL...]  Models to use for scoring
                           (default: claude-sonnet-4.5)
                           Choices: claude-sonnet-4, claude-opus-4.1,
                                   claude-sonnet-4.5, llama-3.3-70b, all

  --use-tools              Enable tool use for documentation lookup
                           (default: enabled)

  --no-tools               Disable tool use

  --region REGION          AWS region (default: us-east-1)

  -h, --help               Show help message
```

## Output Files

Each scoring run generates two files per model:

### Score File (NDJSON)
`scores/{timestamp}-{model-name}.ndjson`

Contains scored services:

```json
{"provider": "AWS", "service_name": "AmazonS3", "claude_sonnet_4_5_score": 8.5}
{"provider": "AWS", "service_name": "AmazonEC2", "claude_sonnet_4_5_score": 2.0}
```

### Log File
`scores/{timestamp}-{model-name}-responses.log`

Contains raw model responses and tool interactions for debugging.

## How Tool Use Works

When enabled, models can automatically search documentation:

1. **Model Evaluation**: Model assesses its confidence about the service
2. **Tool Request**: If uncertain, model requests documentation lookup
3. **Tool Execution**: System searches official docs (AWS Docs API or web search)
4. **Enhanced Scoring**: Model uses additional context to provide accurate score

### Documentation Sources

- **AWS Services**: AWS Documentation API (via DuckDuckGo with domain filtering)
- **Azure Services**: Search `learn.microsoft.com/*` and `docs.microsoft.com/*`
- **GCP Services**: Search `cloud.google.com/docs/*`

### Example Tool Use Flow

```
1. Request: Score "AWS App Runner"
2. Model: "I need more information about AWS App Runner"
3. Tool: Search AWS documentation for App Runner
4. Results: "AWS App Runner is a fully managed service..."
5. Model: Based on documentation, scores App Runner as 8.5 (SaaS)
```

## Architecture

```
scoring-scripts/
├── score_services.py          # Main scoring script
└── utils/
    ├── __init__.py            # Package exports
    ├── model_config.py        # Model definitions and configuration
    ├── bedrock_client.py      # AWS Bedrock client wrapper
    ├── tool_definitions.py    # Tool schemas for documentation lookup
    ├── tool_handlers.py       # Tool execution logic
    ├── web_search.py          # Web search with domain filtering
    └── response_parser.py     # Response parsing utilities
```

## Comparison with Legacy Script

### Old (`score_services_claude_3_5.py`)
- Single model (Claude 3.5 Sonnet via Portkey)
- No tool use
- Basic retry logic
- Single output file

### New (`score_services.py`)
- Multiple models (4 models available)
- Intelligent tool use for documentation
- AWS Bedrock direct API
- Model-specific output files
- Enhanced error handling

## Troubleshooting

### Error: AWS_BEARER_TOKEN_BEDROCK not set

**Solution**: Add your API key to `.env` file:
```bash
AWS_BEARER_TOKEN_BEDROCK="your-key-here"
```

### Error: Model access denied

**Solution**: Request model access in AWS Bedrock console (see Setup step 3)

### Web search not working

**Solution**: Install duckduckgo-search:
```bash
pip install duckduckgo-search
```

### Rate limiting errors

**Solution**: The script automatically waits 1 second between requests. If you still encounter rate limits, consider:
- Increasing the sleep time in the code
- Using a smaller batch of services
- Spreading scoring across multiple sessions

## Performance

Approximate scoring times (623 services):

- Single model: ~20-30 minutes
- With tool use: Add 5-10% overhead (only for uncertain services)
- All 4 models: ~80-120 minutes

## Best Practices

1. **Start with a small test**: Test with a few services first
2. **Use tool use**: Enables better accuracy for lesser-known services
3. **Monitor logs**: Check log files for tool use patterns and errors
4. **Compare models**: Run multiple models to compare scores
5. **Check progress**: Output files are saved every 10 services

## Examples

### Score 10 services with Claude Sonnet 4.5

```bash
head -10 config/extracted_services.ndjson > test_services.ndjson
python3 score_services.py --input test_services.ndjson --models claude-sonnet-4.5
```

### Compare multiple models

```bash
python3 score_services.py --models claude-sonnet-4 claude-opus-4.1 claude-sonnet-4.5
```

### Quick scoring without tools

```bash
python3 score_services.py --no-tools
```
