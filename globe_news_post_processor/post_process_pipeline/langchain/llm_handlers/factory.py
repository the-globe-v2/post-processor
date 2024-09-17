# path: globe_news_post_processor/post_process_pipeline/langchain/llm_handlers/factory.py

import os
from typing import Optional

from pydantic import HttpUrl

from globe_news_post_processor.config import Config
from .azure_openai import AzureOpenAIHandler
from .base import BaseLLMHandler


class LLMHandlerFactory:
    """
    Factory class for creating LLM handlers based on the provided configuration.
    """

    @staticmethod
    def create_handler(config: Config) -> BaseLLMHandler:
        """
        Create and return an LLM handler based on the configuration.

        :param config: Configuration object containing LLM settings.
        :return: An instance of BaseLLMHandler.
        :raises ValueError: If an unsupported LLM provider is specified.
        """
        if config.LLM_PROVIDER == "azure_openai":
            LLMHandlerFactory._validate_azure_openai_config(config)
            return AzureOpenAIHandler(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.LLM_PROVIDER}")

    @staticmethod
    def _validate_azure_openai_config(config: Config) -> None:
        """
        Validate the Azure OpenAI configuration.

        :param config: Configuration object containing Azure OpenAI settings.
        :raises ValueError: If any required configuration is missing or invalid.
        """
        LLMHandlerFactory._validate_api_key(config.LLM_API_KEY.get_secret_value())
        LLMHandlerFactory._validate_endpoint(config.LLM_ENDPOINT)
        LLMHandlerFactory._validate_api_version(config.LLM_API_VERSION)
        LLMHandlerFactory._validate_few_shot_example_file(config.FEW_SHOT_EXAMPLES_FILE)
        LLMHandlerFactory._validate_system_prompt_file(config.SYSTEM_PROMPT_FILE)

    @staticmethod
    def _validate_api_key(api_key: Optional[str]) -> None:
        """
        Validate the Azure OpenAI API key.

        :param api_key: The API key to validate.
        :raises ValueError: If the API key is not configured.
        """
        if not api_key:
            raise ValueError("Azure OpenAI API key is not configured")

    @staticmethod
    def _validate_endpoint(endpoint: Optional[HttpUrl]) -> None:
        """
        Validate the Azure OpenAI endpoint.

        :param endpoint: The endpoint URL to validate.
        :raises ValueError: If the endpoint is not configured.
        """
        if not endpoint:
            raise ValueError("Azure OpenAI endpoint is not configured")

    @staticmethod
    def _validate_api_version(api_version: Optional[str]) -> None:
        """
        Validate the Azure OpenAI API version.

        :param api_version: The API version to validate.
        :raises ValueError: If the API version is not configured.
        """
        if not api_version:
            raise ValueError("Azure OpenAI API version is not configured")

    @staticmethod
    def _validate_few_shot_example_file(filename: str) -> None:
        """
        Validate the existence of the few-shot examples file.

        :param filename: The name of the few-shot examples file.
        :raises ValueError: If the file is not found.
        """

        # Construct the path to the few-shot examples file
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        examples_path = os.path.join(project_root, 'globe_news_post_processor', 'post_process_pipeline', 'langchain',
                                     'prompts', filename)

        if not os.path.isfile(examples_path):
            raise ValueError(f"Few-shot examples file not found: {examples_path}")

    @staticmethod
    def _validate_system_prompt_file(filename: str) -> None:
        """
        Validate the existence of the system prompt file.

        :param filename: The name of the system prompt file.
        :raises ValueError: If the file is not found.
        """
        # Construct the path to the system prompt file
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        prompt_path = os.path.join(project_root, 'globe_news_post_processor', 'post_process_pipeline', 'langchain',
                                   'prompts', filename)

        if not os.path.isfile(prompt_path):
            raise ValueError(f"System prompt file not found: {prompt_path}")
