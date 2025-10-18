"""
AWS Bedrock client wrapper for Converse API.

Provides a unified interface for calling different foundation models via AWS Bedrock.
"""

import os
import boto3
from typing import List, Dict, Any, Optional


class BedrockClient:
    """
    Wrapper for AWS Bedrock Runtime client using the Converse API.

    Handles authentication via bearer token and provides a simplified interface
    for multi-turn conversations with tool use support.
    """

    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize Bedrock client.

        Args:
            region_name: AWS region (default: us-east-1 or from AWS_REGION env var)
        """
        # Set bearer token as environment variable if not already set
        # boto3 automatically picks this up
        if not os.getenv('AWS_BEARER_TOKEN_BEDROCK'):
            raise ValueError(
                "AWS_BEARER_TOKEN_BEDROCK environment variable must be set. "
                "Get your API key from AWS Bedrock console."
            )

        # Determine region
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')

        # Create bedrock-runtime client
        # When AWS_BEARER_TOKEN_BEDROCK is set, boto3 automatically uses it
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=self.region_name
        )

    def converse(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, str]]] = None,
        inference_config: Optional[Dict[str, Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a conversation to a Bedrock model using the Converse API.

        Args:
            model_id: The model identifier (e.g., 'anthropic.claude-sonnet-4-20250514-v1:0')
            messages: List of message objects with 'role' and 'content'
            system: Optional system prompt(s)
            inference_config: Optional inference configuration (temperature, maxTokens, etc.)
            tool_config: Optional tool configuration for function calling
            additional_model_request_fields: Optional model-specific fields

        Returns:
            dict: Response from Bedrock Converse API

        Example message format:
            [
                {
                    "role": "user",
                    "content": [{"text": "Hello, how are you?"}]
                }
            ]

        Example tool_config format:
            {
                "tools": [
                    {
                        "toolSpec": {
                            "name": "get_weather",
                            "description": "Get weather for a location",
                            "inputSchema": {
                                "json": {
                                    "type": "object",
                                    "properties": {
                                        "location": {"type": "string"}
                                    },
                                    "required": ["location"]
                                }
                            }
                        }
                    }
                ]
            }
        """
        # Build request parameters
        request_params = {
            'modelId': model_id,
            'messages': messages
        }

        # Add optional parameters
        if system:
            request_params['system'] = system

        if inference_config:
            request_params['inferenceConfig'] = inference_config

        if tool_config:
            request_params['toolConfig'] = tool_config

        if additional_model_request_fields:
            request_params['additionalModelRequestFields'] = additional_model_request_fields

        # Make the API call
        try:
            response = self.client.converse(**request_params)
            return response
        except Exception as e:
            # Add more context to the error
            raise Exception(f"Bedrock Converse API error: {str(e)}") from e

    def converse_simple(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 8192,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Simplified interface for single-turn conversations.

        Args:
            model_id: The model identifier
            prompt: User prompt text
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            tools: Optional list of tool specifications

        Returns:
            dict: Response from Bedrock Converse API
        """
        # Format messages
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]

        # Format system prompt
        system = None
        if system_prompt:
            system = [{"text": system_prompt}]

        # Format inference config
        inference_config = {
            "temperature": temperature,
            "maxTokens": max_tokens
        }

        # Format tool config
        tool_config = None
        if tools:
            tool_config = {"tools": tools}

        return self.converse(
            model_id=model_id,
            messages=messages,
            system=system,
            inference_config=inference_config,
            tool_config=tool_config
        )
