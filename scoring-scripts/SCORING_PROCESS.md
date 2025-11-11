# Complete Scoring Process Flow

This document explains the complete end-to-end flow of how a cloud service gets scored using the CEI (Cloud Elevation Index) scoring system.

## Overview

The scoring system uses AWS Bedrock LLMs (primarily Claude models) to evaluate cloud services on a 1.00-10.00 scale. The LLM autonomously decides whether to use web search tools to gather documentation when it lacks confidence about a service.

---

## Input → Output Flow

### Step 1: Service Input

**Source:** `config/extracted_services.ndjson`

**Format:**
```json
{
  "provider": "AWS",
  "service_name": "AmazonEC2",
  "service_alias": "Amazon Elastic Compute Cloud"
}
```

Each line in the NDJSON file represents one service to be scored.

---

### Step 2: Base Conversation Setup

**Location:** [score_services.py:606-624](score_services.py#L606-L624)

**Built once and reused for all services:**

The system creates a base conversation that includes:

1. **Initial User Message:**
   - Scoring instructions (1.00-10.00 scale)
   - 7 criteria definitions:
     - Infrastructure Management Responsibility
     - Operational Maintenance Burden
     - Technical Skill Requirements
     - Pricing Model and Cost Structure
     - Security and Compliance Responsibility
     - Scalability Control and Management
     - Business Continuity and Disaster Recovery
   - Few-shot examples (from `ground_truth.json`)
   - Required JSON output format

2. **Assistant Acknowledgment:**
   ```
   "I understand. I'll score cloud services using those 7 criteria on a
   1.00-10.00 scale, where lower scores indicate more user responsibility
   (IaaS-like) and higher scores indicate more provider responsibility
   (SaaS-like). I'm ready to score services accordingly. If I need more
   information about a service, I'll use the available tools to search
   official documentation."
   ```

3. **System Prompt:**
   ```
   "You are a cloud architecture expert who scores cloud services on a
   Cloud Elevation Index from 1.00 (pure IaaS) to 10.00 (pure SaaS).
   Score each service across 7 criteria using two decimal places.
   Base your scores on the service's primary function and typical user experience.
   Always respond with valid JSON in the exact format shown in examples.

   If you are not confident about a service or lack detailed information,
   you can use the available tools to search official documentation.
   This is especially helpful for newer, less common, or recently updated services."
   ```

**Conversation Structure:**
```python
base_conversation = [
  {
    "role": "user",
    "content": [{"text": initial_message}]
  },
  {
    "role": "assistant",
    "content": [{"text": acknowledgment}]
  }
]
```

---

### Step 3: Service-Specific Request

**Location:** [score_services.py:196-203](score_services.py#L196-L203)

For each service, a new user message is appended:

```python
messages = base_conversation.copy()
messages.append({
  "role": "user",
  "content": [{"text": "Please score AmazonEC2 for AWS"}]
})
```

---

### Step 4: Tool Configuration

**Location:** [score_services.py:206-211](score_services.py#L206-L211)

**Tools are provided to the model** (the model decides whether to use them):

```json
{
  "tools": [
    {
      "toolSpec": {
        "name": "get_aws_service_docs",
        "description": "Retrieve official AWS documentation for a specific service...",
        "inputSchema": {
          "type": "object",
          "properties": {
            "service_name": {
              "type": "string",
              "description": "The AWS service name to look up"
            },
            "focus_areas": {
              "type": "array",
              "items": {"type": "string"},
              "description": "Optional: Specific aspects to focus on (e.g., 'pricing', 'management')"
            }
          },
          "required": ["service_name"]
        }
      }
    },
    {
      "toolSpec": {
        "name": "search_cloud_provider_docs",
        "description": "Search official cloud provider documentation for Azure or GCP services...",
        "inputSchema": {
          "type": "object",
          "properties": {
            "service_name": {
              "type": "string",
              "description": "The cloud service name to search for"
            },
            "provider": {
              "type": "string",
              "enum": ["Azure", "GCP"],
              "description": "The cloud provider: 'Azure' or 'GCP'"
            },
            "query_context": {
              "type": "string",
              "description": "Optional: Additional context for the search"
            }
          },
          "required": ["service_name", "provider"]
        }
      }
    }
  ]
}
```

**Tool Availability Logic:** [utils/tool_handlers.py:197-226](utils/tool_handlers.py#L197-L226)

Currently, `should_use_tools()` returns `True` for all services, making tools available. The model decides whether to actually invoke them based on its confidence.

---

### Step 5: First LLM Call

**Location:** [score_services.py:223-229](score_services.py#L223-L229)

**Request to AWS Bedrock:**
```python
response = bedrock_client.converse(
    model_id="anthropic.claude-sonnet-4-5-v2:0",
    messages=[...base_conversation + service_request],
    system=[system_prompt],
    inference_config={
        "temperature": 0.0,
        "maxTokens": 4096
    },
    tool_config={"tools": [...]}
)
```

---

### Step 6A: Path 1 - Direct Scoring (No Tools Needed)

**Location:** [score_services.py:237](score_services.py#L237)

**When:** Service is well-known (e.g., EC2, S3, Lambda)

**LLM Response:**
```json
{
  "output": {
    "message": {
      "role": "assistant",
      "content": [{
        "text": "```json\n{\n  \"service_name\": \"AmazonEC2\",\n  \"provider\": \"AWS\",\n  \"category\": \"Virtual machine infrastructure\",\n  \"properties\": {\n    \"scores\": {\n      \"infrastructure_management\": {\"score\": 1.5},\n      \"operational_maintenance\": {\"score\": 1.5},\n      \"technical_skills\": {\"score\": 2.0},\n      \"pricing_model\": {\"score\": 2.5},\n      \"security_compliance\": {\"score\": 2.0},\n      \"scalability_control\": {\"score\": 2.0},\n      \"business_continuity\": {\"score\": 1.5}\n    }\n  },\n  \"summary\": \"Pure IaaS - user manages OS, applications, scaling\"\n}\n```"
      }]
    }
  },
  "stopReason": "end_turn"
}
```

→ **Proceed to Step 7 (Parsing)**

---

### Step 6B: Path 2 - Tool Use Required

**Location:** [score_services.py:237-253](score_services.py#L237-L253)

**When:** Service is obscure, new, or the model lacks confidence

**LLM Response:**
```json
{
  "output": {
    "message": {
      "role": "assistant",
      "content": [
        {
          "text": "I need more information about this service to provide an accurate score."
        },
        {
          "toolUse": {
            "toolUseId": "tooluse_abc123",
            "name": "get_aws_service_docs",
            "input": {
              "service_name": "AWS Modular Data Center",
              "focus_areas": ["deployment", "management", "pricing"]
            }
          }
        }
      ]
    }
  },
  "stopReason": "tool_use"
}
```

**Detection:** [utils/response_parser.py:244-254](utils/response_parser.py#L244-L254)
```python
def is_tool_use_response(response):
    return response.get('stopReason') == 'tool_use'
```

---

### Step 6C: Tool Execution

**Location:** [utils/tool_handlers.py:140-194](utils/tool_handlers.py#L140-L194)

**Process:**

1. **Extract tool requests:** [utils/response_parser.py:15-55](utils/response_parser.py#L15-L55)
   ```python
   tool_requests = extract_tool_requests(response)
   # Returns: [{"toolUse": {"toolUseId": "...", "name": "...", "input": {...}}}]
   ```

2. **Execute tool:** [utils/tool_handlers.py:22-44](utils/tool_handlers.py#L22-L44)
   ```python
   if tool_name == 'get_aws_service_docs':
       result = execute_aws_docs_tool(tool_input)
   elif tool_name == 'search_cloud_provider_docs':
       result = execute_cloud_docs_search_tool(tool_input)
   ```

3. **Web Search Implementation:** [utils/web_search.py:30-114](utils/web_search.py#L30-L114)

   **For AWS:**
   ```python
   query = "AWS Modular Data Center deployment management pricing"
   # Searches with domain filter:
   # "query (site:docs.aws.amazon.com OR site:aws.amazon.com)"
   ```

   **For Azure:**
   ```python
   query = "Azure App Service overview features pricing"
   # Searches: "(site:learn.microsoft.com OR site:azure.microsoft.com)"
   ```

   **For GCP:**
   ```python
   query = "Cloud Run overview features pricing"
   # Searches: "site:cloud.google.com"
   ```

4. **Web Search via DuckDuckGo:** [utils/web_search.py:84-105](utils/web_search.py#L84-L105)
   ```python
   from ddgs import DDGS

   with DDGS() as ddgs:
       results = list(ddgs.text(
           search_query,
           max_results=5,
           region='wt-wt',  # Worldwide
           safesearch='off'
       ))
   ```

5. **Format Results:** [utils/web_search.py:116-139](utils/web_search.py#L116-L139)
   ```
   AWS Documentation for 'AWS Modular Data Center':
   ==================================================

   1. **AWS Modular Data Center - Overview**
      URL: https://aws.amazon.com/modular-data-center/
      AWS Modular Data Center is a fully managed, ruggedized data center
      solution for disconnected and austere environments. Provides compute,
      storage, and networking in a portable form factor...

   2. **AWS MDC Features and Management**
      URL: https://docs.aws.amazon.com/mdc/latest/userguide/what-is.html
      AWS manages hardware maintenance, cooling, power, and security.
      Customers deploy workloads using familiar AWS services...

   [... up to 5 results ...]
   ```

---

### Step 6D: Tool Results Added to Conversation

**Location:** [score_services.py:242-252](score_services.py#L242-L252)

**Update conversation:**
```python
# Add assistant's tool use request
messages.append({
    "role": "assistant",
    "content": [tool_use_block]
})

# Add tool execution results
messages.append({
    "role": "user",
    "content": [{
        "toolResult": {
            "toolUseId": "tooluse_abc123",
            "content": [{"text": formatted_documentation}],
            "status": "success"
        }
    }]
})
```

---

### Step 6E: Second LLM Call (With Documentation Context)

**Location:** [score_services.py:221-255](score_services.py#L221-L255)

**Same API call, but with updated conversation including tool results.**

**LLM Response:**
```json
{
  "output": {
    "message": {
      "role": "assistant",
      "content": [{
        "text": "Based on the documentation, AWS MDC is highly managed by AWS...\n\n```json\n{\n  \"service_name\": \"AWSMDC\",\n  \"provider\": \"AWS\",\n  \"category\": \"Managed hardware infrastructure\",\n  \"properties\": {\n    \"scores\": {\n      \"infrastructure_management\": {\"score\": 7.0},\n      \"operational_maintenance\": {\"score\": 8.5},\n      \"technical_skills\": {\"score\": 6.0},\n      \"pricing_model\": {\"score\": 5.0},\n      \"security_compliance\": {\"score\": 7.5},\n      \"scalability_control\": {\"score\": 4.0},\n      \"business_continuity\": {\"score\": 8.0}\n    }\n  },\n  \"summary\": \"High PaaS - AWS manages physical infrastructure and maintenance\"\n}\n```"
      }]
    }
  },
  "stopReason": "end_turn"
}
```

**Note:** The tool loop can iterate **up to 3 times** if the model makes multiple tool requests. See [score_services.py:221](score_services.py#L221) for `max_tool_iterations` parameter.

---

### Step 7: Score Parsing

**Location:** [utils/response_parser.py:189-228](utils/response_parser.py#L189-L228)

**Parsing Process:**

1. **Extract text from response:** [response_parser.py:58-76](utils/response_parser.py#L58-L76)
   ```python
   text = extract_text_from_response(response)
   # Extracts text from all "text" blocks in content
   ```

2. **Parse JSON:** [response_parser.py:79-130](utils/response_parser.py#L79-L130)
   - Handles ````json` code blocks
   - Handles plain JSON objects
   - Uses brace matching to extract JSON from mixed text
   ```python
   score_data = parse_json_from_text(text)
   ```

3. **Extract individual scores:** [response_parser.py:133-165](utils/response_parser.py#L133-L165)
   ```python
   scores = {
       "infrastructure_management": 1.5,
       "operational_maintenance": 1.5,
       "technical_skills": 2.0,
       "pricing_model": 2.5,
       "security_compliance": 2.0,
       "scalability_control": 2.0,
       "business_continuity": 1.5
   }
   ```

4. **Calculate average:** [response_parser.py:168-186](utils/response_parser.py#L168-L186)
   ```python
   avg_score = sum(scores.values()) / len(scores)
   # Result: 1.86 (rounded to 2 decimal places)
   ```

---

### Step 8: Result Storage

**Location:** [score_services.py:350-359](score_services.py#L350-L359)

**Written to NDJSON output file:**
```json
{
  "provider": "AWS",
  "service_name": "AmazonEC2",
  "service_alias": "Amazon Elastic Compute Cloud",
  "claude_sonnet_4.5_score": 1.86
}
```

**File naming convention:**
```
results/scores/2025-10-18-21-10-00-claude-sonnet-4-5.ndjson
            └─ timestamp ─┘  └─── model name ──┘
```

**Thread-safe writing:** [score_services.py:363-383](score_services.py#L363-L383)
- Uses file lock for concurrent writes
- Saves progress every 10 services
- Appends to existing file in retry mode

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Service Input                                       │
│ {"provider": "AWS", "service_name": "AmazonEC2"}            │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2-3: Build Conversation                                │
│ - Base conversation (prompt + examples)                     │
│ - System prompt                                             │
│ - Service-specific request: "Please score AmazonEC2 for AWS"│
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Add Tool Config                                     │
│ - get_aws_service_docs                                      │
│ - search_cloud_provider_docs                                │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: First LLM Call                                      │
│ AWS Bedrock Converse API                                    │
│ Model: Claude Sonnet 4.5                                    │
└────────────────────────┬────────────────────────────────────┘
                         ↓
         ┌───────────────┴───────────────┐
         ↓                               ↓
┌──────────────────────┐      ┌──────────────────────┐
│ stopReason:          │      │ stopReason:          │
│ "end_turn"           │      │ "tool_use"           │
│                      │      │                      │
│ Well-known service   │      │ Needs documentation  │
│ (e.g., EC2, S3)      │      │ (e.g., obscure AWS   │
│                      │      │  service)            │
└──────────┬───────────┘      └──────────┬───────────┘
           │                             │
           │                             ↓
           │                  ┌──────────────────────┐
           │                  │ Step 6B-C:           │
           │                  │ Tool Execution       │
           │                  │                      │
           │                  │ 1. Extract tool req  │
           │                  │ 2. Build search      │
           │                  │    query             │
           │                  │ 3. DuckDuckGo search │
           │                  │    (domain filtered) │
           │                  │ 4. Format results    │
           │                  └──────────┬───────────┘
           │                             │
           │                             ↓
           │                  ┌──────────────────────┐
           │                  │ Step 6D:             │
           │                  │ Add Tool Results     │
           │                  │ to Conversation      │
           │                  └──────────┬───────────┘
           │                             │
           │                             ↓
           │                  ┌──────────────────────┐
           │                  │ Step 6E:             │
           │                  │ Second LLM Call      │
           │                  │ (with docs context)  │
           │                  │                      │
           │                  │ Can iterate up to    │
           │                  │ 3 times if needed    │
           │                  └──────────┬───────────┘
           │                             │
           └─────────────┬───────────────┘
                         ↓
           ┌──────────────────────────────┐
           │ Step 7: Parse Response       │
           │                              │
           │ 1. Extract text              │
           │ 2. Parse JSON                │
           │ 3. Extract 7 scores          │
           │ 4. Calculate average         │
           │                              │
           │ Result: 1.86                 │
           └──────────────┬───────────────┘
                          ↓
           ┌──────────────────────────────┐
           │ Step 8: Save Result          │
           │                              │
           │ Write to NDJSON:             │
           │ {                            │
           │   "provider": "AWS",         │
           │   "service_name": "...",     │
           │   "claude_..._score": 1.86   │
           │ }                            │
           └──────────────────────────────┘
```

---

## Key Decision Points

### 1. Tool Use Decision (Autonomously by LLM)

**Location:** Model's internal reasoning

The LLM decides whether to use tools based on:
- Its confidence in knowledge about the service
- Whether the service is well-known vs. obscure
- If the service is new or recently updated

**Well-known services** (typically no tools needed):
- AWS: EC2, S3, RDS, Lambda, CloudFront
- Azure: Virtual Machines, Storage, SQL Database
- GCP: Compute Engine, Cloud Storage, Cloud SQL

**Obscure services** (likely to trigger tool use):
- New services
- Niche/specialized services
- Services with recent major updates
- Services with unclear naming

### 2. Tool Iteration Limit

**Location:** [score_services.py:221, 267](score_services.py#L221)

Maximum **3 tool use iterations** per service to prevent infinite loops.

If the model continues requesting tools after 3 iterations, the scoring attempt fails and gets retried.

### 3. Retry Logic

**Location:** [score_services.py:193, 269-295](score_services.py#L193)

- **Max retries per service:** 3 attempts
- **Backoff strategy:**
  - Normal errors: 1s, 2s, 4s (with jitter)
  - Throttling errors: 5s, 10s, 20s (with jitter)
- **Second pass:** [score_services.py:759-796](score_services.py#L759-L796)
  - Failed services retried sequentially (not parallel)
  - Avoids overwhelming the API

---

## Error Handling

### Failed Scoring

**Location:** [score_services.py:407-431](score_services.py#L407-L431)

Failed services are saved to a separate file:
```
results/scores/2025-10-18-21-10-00-claude-sonnet-4-5.failed.ndjson
```

**Format:**
```json
{"provider": "AWS", "service_name": "ServiceName", "service_alias": "..."}
```

### Retry Failed Services

**Command provided in summary:** [score_services.py:489-501](score_services.py#L489-L501)
```bash
cd scoring-scripts && python score_services.py \
  --input ../results/scores/2025-10-18-claude-sonnet-4-5.failed.ndjson \
  --append-to ../results/scores/2025-10-18-claude-sonnet-4-5.ndjson \
  --models claude-sonnet-4.5 \
  --max-workers 3
```

---

## Parallel Execution

**Location:** [score_services.py:702-751](score_services.py#L702-L751)

**Thread Pool:** Uses `ThreadPoolExecutor` for concurrent scoring

**Default:** 5 parallel workers (configurable via `--max-workers`)

**Thread Safety:**
- Each thread creates its own `BedrockClient` instance
- File writes protected by lock
- Results list protected by lock
- Logger is thread-safe

**Performance:**
- Progress saved every 10 services
- Services scored as they complete (not in order)
- Failed services get sequential retry pass

---

## Model Support

**Location:** [utils/model_config.py](utils/model_config.py)

**Supported models:**
- **Claude Sonnet 4** (`claude-sonnet-4`)
- **Claude Sonnet 4.5** (`claude-sonnet-4.5`) - Default
- **Claude Opus 4.1** (`claude-opus-4.1`)
- **Llama 3.3 70B Instruct** (`llama-3-3-70b`)

**Model-specific configurations:**
- Temperature settings
- Max tokens
- Tool support (Claude models support tools, some others may not)
- Score field naming (e.g., `claude_sonnet_4.5_score`)

---

## Configuration Files

### Input Files

1. **`config/extracted_services.ndjson`**
   - List of services to score
   - Format: `{"provider": "...", "service_name": "...", "service_alias": "..."}`

2. **`config/simple_prompt.json`**
   - Base prompt with 7 criteria definitions
   - Scoring scale (1.00-10.00)
   - Initial conversation structure

3. **`config/ground_truth.json`**
   - Few-shot examples for IaaS, PaaS, SaaS
   - Expected score ranges
   - Used to calibrate model scoring

### Output Files

1. **Score files:** `results/scores/TIMESTAMP-MODEL.ndjson`
2. **Log files:** `results/scores/logs/TIMESTAMP-MODEL-responses.log`
3. **Failed services:** `results/scores/TIMESTAMP-MODEL.failed.ndjson`

---

## Usage Examples

### Basic Scoring

```bash
cd scoring-scripts
python score_services.py
```

### Multiple Models

```bash
python score_services.py --models claude-sonnet-4.5 claude-opus-4.1
```

### Disable Tools

```bash
python score_services.py --no-tools
```

### Custom Parallelism

```bash
python score_services.py --max-workers 10
```

### Retry Failed Services

```bash
python score_services.py \
  --input ../results/scores/2025-10-18-claude-sonnet-4-5.failed.ndjson \
  --append-to ../results/scores/2025-10-18-claude-sonnet-4-5.ndjson \
  --models claude-sonnet-4.5
```

---

## Logging

**Location:** [score_services.py:152-160](score_services.py#L152-L160)

**What gets logged:**
- Full LLM requests and responses
- Tool execution requests and results
- Errors and retry attempts
- Session start/end timestamps
- Final scoring summary

**Log format:**
```
2025-10-18 21:10:00,123 - [ThreadPoolExecutor-0_0] - INFO - === SERVICE: AmazonEC2 (AWS) - ATTEMPT 1, ITER 1 ===
2025-10-18 21:10:00,456 - [ThreadPoolExecutor-0_0] - INFO - RESPONSE: {...}
2025-10-18 21:10:00,789 - [ThreadPoolExecutor-0_0] - INFO - Parsed score: 1.86
```

---

## Summary

The scoring system is designed to be:

1. **Autonomous** - LLM decides when it needs more information
2. **Robust** - Retry logic with exponential backoff
3. **Scalable** - Parallel execution with thread safety
4. **Accurate** - Uses official documentation when needed
5. **Traceable** - Comprehensive logging of all decisions

The key innovation is the **tool use pattern**: rather than pre-determining which services need documentation lookup, the LLM autonomously assesses its confidence and requests documentation only when needed. This reduces API calls and cost while ensuring accuracy for less common services.
