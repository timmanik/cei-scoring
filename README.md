# Cloud Elevation Index - Scoring Toolkit

Analysis tools and utilities for evaluating and scoring cloud services using the Cloud Elevation Index (CEI) methodology.

This repository contains supplemental work for the [Cloud Elevation Index project](https://github.com/psu-cloudservices/Cloud-Elevation-Index) developed by the cloud team at Penn State. See their [project presentation](https://drive.google.com/file/d/19nPqr4m0cxjSRZbBE-f4FiY1yiPmBLOq/view) for an overview of the CEI methodology and framework.

## Directory Structure

```
cei-scoring/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── config/                      # Configuration files and prompts
│   └── README.md                # Details on prompts and ground truth
├── scoring-scripts/             # AWS Bedrock scoring implementation
│   ├── README.md                # Detailed usage documentation
│   ├── score_services.py        # Multi-model scoring with tool use
│   ├── extract_services.py      # Extract services from score files
│   └── utils/                   # Bedrock client, tools, parsers
├── notebooks/                   # Jupyter notebooks for analysis
│   ├── scoring_evaluation.ipynb # Score comparison and validation
│   └── utils/                   # Analysis utilities (comparisons, validators)
└── results/                     # Generated outputs
    ├── scores/                  # NDJSON score files by model
    └── comparison-reports/      # Exported analysis reports
```

## Quick Start

### 1. Setup Environment

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure AWS Bedrock

Copy `.env.copy` to `.env` and add your AWS Bedrock credentials:

```bash
AWS_BEARER_TOKEN_BEDROCK="your-api-key-here"
AWS_REGION="us-east-1"
```

Request model access in the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/) for:
- Anthropic Claude Sonnet 4, Opus 4.1, Sonnet 4.5
- Meta Llama 3.3 70B Instruct

### 3. Score Services

```bash
cd scoring-scripts

# Score with default model (Claude Sonnet 4.5)
python3 score_services.py

# Score with multiple models
python3 score_services.py --models claude-sonnet-4 claude-opus-4.1 llama-3.3-70b

# Score with all available models
python3 score_services.py --models all
```

See [scoring-scripts/README.md](scoring-scripts/README.md) for detailed usage, tool configuration, and advanced options.

### 4. Analyze Results

```bash
# Open analysis notebook
jupyter notebook notebooks/scoring_evaluation.ipynb
```

The notebook provides:
- Cross-model score comparison
- Ground truth validation
- Disagreement analysis
- Statistical summaries

## Scoring Methodology

The Cloud Elevation Index scores cloud services on a 1-10 scale across seven dimensions:

1. **Infrastructure Management** - Who manages servers, OS, networking (1=user, 10=provider)
2. **Operational Maintenance** - Who handles updates, patches, scaling (1=user, 10=provider)
3. **Technical Skills** - Expertise required to use service (1=expert, 10=none)
4. **Pricing Model** - Billing complexity and predictability (1=complex, 10=simple)
5. **Security & Compliance** - Who manages security controls (1=user, 10=provider)
6. **Scalability & Control** - How scaling is managed (1=manual, 10=automatic)
7. **Business Continuity** - Who handles backup and recovery (1=user, 10=provider)

### Service Categories

| Score Range | Category | Description |
|-------------|----------|-------------|
| 1.0-2.9     | IaaS     | Raw infrastructure, user manages most aspects |
| 3.0-7.9     | PaaS     | Platform services with shared responsibility |
| 8.0-10.0    | SaaS     | Fully managed, provider handles operations |

## Key Features

### Multi-Model Scoring
Score services using multiple AWS Bedrock foundation models:
- Claude Sonnet 4, Opus 4.1, Sonnet 4.5
- Llama 3.3 70B Instruct
- Each model generates separate timestamped output files

### Intelligent Tool Use
Models can automatically search official documentation when uncertain:
- AWS services: AWS Documentation API
- Azure services: learn.microsoft.com, docs.microsoft.com
- GCP services: cloud.google.com/docs

### Analysis Utilities
Located in `notebooks/utils/`:
- **data_loaders.py** - Load and normalize score files
- **comparisons.py** - Cross-model score comparison
- **validators.py** - Validate against ground truth
- **export_comparison.py** - Generate analysis reports

## Configuration Files

See [config/README.md](config/README.md) for detailed documentation on:
- **simple_prompt.json** - Streamlined scoring prompt
- **ground_truth.json** - Reference examples for few-shot learning
- **extracted_services.ndjson** - Input services to score

## Output Format

### Score Files (results/scores/*.ndjson)
```json
{"provider": "AWS", "service_name": "AmazonS3", "claude_sonnet_4_5_score": 8.5}
{"provider": "AWS", "service_name": "AmazonEC2", "claude_sonnet_4_5_score": 2.0}
```

### Log Files (results/scores/*-responses.log)
Raw model responses and tool interactions for debugging.

## Troubleshooting

### Missing API Keys
Ensure `.env` contains valid AWS Bedrock credentials:
```bash
AWS_BEARER_TOKEN_BEDROCK="your-key-here"
```

### Model Access Denied
Request model access in AWS Bedrock Console under "Model access" section.

### Empty Responses
Check API rate limits and model availability. Scripts include automatic 1-second delay between requests.

### Score Validation
Use the analysis notebook to compare scores against ground truth and identify outliers.

## Performance

Approximate scoring times for 623 services:
- Single model: 20-30 minutes
- With tool use: +5-10% overhead (only when models are uncertain)
- All 4 models: 80-120 minutes

Progress is saved every 10 services, allowing interruption and resumption.
