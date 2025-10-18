"""
Utilities for cloud service scoring with AWS Bedrock.

This package provides:
- Model configurations for multiple LLMs
- AWS Bedrock client wrapper
- Tool definitions and handlers for supplemental documentation lookup
- Web search capabilities with domain filtering
- Response parsing utilities
"""

from .model_config import MODEL_CONFIG, get_model_config
from .bedrock_client import BedrockClient
from .tool_definitions import get_tool_definitions
from .tool_handlers import execute_tool
from .response_parser import parse_score_response, extract_tool_requests
from .web_search import search_with_domain_filter

__all__ = [
    'MODEL_CONFIG',
    'get_model_config',
    'BedrockClient',
    'get_tool_definitions',
    'execute_tool',
    'parse_score_response',
    'extract_tool_requests',
    'search_with_domain_filter',
]
