# Configuration Files for Cloud Elevation Index Scoring

This directory contains the configuration files used for scoring cloud services on the Cloud Elevation Index (CEI) scale from 1.00 (pure IaaS) to 10.00 (pure SaaS).

## File Overview

- **`simple_prompt.json`** - Streamlined prompt for automated scoring
- **`ground_truth.json`** - Reference examples for few-shot learning
- **`extracted_services.ndjson`** - Input file containing services to be scored

## Evolution from Original to Simplified Approach

### Original Approach (`default_prompt.json`)

The original prompt was designed as a conversational, detailed rubric with extensive explanations:

**Original Scoring Criteria:**
1. `level_of_control` - Comprehensive control over infrastructure
2. `maintenance_and_updates` - Ongoing maintenance responsibilities
3. `skill_requirement` - Infrastructure management skills needed
4. `cost_effectiveness` - Resource-based vs subscription pricing
5. `security_and_compliance` - Security and data governance responsibility
6. `disaster_recovery_business_continuity` - DR planning and implementation
7. `scalability_and_performance` - Resource scaling management

**Characteristics:**
- Long, conversational prompt with extensive context
- Detailed scoring rubric with ranges and explanations
- Complex JSON output format with justifications
- Multiple conversation turns to establish context
- Verbose category names

### Simplified Approach (`simple_prompt.json`)

The simplified prompt was created for more reliable automated scoring:

**Simplified Scoring Criteria:**
1. `infrastructure_management` - Who manages servers, OS, networking
2. `operational_maintenance` - Who handles updates, patches, scaling
3. `technical_skills` - Level of expertise needed to use the service
4. `pricing_model` - How the service is priced and billed
5. `security_compliance` - Who handles security controls
6. `scalability_control` - How scaling is managed
7. `business_continuity` - Who manages backup and recovery

**Key Improvements:**
- **Concise criteria names** - Shortened for easier JSON parsing
- **Clear scale definition** - Explicit 1.00-2.99 (IaaS), 3.00-7.99 (PaaS), 8.00-10.00 (SaaS) ranges
- **Simplified language** - More direct, less verbose descriptions
- **Streamlined JSON format** - Cleaner structure for automated processing
- **Few-shot learning integration** - Designed to work with ground truth examples

## Python Implementation Enhancements

The `score_services_claude_3_5.py` script adds several layers of prompt engineering:

### 1. Ground Truth Integration
```python
def load_ground_truth_examples(ground_truth_file):
```
- Automatically injects examples from `ground_truth.json`
- Groups examples by IaaS, PaaS, and SaaS categories
- Provides 2 examples per category for few-shot learning

### 2. Dynamic Prompt Padding
The script automatically appends to the base prompt:
- **Example scores** categorized by service type
- **Expected score ranges** for each category
- **Required JSON output format** specification
- **Service descriptions** to guide scoring consistency

### 3. Enhanced Error Handling
- Robust JSON parsing from LLM responses
- Retry logic for failed scoring attempts
- Validation of required 7 scoring criteria
- Automatic score averaging and rounding

## Scoring Scale Consistency

Both approaches use the same 7-point evaluation but with different presentation:

| Score Range | Classification | Responsibility Model |
|-------------|----------------|---------------------|
| 1.00-2.99   | IaaS          | User manages most everything |
| 3.00-7.99   | PaaS          | Shared responsibility |
| 8.00-10.00  | SaaS          | Provider manages almost everything |

## Why the Changes Were Made

### 1. **Reliability**
- Original prompt was too conversational for consistent automated scoring
- Simplified prompt produces more predictable JSON output

### 2. **Efficiency**
- Reduced token usage by eliminating verbose explanations
- Faster processing with shorter, more focused prompts

### 3. **Consistency**
- Ground truth examples provide scoring benchmarks
- Standardized category names reduce parsing errors

### 4. **Scalability**
- Automated few-shot learning from ground truth
- Easier to maintain and update scoring criteria

## Usage Example

```bash
# Score services using the simplified prompt with ground truth examples
python score_services_claude_3_5.py \
    --input config/extracted_services.ndjson \
    --prompt config/simple_prompt.json \
    --ground-truth config/ground_truth.json \
    --output scores/my_results.ndjson
```

The system automatically combines the base prompt, ground truth examples, and output format specifications to create a comprehensive scoring context for the LLM.