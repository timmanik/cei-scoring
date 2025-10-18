"""
Model configurations for AWS Bedrock foundation models.

Defines model IDs, parameters, and naming conventions for supported models.
"""

MODEL_CONFIG = {
    'claude-sonnet-4': {
        'id': 'us.anthropic.claude-sonnet-4-20250514-v1:0',
        'provider': 'anthropic',
        'max_tokens': 8192,
        'temperature': 0.0,
        'supports_tools': True,
        'score_field': 'claude_sonnet_4_score',
        'display_name': 'Claude Sonnet 4'
    },
    'claude-opus-4.1': {
        'id': 'us.anthropic.claude-opus-4-1-20250805-v1:0',
        'provider': 'anthropic',
        'max_tokens': 8192,
        'temperature': 0.0,
        'supports_tools': True,
        'score_field': 'claude_opus_4_1_score',
        'display_name': 'Claude Opus 4.1'
    },
    'claude-sonnet-4.5': {
        'id': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        'provider': 'anthropic',
        'max_tokens': 8192,
        'temperature': 0.0,
        'supports_tools': True,
        'score_field': 'claude_sonnet_4_5_score',
        'display_name': 'Claude Sonnet 4.5'
    },
    'llama-3.3-70b': {
        'id': 'us.meta.llama3-3-70b-instruct-v1:0',
        'provider': 'meta',
        'max_tokens': 8192,
        'temperature': 0.0,
        'supports_tools': True,  # Llama 3.1+ supports tool use
        'score_field': 'llama_3_3_70b_score',
        'display_name': 'Llama 3.3 70B Instruct'
    }
}

# Model name aliases for CLI convenience
MODEL_ALIASES = {
    'sonnet-4': 'claude-sonnet-4',
    'opus-4.1': 'claude-opus-4.1',
    'opus': 'claude-opus-4.1',
    'sonnet-4.5': 'claude-sonnet-4.5',
    'sonnet': 'claude-sonnet-4.5',  # Default to latest
    'llama': 'llama-3.3-70b',
    'llama-3.3': 'llama-3.3-70b'
}


def get_model_config(model_name):
    """
    Get configuration for a specific model.

    Args:
        model_name: Model name or alias

    Returns:
        dict: Model configuration

    Raises:
        ValueError: If model name is not recognized
    """
    # Check if it's an alias
    if model_name in MODEL_ALIASES:
        model_name = MODEL_ALIASES[model_name]

    if model_name not in MODEL_CONFIG:
        available = list(MODEL_CONFIG.keys()) + list(MODEL_ALIASES.keys())
        raise ValueError(
            f"Unknown model '{model_name}'. Available models: {', '.join(available)}"
        )

    return MODEL_CONFIG[model_name]


def get_all_model_names():
    """Get list of all supported model names."""
    return list(MODEL_CONFIG.keys())


def get_file_safe_name(model_name):
    """
    Convert model name to file-safe format.

    Args:
        model_name: Model name (e.g., 'claude-opus-4.1')

    Returns:
        str: File-safe name (e.g., 'claude-opus-4-1')
    """
    return model_name.replace('.', '-')
