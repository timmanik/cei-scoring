# Cloud Service Scoring with AWS Bedrock

Score cloud services using multiple AWS Bedrock foundation models with intelligent tool use for documentation lookup.

**⚡ NEW: Parallel Execution** - Score 623 services in ~8-12 minutes (vs 30-40 minutes sequential) with automatic retry and failure tracking.

## Features

- **Multiple Model Support**: Score services using Claude Sonnet 4, Claude Opus 4.1, Claude Sonnet 4.5, and Llama 3.3 70B
- **AWS Bedrock Integration**: Direct API access via bearer token authentication
- **Intelligent Tool Use**: Models can automatically search official documentation when uncertain
- **Parallel Execution**: Score multiple services concurrently (default: 5 workers)
- **Smart Retry Logic**: Automatic retry with exponential backoff and throttling detection
- **Second-Pass Retry**: Failed services are automatically retried sequentially
- **Failed Services Tracking**: Saves `.failed.ndjson` files for easy retry workflow
- **Append Mode**: Merge new scores with existing files (deduplication included)
- **Multi-Model Execution**: Run scoring with multiple models in a single command
- **Separate Outputs**: Each model generates its own timestamped NDJSON file
- **Progress Tracking**: Saves progress every 10 services
- **Comprehensive Summary**: Detailed success/failure report with retry commands

## Quick Start

```bash
# 1. Setup
cd scoring-scripts
python3 -m venv .venv
source .venv/bin/activate
pip install boto3 duckduckgo-search python-dotenv

# 2. Configure (add your AWS Bedrock API key)
cp ../.env.copy ../.env
# Edit .env and add AWS_BEARER_TOKEN_BEDROCK

# 3. Test with 10 services
head -10 ../config/extracted_services.ndjson > ../config/test.ndjson
python3 score_services.py --input ../config/test.ndjson --max-workers 3

# 4. Full run (623 services, ~8-12 minutes)
python3 score_services.py --models claude-sonnet-4.5 --max-workers 5

# 5. Retry failures (if any)
# Use exact command from summary output
python3 score_services.py \
  --input ../results/scores/<timestamp>-claude-sonnet-4-5.failed.ndjson \
  --append-to ../results/scores/<timestamp>-claude-sonnet-4-5.ndjson \
  --models claude-sonnet-4.5 \
  --max-workers 3
```

**Expected results:**
- First run: 98-99% success rate (615-620 services scored)
- After retry: 99.5%+ success rate (620-623 services scored)
- Total time: ~10-15 minutes

## Setup

### 0. Set up python3 virtual environment
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

Control maximum tool iterations per service (default: 3):

```bash
# Allow more tool iterations (for complex services)
python3 score_services.py --max-tool-iterations 5

# Allow fewer tool iterations (faster, less thorough)
python3 score_services.py --max-tool-iterations 1

# Disable tool iteration limits
python3 score_services.py --max-tool-iterations 0
```

### Parallel Execution

Control the number of concurrent workers (default: 5):

```bash
# Conservative (fewer rate limits, slower)
python3 score_services.py --max-workers 3

# Default (balanced)
python3 score_services.py --max-workers 5

# Aggressive (faster, may hit rate limits)
python3 score_services.py --max-workers 10
```

### Advanced Options

```bash
python3 score_services.py \
  --input ../config/extracted_services.ndjson \
  --output-dir ../results/scores \
  --prompt ../config/simple_prompt.json \
  --ground-truth ../config/ground_truth.json \
  --models claude-sonnet-4.5 \
  --region us-east-1 \
  --max-workers 5 \
  --max-tool-iterations 3 \
  --use-tools
```

### Full Command Reference

```
python3 score_services.py [OPTIONS]

Options:
  --input PATH              Input NDJSON file with services
                           (default: ../config/extracted_services.ndjson)

  --output-dir PATH        Output directory for score files
                           (default: ../results/scores)

  --prompt PATH            Prompt configuration file
                           (default: ../config/simple_prompt.json)

  --ground-truth PATH      Ground truth examples file
                           (default: ../config/ground_truth.json)

  --models MODEL [MODEL...]  Models to use for scoring
                           (default: claude-sonnet-4.5)
                           Choices: claude-sonnet-4, claude-opus-4.1,
                                   claude-sonnet-4.5, llama-3.3-70b, all

  --use-tools              Enable tool use for documentation lookup
                           (default: enabled)

  --no-tools               Disable tool use

  --region REGION          AWS region (default: us-east-1)

  --max-workers N          Number of parallel workers (default: 5)
                           Lower values = fewer rate limits
                           Higher values = faster execution

  --append-to PATH         Append results to existing output file
                           (for retrying failed services)
                           Automatically deduplicates already-scored services

  --max-tool-iterations N  Maximum number of tool use iterations per service
                           (default: 3)
                           Set to 0 for unlimited iterations
                           Higher values allow more thorough documentation search

  -h, --help               Show help message
```

## Output Files

