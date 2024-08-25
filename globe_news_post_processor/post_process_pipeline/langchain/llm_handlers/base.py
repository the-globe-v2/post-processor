# path: globe_news_post_processor/post_process_pipeline/langchain/llm_handlers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List
import os
import json
import structlog
from langchain_core.prompts import PromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import LLMArticleData


class BaseLLMHandler(ABC):
    """
    Abstract base class for handling Large Language Model (LLM) operations on articles.

    This class provides a foundation for processing articles using an LLM, including
    loading few-shot examples, system prompts, and rate limiting.

    :param config: Configuration object containing LLM-related settings.
    """

    def __init__(self, config: Config):
        self._logger = structlog.get_logger()
        self._temperature = config.TEMPERATURE
        self._max_tokens = config.MAX_TOKENS
        self._max_retries = config.MAX_RETRIES
        self._few_shot_examples = self._load_few_shot_examples(config.FEW_SHOT_EXAMPLES_FILE)
        self._system_prompt = self._load_system_prompt(config.SYSTEM_PROMPT_FILE)
        self._example_prompt = PromptTemplate.from_template("Article: {input}\n{output}")
        self._rate_limiter = self._create_rate_limiter()

    @abstractmethod
    def process_article(self, article: Dict[str, Any]) -> Tuple[LLMArticleData, Dict[str, int]]:
        """
        Process a single article using the LLM.

        :param article: A dictionary containing the article content to be processed.
        :return: A tuple containing:
            - LLMArticleData: The processed article data.
            - Dict[str, int]: Token usage information.
        """
        pass

    @staticmethod
    def _load_few_shot_examples(filename: str) -> List[Dict[str, str]]:
        """
        Load few-shot examples from a JSON file.

        :param filename: Name of the file containing few-shot examples.
        :return: List of dictionaries containing few-shot examples.
        :raises ValueError: If the file is not found or the format is invalid.
        """
        examples_path = os.path.join('globe_news_post_processor', 'post_process_pipeline', 'langchain', 'prompts',
                                     filename)
        try:
            with open(examples_path, 'r') as f:
                data = json.load(f)
            # Validate the structure of the loaded data
            if not isinstance(data, list) or not all(
                    isinstance(item, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in item.items())
                    for item in data):
                raise ValueError("Invalid few-shot examples format")
            return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading few-shot examples: {str(e)}")

    @staticmethod
    def _load_system_prompt(filename: str) -> str:
        """
        Load the system prompt from a text file.

        :param filename: Name of the file containing the system prompt.
        :return: The system prompt as a string.
        :raises ValueError: If the file is not found.
        """
        prompt_path = os.path.join('globe_news_post_processor', 'post_process_pipeline', 'langchain', 'prompts',
                                   filename)
        try:
            with open(prompt_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"System prompt file not found: {prompt_path}")

    @staticmethod
    def _create_rate_limiter() -> InMemoryRateLimiter:
        """
        Create an in-memory rate limiter for API calls.

        The in-memory rate limiter works by using a token bucket algorithm.
        It allocates a specific number of tokens into a bucket at a fixed rate, where each request consumes one token.
        If there aren't enough tokens available, the request is blocked until tokens are replenished.
        This rate limiter is supports time-based rate limiting without considering request size or other factors.

        :return: An InMemoryRateLimiter instance.
        """
        return InMemoryRateLimiter(
            requests_per_second=0.2,  # Limit to 1 request every 5 seconds
            check_every_n_seconds=0.1,  # Check the limit every 100ms
            max_bucket_size=5  # Allow bursts of up to 5 requests
        )