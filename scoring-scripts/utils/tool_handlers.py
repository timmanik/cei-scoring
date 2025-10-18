"""
Tool execution handlers for AWS Bedrock Converse API.

Executes tool requests from models and formats results.
"""

import logging
from typing import Dict, Any, List

from .web_search import (
    search_aws_documentation,
    search_azure_documentation,
    search_gcp_documentation,
    format_search_results_for_model
)
from .tool_definitions import format_tool_result


logger = logging.getLogger(__name__)


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """
    Execute a tool and return the result.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Input parameters for the tool

    Returns:
        str: Tool execution result as text

    Raises:
        ValueError: If tool name is not recognized
    """
    logger.info(f"Executing tool: {tool_name}")
    logger.debug(f"Tool input: {tool_input}")

    if tool_name == 'get_aws_service_docs':
        return execute_aws_docs_tool(tool_input)
    elif tool_name == 'search_cloud_provider_docs':
        return execute_cloud_docs_search_tool(tool_input)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


def execute_aws_docs_tool(tool_input: Dict[str, Any]) -> str:
    """
    Execute the AWS documentation lookup tool.

    Args:
        tool_input: Tool parameters with 'service_name' and optional 'focus_areas'

    Returns:
        str: Formatted documentation search results
    """
    service_name = tool_input.get('service_name')
    focus_areas = tool_input.get('focus_areas', [])

    if not service_name:
        return "Error: service_name is required"

    logger.info(f"Searching AWS docs for: {service_name}")

    # Build enhanced query with focus areas
    query = service_name
    if focus_areas:
        query += ' ' + ' '.join(focus_areas)

    # Search AWS documentation
    try:
        results = search_aws_documentation(query, max_results=5)
        formatted = format_search_results_for_model(results)

        # Add context header
        output = f"AWS Documentation for '{service_name}':\n"
        output += "=" * 50 + "\n"
        output += formatted

        if focus_areas:
            output += f"\n\nFocus areas searched: {', '.join(focus_areas)}"

        return output

    except Exception as e:
        logger.error(f"Error searching AWS docs: {str(e)}")
        return f"Error retrieving AWS documentation: {str(e)}"


def execute_cloud_docs_search_tool(tool_input: Dict[str, Any]) -> str:
    """
    Execute the cloud provider documentation search tool.

    Args:
        tool_input: Tool parameters with 'service_name', 'provider', and optional 'query_context'

    Returns:
        str: Formatted documentation search results
    """
    service_name = tool_input.get('service_name')
    provider = tool_input.get('provider')
    query_context = tool_input.get('query_context', '')

    if not service_name or not provider:
        return "Error: service_name and provider are required"

    logger.info(f"Searching {provider} docs for: {service_name}")

    # Build query
    query = service_name
    if query_context:
        query += ' ' + query_context

    # Search appropriate provider
    try:
        if provider == 'Azure':
            results = search_azure_documentation(query, max_results=5)
        elif provider == 'GCP':
            results = search_gcp_documentation(query, max_results=5)
        else:
            return f"Error: Unknown provider '{provider}'. Use 'Azure' or 'GCP'."

        formatted = format_search_results_for_model(results)

        # Add context header
        output = f"{provider} Documentation for '{service_name}':\n"
        output += "=" * 50 + "\n"
        output += formatted

        if query_context:
            output += f"\n\nContext: {query_context}"

        return output

    except Exception as e:
        logger.error(f"Error searching {provider} docs: {str(e)}")
        return f"Error retrieving {provider} documentation: {str(e)}"


def process_tool_use_requests(
    tool_use_blocks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Process multiple tool use requests from a model response.

    Args:
        tool_use_blocks: List of tool use content blocks from model response

    Returns:
        list: List of tool result content blocks

    Example input:
        [
            {
                "toolUse": {
                    "toolUseId": "tooluse_abc123",
                    "name": "get_aws_service_docs",
                    "input": {"service_name": "AWS Lambda"}
                }
            }
        ]

    Example output:
        [
            {
                "toolResult": {
                    "toolUseId": "tooluse_abc123",
                    "content": [{"text": "Documentation content..."}],
                    "status": "success"
                }
            }
        ]
    """
    tool_results = []

    for tool_use_block in tool_use_blocks:
        tool_use = tool_use_block.get('toolUse', {})
        tool_use_id = tool_use.get('toolUseId')
        tool_name = tool_use.get('name')
        tool_input = tool_use.get('input', {})

        try:
            # Execute the tool
            result_text = execute_tool(tool_name, tool_input)
            tool_result = format_tool_result(tool_use_id, result_text, is_error=False)

        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            error_message = f"Error executing {tool_name}: {str(e)}"
            tool_result = format_tool_result(tool_use_id, error_message, is_error=True)

        tool_results.append(tool_result)

    return tool_results


def should_use_tools(service_name: str, provider: str) -> bool:
    """
    Determine if tools should be enabled for a service scoring request.

    Args:
        service_name: Cloud service name
        provider: Cloud provider (AWS, Azure, GCP)

    Returns:
        bool: True if tools should be enabled

    Note:
        Currently returns True for all services. In the future, this could
        implement logic to skip tools for well-known services.
    """
    # Well-known services that typically don't need tool use
    # (models have good knowledge of these)
    well_known_services = {
        'AWS': ['AmazonEC2', 'AmazonS3', 'AmazonRDS', 'AWSLambda'],
        'Azure': ['Virtual Machines', 'Azure Storage', 'Azure SQL Database'],
        'GCP': ['Compute Engine', 'Cloud Storage', 'Cloud SQL']
    }

    # For now, enable tools for all services
    # The model will decide whether to use them based on its confidence
    return True

    # Future implementation could check:
    # return service_name not in well_known_services.get(provider, [])