Each scoring run generates multiple files per model:

### 1. Score File (NDJSON)
`../results/scores/{timestamp}-{model-name}.ndjson`

Contains successfully scored services:

```json
{"provider": "AWS", "service_name": "AmazonS3", "claude_sonnet_4_5_score": 8.5}
{"provider": "AWS", "service_name": "AmazonEC2", "claude_sonnet_4_5_score": 2.0}
```

### 2. Failed Services File (NDJSON)
`../results/scores/{timestamp}-{model-name}.failed.ndjson`

Contains services that failed scoring (only created if there are failures):

```json
{"provider": "AWS", "service_name": "ComplexService"}
{"provider": "GCP", "service_name": "UnknownService"}
```

This file can be used directly as `--input` for retry runs.

### 3. Log File
`../results/scores/logs/{timestamp}-{model-name}-responses.log`

Contains raw model responses, tool interactions, and thread information for debugging.

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

## Retry Workflow

The script includes comprehensive retry mechanisms:

### Automatic Retries (Built-in)

1. **Per-Service Retries**: Each service is retried up to 3 times with exponential backoff
2. **Throttling Detection**: Longer backoff (5-20s) for rate limit errors with random jitter
3. **Tool Iteration Limit**: Maximum 3 tool iterations per attempt by default (configurable with `--max-tool-iterations`) prevents infinite loops (tools remain available on all retries)
4. **Second-Pass Sequential Retry**: After parallel execution, failed services are retried one-by-one

### Manual Retry Workflow

If services still fail after automatic retries, use the failed services file:

#### Step 1: Initial Run
```bash
cd scoring-scripts
python3 score_services.py --models claude-sonnet-4.5 --max-workers 5
```

**Output:**
```
============================================================
SCORING SUMMARY
============================================================
Model: claude-sonnet-4.5
Total services: 623
Successfully scored: 615 (98.7%)
Failed services: 8 (1.3%)

Failed services (by provider):
  AWS (6 services):
    - ComplexService1
    - ComplexService2
    ...

  GCP (2 services):
    - GCPService1
    - GCPService2

Failed services saved to:
  ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.failed.ndjson

To retry failed services:
  cd scoring-scripts && python score_services.py \
    --input ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.failed.ndjson \
    --append-to ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.ndjson \
    --models claude-sonnet-4.5 \
    --max-workers 3
============================================================
```

#### Step 2: Retry Failed Services
```bash
python3 score_services.py \
  --input ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.failed.ndjson \
  --append-to ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.ndjson \
  --models claude-sonnet-4.5 \
  --max-workers 3
```

