"""
Tool definitions for AWS Bedrock Converse API.

Defines tools that models can use to fetch supplemental documentation
about cloud services when they lack confidence in their scoring.
"""

from typing import List, Dict, Any


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get all tool definitions for Bedrock Converse API.

    Returns:
        list: List of tool specification dictionaries
    """
    return [
        get_aws_docs_tool(),
        get_cloud_docs_search_tool()
    ]


def get_aws_docs_tool() -> Dict[str, Any]:
    """
    Tool for retrieving official AWS service documentation.

    This tool should be used when the model needs more information about:
    - Newer or less common AWS services
    - Specific service features and capabilities
    - How the service is managed and operated
    - Pricing and deployment models
    """
    return {
        "toolSpec": {
            "name": "get_aws_service_docs",
            "description": (
                "Retrieve official AWS documentation for a specific service. "
                "Use this when you need detailed information about an AWS service's "
                "features, management model, operational characteristics, or pricing. "
                "Especially useful for newer or less common services where you lack "
                "confidence in your knowledge."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": (
                                "The AWS service name to look up (e.g., 'Amazon S3', "
                                "'AWS Lambda', 'Amazon RDS'). Can be the full name or common abbreviation."
                            )
                        },
                        "focus_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Optional: Specific aspects to focus on (e.g., 'pricing', "
                                "'management', 'features', 'deployment')"
                            )
                        }
                    },
                    "required": ["service_name"]
                }
            }
        }
    }


def get_cloud_docs_search_tool() -> Dict[str, Any]:
    """
    Tool for searching Azure and GCP official documentation.

    This tool performs web searches restricted to official cloud provider documentation
    domains to ensure accurate, authoritative information.
    """
    return {
        "toolSpec": {
            "name": "search_cloud_provider_docs",
            "description": (
                "Search official cloud provider documentation for Azure or GCP services. "
                "This searches the official documentation websites (learn.microsoft.com for Azure, "
                "cloud.google.com/docs for GCP) to find authoritative information about service "
                "features, management models, and operational characteristics. "
                "Use this for non-AWS services when you need more information."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": (
                                "The cloud service name to search for (e.g., 'Azure App Service', "
                                "'Google Cloud Run', 'Azure Cosmos DB')"
                            )
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["Azure", "GCP"],
                            "description": "The cloud provider: 'Azure' or 'GCP'"
                        },
                        "query_context": {
                            "type": "string",
                            "description": (
                                "Optional: Additional context for the search (e.g., "
                                "'pricing model', 'management responsibilities', 'scaling features')"
                            )
                        }
                    },
                    "required": ["service_name", "provider"]
                }
            }
        }
    }


def format_tool_result(tool_use_id: str, content: str, is_error: bool = False) -> Dict[str, Any]:
    """
    Format a tool result for sending back to the model.

    Args:
        tool_use_id: The ID of the tool use request from the model
        content: The result content (documentation text or error message)
        is_error: Whether this is an error response

    Returns:
        dict: Formatted tool result content block

    Example:
        {
            "toolResult": {
                "toolUseId": "tooluse_abc123",
                "content": [{"text": "Documentation content..."}],
                "status": "success"
            }
        }
    """
    return {
        "toolResult": {
            "toolUseId": tool_use_id,
            "content": [{"text": content}],
            "status": "error" if is_error else "success"
        }
    }


def create_tool_result_message(tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a user message containing tool results.

    Args:
        tool_results: List of tool result content blocks

    Returns:
        dict: Message object with tool results

    Example input:
        [
            {
                "toolResult": {
                    "toolUseId": "tooluse_abc123",
                    "content": [{"text": "Doc content"}],
                    "status": "success"
                }
            }
        ]

    Returns:
        {
            "role": "user",
            "content": [...]
        }
    """
    return {
        "role": "user",
        "content": tool_results
    }
