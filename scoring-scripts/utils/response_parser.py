"""
Response parsing utilities for AWS Bedrock Converse API.

Extracts scores, tool requests, and handles different response formats.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple


logger = logging.getLogger(__name__)


def extract_tool_requests(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract tool use requests from a Bedrock response.

    Args:
        response: Response from Bedrock Converse API

    Returns:
        list: List of tool use content blocks

    Example response structure:
        {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_abc123",
                                "name": "get_aws_service_docs",
                                "input": {"service_name": "AWS Lambda"}
                            }
                        }
                    ]
                }
            },
            "stopReason": "tool_use"
        }
    """
    tool_requests = []

    # Get message content
    message = response.get('output', {}).get('message', {})
    content = message.get('content', [])

    # Extract tool use blocks
    for block in content:
        if 'toolUse' in block:
            tool_requests.append(block)

    return tool_requests


def extract_text_from_response(response: Dict[str, Any]) -> str:
    """
    Extract text content from a Bedrock response.

    Args:
        response: Response from Bedrock Converse API

    Returns:
        str: Combined text from all text blocks
    """
    message = response.get('output', {}).get('message', {})
    content = message.get('content', [])

    text_parts = []
    for block in content:
        if 'text' in block:
            text_parts.append(block['text'])

    return '\n'.join(text_parts)


def parse_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract and parse JSON from text response.

    Handles various formats:
    - JSON in ```json code blocks
    - Plain JSON objects
    - JSON embedded in text

    Args:
        text: Text potentially containing JSON

    Returns:
        dict: Parsed JSON object, or None if parsing fails
    """
    # Try to find JSON in code block
    if "```json" in text:
        try:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            if json_end == -1:
                json_text = text[json_start:].strip()
            else:
                json_text = text[json_start:json_end].strip()

            return json.loads(json_text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON from code block: {e}")

    # Try to find plain JSON object
    json_start = text.find('{')
    if json_start != -1:
        # Find matching closing brace
        brace_count = 0
        json_end = json_start
        for i, char in enumerate(text[json_start:], json_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_end > json_start:
            try:
                json_text = text[json_start:json_end].strip()
                return json.loads(json_text)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse JSON from text: {e}")

    return None


def extract_scores_from_json(score_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Extract individual scores from parsed JSON.

    Args:
        score_data: Parsed JSON containing scores

    Returns:
        dict: Dictionary of {category: score} or None if extraction fails
    """
    # Try different possible locations for scores
    if "properties" in score_data and "scores" in score_data["properties"]:
        scores = score_data["properties"]["scores"]
    elif "scores" in score_data:
        scores = score_data["scores"]
    else:
        logger.warning("Cannot find scores in response JSON")
        return None

    # Extract score values
    score_values = {}
    for category, value in scores.items():
        if isinstance(value, dict):
            if 'score' in value:
                score_values[category] = float(value['score'])
            else:
                logger.warning(f"Missing 'score' field in category {category}")
                return None
        else:
            # If it's just a number
            score_values[category] = float(value)

    return score_values


def calculate_average_score(scores: Dict[str, float]) -> Optional[float]:
    """
    Calculate average of scores.

    Args:
        scores: Dictionary of {category: score}

    Returns:
        float: Average score rounded to 2 decimal places, or None if invalid
    """
    if not scores:
        return None

    if len(scores) != 7:
        logger.warning(f"Expected 7 scores, got {len(scores)}")
        return None

    avg = sum(scores.values()) / len(scores)
    return round(avg, 2)


def parse_score_response(response: Dict[str, Any]) -> Optional[float]:
    """
    Parse a scoring response and extract the final average score.

    Args:
        response: Response from Bedrock Converse API

    Returns:
        float: Average score (1.00-10.00), or None if parsing fails
    """
    # Extract text from response
    text = extract_text_from_response(response)

    if not text:
        logger.error("No text content in response")
        return None

    # Parse JSON from text
    score_data = parse_json_from_text(text)

    if not score_data:
        logger.error("Failed to parse JSON from response")
        return None

    # Extract scores
    scores = extract_scores_from_json(score_data)

    if not scores:
        logger.error("Failed to extract scores from JSON")
        return None

    # Calculate average
    avg_score = calculate_average_score(scores)

    if avg_score is None:
        logger.error("Failed to calculate average score")
        return None

    logger.info(f"Parsed score: {avg_score}")
    return avg_score


def get_stop_reason(response: Dict[str, Any]) -> str:
    """
    Get the stop reason from a response.

    Args:
        response: Response from Bedrock Converse API

    Returns:
        str: Stop reason (e.g., 'end_turn', 'tool_use', 'max_tokens')
    """
    return response.get('stopReason', 'unknown')


def is_tool_use_response(response: Dict[str, Any]) -> bool:
    """
    Check if response contains tool use requests.

    Args:
        response: Response from Bedrock Converse API

    Returns:
        bool: True if response requests tool use
    """
    return get_stop_reason(response) == 'tool_use'


def get_response_message(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the assistant message from response.

    This is useful for adding to conversation history.

    Args:
        response: Response from Bedrock Converse API

    Returns:
        dict: Message object with role and content
    """
    return response.get('output', {}).get('message', {})