**What happens:**
- Loads the 8 failed services
- Uses lower worker count (3) for better reliability
- Scores services and appends to original file
- Creates new `.failed.ndjson` with any remaining failures
- **Deduplicates** automatically (won't re-score already-scored services)

#### Step 3: Verify Results
```bash
wc -l ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.ndjson
# Output: 621 (or higher)
```

### Retry Best Practices

1. **Lower worker count on retry**: Use `--max-workers 3` for more reliable retries
2. **Wait between retries**: Give AWS Bedrock rate limits time to reset (5-10 minutes)
3. **Check logs**: Review log files to understand why services failed
4. **Multiple retry attempts**: You can retry multiple times until success rate is acceptable

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

### Legacy (`score_services_claude_3_5.py`)
- Single model (Claude 3.5 Sonnet via Portkey)
- Sequential execution (~30-40 minutes)
- No tool use
- Basic retry logic
- Single output file
- No failure tracking

### Current (`score_services.py`)
- **4 models available** (Claude Sonnet 4, Opus 4.1, Sonnet 4.5, Llama 3.3)
- **Parallel execution** (~8-12 minutes with 5 workers)
- **Intelligent tool use** for documentation lookup
- **Smart retry logic** with throttling detection and jitter
- **Second-pass sequential retry** for failed services
- **Failed services tracking** (`.failed.ndjson` files)
- **Append mode** for iterative retry workflow
- **Thread-safe** execution with per-thread boto3 clients
- **Comprehensive summaries** with retry commands
- AWS Bedrock direct API (no Portkey)
- Model-specific output files
- Enhanced error handling

**Performance improvement:** 3-5x faster with better reliability (98-99% vs ~95% success)

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

### Rate limiting / ThrottlingException errors

**Symptoms:**
```
→ Attempt 2 failed: Exception: Bedrock Converse API error: An error occurred
  (ThrottlingException) when calling the Converse operation: Too many tokens
```

**Solutions:**
1. **Reduce worker count**: Use `--max-workers 3` (more conservative)
2. **Wait and retry**: The script automatically uses longer backoff (5-20s) for throttling
3. **Use failed services workflow**: Failed services are saved to `.failed.ndjson` for later retry
4. **Wait between retry attempts**: Give rate limits 5-10 minutes to reset before retrying

**Automatic handling:**
- Script detects throttling errors and uses 5-20s backoff (vs normal 1-4s)
- Random jitter prevents all threads from retrying simultaneously
- Second-pass sequential retry avoids concurrent pressure

### "Maximum tool use iterations reached" errors

**Symptoms:**
```
→ Attempt 1 failed: Exception: Maximum tool use iterations (3) reached
```

**What it means:**
- Model requested documentation tools 3 times but never provided a final score
- Can happen with very complex or ambiguous services

**Automatic handling:**
- Script retries the service (up to 3 attempts)
- Tools remain available on all retry attempts
- Second-pass retry also attempts scoring

**Manual solutions:**
If service still fails, review logs to understand why and consider:
1. **Increase tool iterations**: Allow more documentation searches
   ```bash
   python3 score_services.py --max-tool-iterations 5
   ```
2. **Add to ground truth**: Add the service to ground truth examples
3. **Disable tools**: Run with `--no-tools` for that specific service

### Segmentation fault on startup

**Cause:** boto3 thread-safety issue (now fixed in latest version)

**Solution:** Update to latest version of the script - each thread creates its own BedrockClient

## Performance

Approximate scoring times for 623 services:

### With Parallel Execution (NEW)

| Workers | Time (Single Model) | Success Rate | Notes |
|---------|---------------------|--------------|-------|
| 3 workers | ~12-15 minutes | 99%+ | Most reliable, fewest rate limits |
| 5 workers (default) | ~8-12 minutes | 98-99% | Balanced speed and reliability |
| 10 workers | ~5-8 minutes | 95-98% | Faster but more throttling |

### Legacy (Sequential)
- Single model: ~30-40 minutes
- With tool use: Add 5-10% overhead
- All 4 models: ~120-160 minutes

### Performance Notes
- **Tool use overhead**: ~5-10% (only when models request documentation)
- **Second-pass retry**: Adds ~2-3 minutes for failed services
- **Multiple models**: Run time scales linearly (4 models ≈ 4x single model time)

## Best Practices

1. **Start with a small test**: Test with 10-20 services first to verify setup
   ```bash
   head -20 ../config/extracted_services.ndjson > test_services.ndjson
   python3 score_services.py --input test_services.ndjson --max-workers 3
   ```

2. **Use default worker count (5)**: Balanced speed and reliability for production runs

3. **Enable tool use**: Provides better accuracy for lesser-known services (enabled by default)

4. **Monitor the summary**: Check success rate after each run
   - Target: 98%+ success rate
   - If lower, reduce `--max-workers` and retry failed services

5. **Use retry workflow for failures**: Always retry failed services for maximum coverage
   ```bash
   # Script provides exact command in summary output
   python3 score_services.py --input <file>.failed.ndjson --append-to <file>.ndjson --max-workers 3
   ```

6. **Review logs for patterns**: Check log files to understand tool use and failure patterns

7. **Compare models**: Run multiple models to compare scoring consistency
   ```bash
   python3 score_services.py --models claude-sonnet-4.5 claude-opus-4.1
   ```

8. **Wait between large runs**: Give rate limits time to reset (5-10 minutes) between retry attempts

## Examples

### Example 1: Test Run with 20 Services

```bash
cd scoring-scripts
head -20 ../config/extracted_services.ndjson > ../config/test_services.ndjson
python3 score_services.py \
  --input ../config/test_services.ndjson \
  --models claude-sonnet-4.5 \
  --max-workers 3
```

### Example 2: Full Production Run

```bash
cd scoring-scripts
python3 score_services.py \
  --models claude-sonnet-4.5 \
  --max-workers 5
```

**Expected output:**
```
Successfully scored: 615/623 (98.7%)
Failed services: 8 (1.3%)

To retry failed services:
  python score_services.py \
    --input ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.failed.ndjson \
    --append-to ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.ndjson \
    --models claude-sonnet-4.5 \
    --max-workers 3
```

### Example 3: Retry Failed Services

```bash
# Use exact command from summary output
python3 score_services.py \
  --input ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.failed.ndjson \
  --append-to ../results/scores/2025-10-18-20-00-00-claude-sonnet-4-5.ndjson \
  --models claude-sonnet-4.5 \
  --max-workers 3
```

**Result:** Original file updated with new scores (621/623 scored)

### Example 4: Compare Multiple Models

```bash
python3 score_services.py \
  --models claude-sonnet-4.5 claude-opus-4.1 \
  --max-workers 5
```

**Runtime:** ~16-24 minutes for 2 models

### Example 5: Conservative Run (Minimize Rate Limits)

```bash
python3 score_services.py \
  --models claude-sonnet-4.5 \
  --max-workers 3
```

**Trade-off:** Slower (~12-15 min) but 99%+ success rate

### Example 6: Fast Run (Acceptable Rate Limits)

```bash
python3 score_services.py \
  --models claude-sonnet-4.5 \
  --max-workers 10
```

**Trade-off:** Faster (~5-8 min) but 95-98% success rate, more failures to retry
