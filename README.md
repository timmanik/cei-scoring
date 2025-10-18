# Cloud Elevation Index - Notebook Analysis Toolkit

This directory contains the analysis tools and utilities for evaluating and scoring cloud services using the Cloud Elevation Index (CEI) methodology.

## 📁 Directory Structure

```
cei-scoring/
├── README.md                          # This file
├── .env                               # Environment variables (API keys)
├── extract_services.py                # Extract service data from scores
├── score_services_claude_3_5.py       # Score services using Claude AI
├── scoring_evaluation.ipynb           # Jupyter notebook for analysis
├── comparisons/                       # Exported comparison reports
│   └── *.txt                          # Analysis reports
├── config/                            # Configuration files
│   ├── extracted_services.ndjson      # Service list for scoring
│   ├── ground_truth.json              # Validation data
│   ├── new_prompt.json                # Detailed AI prompt
│   └── simple_prompt.json             # Simplified AI prompt
├── scores/                            # Generated score files
│   ├── *.ndjson                       # Score results
│   └── *.log                          # Raw AI responses
└── utils/                             # Helper utilities
    ├── comparisons.py                 # Cross-model comparison tools
    ├── data_loaders.py                # Data loading functions
    ├── export_comparison.py           # Export analysis reports
    └── validators.py                  # Validation against ground truth
```

## 🚀 Quick Start

### Prerequisites
0. Set up a Python virtual environment ([venv documentation](https://docs.python.org/3/library/venv.html)) for isolated dependencies:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

1. Install required dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```

2. Set up your environment variables in `.env`:
> **Note:**  
> This project currently uses Portkey AI Gateway to access LLM endpoints. In the future, I may implement direct integration with AWS Bedrock or other LLM providers as needed.
   ```bash
   PORTKEY_API_KEY=your_api_key_here
   PORTKEY_VIRTUAL_KEY_AWS=your_virtual_key_here
   ```

### Basic Workflow

1. **Extract Services** - Get service list from existing scores:
   ```bash
   python extract_services.py --input scores/cei_scores.ndjson --output config/extracted_services.ndjson
   ```

2. **Score Services** - Generate new scores using AI:
   ```bash
   # Using detailed prompt
   python score_services_claude.py --input config/extracted_services.ndjson
   
   # Using simplified prompt with examples
   python score_services_simple.py --input config/extracted_services.ndjson
   ```

3. **Analyze Results** - Open the Jupyter notebook:
   ```bash
   jupyter notebook scoring_evaluation.ipynb
   ```

## 📊 Core Components

### Scoring Scripts

#### `score_services_claude_3_5.py`
- **Purpose**: Simplified scoring with ground truth examples
- **Features**: Few-shot learning, retry logic, response logging
- **Usage**: `python score_services_claude_3_5.py --input services.ndjson --ground-truth config/ground_truth.json`

#### `extract_services.py`
> **Note:**  
> This script does not need to be run again. It was used to extract the service names from the original `cei_scores.ndjson`.
- **Purpose**: Extract service information from existing score files
- **Output**: Clean NDJSON with provider, service_name, service_alias
- **Usage**: `python extract_services.py --input scores.ndjson --output services.ndjson`

### Analysis Notebook

#### `scoring_evaluation.ipynb`
Interactive Jupyter notebook for:
- Loading and comparing score files
- Validating against ground truth data
- Cross-model score comparison
- Visualization of results
- Statistical analysis

### Utility Functions

#### `utils/data_loaders.py`
- `load_old_format_scores()` - Load legacy score formats
- `load_new_format_scores()` - Load current score formats
- Automatic score column detection and cleaning

#### `utils/comparisons.py`
- `compare_model_scores_unified()` - Compare scores across models
- Identify high disagreement services
- Flag similar scoring patterns
- Statistical disagreement analysis

#### `utils/validators.py`
- `validate_dataframe_against_ground_truth()` - Validate scores
- Check against expected ranges
- Calculate accuracy rates
- Identify outliers

#### `utils/export_comparison.py`
- `export_comparison_results_to_file()` - Export analysis to text files
- Generates timestamped reports in `comparisons/` folder
- Includes all services meeting criteria (not just top results)

## 🎯 Scoring Methodology

The Cloud Elevation Index scores services on a scale of 1-10 across seven dimensions:

1. **Infrastructure Management** (1=manual, 10=fully managed)
2. **Operational Maintenance** (1=high maintenance, 10=zero maintenance)
3. **Technical Skills** (1=expert required, 10=no technical skills)
4. **Pricing Model** (1=complex/unpredictable, 10=simple/predictable)
5. **Security & Compliance** (1=user responsible, 10=provider managed)
6. **Scalability & Control** (1=manual scaling, 10=automatic scaling)
7. **Business Continuity** (1=user managed, 10=provider guaranteed)

### Service Categories
- **IaaS** (1.0-2.9): Raw infrastructure services
- **PaaS** (3.0-7.9): Platform services with shared responsibility
- **SaaS** (8.0-10.0): Fully managed application services

## 📁 Configuration Files

### `config/ground_truth.json`
Contains validated service scores for testing accuracy:
```json
{
  "ground_truth": {
    "AmazonEC2": {"expected_range": [1.0, 2.5], "category": "IaaS", "provider": "AWS"},
    "AWSLambda": {"expected_range": [7.5, 9.5], "category": "High-PaaS/SaaS", "provider": "AWS"}
  }
}
```

### `config/simple_prompt.json` & `config/new_prompt.json`
Instruction prompts for AI calls.

## Output Formats

### Score Files (`scores/*.ndjson`)
```json
{"provider": "AWS", "service_name": "AWSLambda", "claude_simple_score": 8.43, "service_alias": "AWS Lambda"}
```

### Log Files (`scores/*.log`)
Raw AI responses for debugging and analysis.

## Advanced Usage

### Custom Scoring
```bash
# Score specific services with custom prompt
python score_services_claude.py \
  --input my_services.ndjson \
  --output custom_scores.ndjson \
  --prompt my_custom_prompt.json
```


## Troubleshooting

### Common Issues
1. **Missing API Keys**: Ensure `.env` file contains valid Portkey credentials
2. **Empty Responses**: Check API rate limits and model availability
3. **JSON Parse Errors**: Review raw log files for malformed responses
4. **Score Validation**: Compare against ground truth in the notebook

### Rate Limiting
Scripts include automatic rate limiting (1 second between requests) to prevent API throttling.

> **Cost Reference**: The `2025-09-15-15-43-15-claude-3-5.ndjson` scores (623 API calls) cost $3.80 using Claude Sonnet 3.5 on-demand pricing.