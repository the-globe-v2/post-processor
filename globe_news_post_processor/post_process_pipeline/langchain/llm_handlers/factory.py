# path: globe_news_post_processor/post_process_pipeline/langchain/llm_handlers/factory.py

import os
from typing import Optional
from pydantic import HttpUrl
from globe_news_post_processor.config import Config
from .azure_openai import AzureOpenAIHandler
from .base import BaseLLMHandler


class LLMHandlerFactory:
    @staticmethod
    def create_handler(config: Config) -> BaseLLMHandler:
        if config.LLM_PROVIDER == "azure_openai":
            LLMHandlerFactory._validate_azure_openai_config(config)
            return AzureOpenAIHandler(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.LLM_PROVIDER}")

    @staticmethod
    def _validate_azure_openai_config(config: Config) -> None:
        LLMHandlerFactory._validate_api_key(config.LLM_API_KEY.get_secret_value())
        LLMHandlerFactory._validate_endpoint(config.LLM_ENDPOINT)
        LLMHandlerFactory._validate_api_version(config.LLM_API_VERSION)
        LLMHandlerFactory._validate_few_shot_example_file(config.FEW_SHOT_EXAMPLES_FILE)
        LLMHandlerFactory._validate_system_prompt_file(config.SYSTEM_PROMPT_FILE)

    @staticmethod
    def _validate_api_key(api_key: Optional[str]) -> None:
        if not api_key:
            raise ValueError("Azure OpenAI API key is not configured")

    @staticmethod
    def _validate_endpoint(endpoint: Optional[HttpUrl]) -> None:
        if not endpoint:
            raise ValueError("Azure OpenAI endpoint is not configured")

    @staticmethod
    def _validate_api_version(api_version: Optional[str]) -> None:
        if not api_version:
            raise ValueError("Azure OpenAI API version is not configured")

    @staticmethod
    def _validate_few_shot_example_file(filename: str) -> None:
        examples_path = os.path.join('globe_news_post_processor', 'post_process_pipeline', 'langchain', 'prompts',
                                     filename)
        if not os.path.isfile(examples_path):
            raise ValueError(f"Few-shot examples file not found: {examples_path}")

    @staticmethod
    def _validate_system_prompt_file(filename: str) -> None:
        prompt_path = os.path.join('globe_news_post_processor', 'post_process_pipeline', 'langchain', 'prompts',
                                   filename)
        if not os.path.isfile(prompt_path):
            raise ValueError(f"System prompt file not found: {prompt_path}")
