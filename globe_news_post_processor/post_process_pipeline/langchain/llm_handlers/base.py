import os
import json
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any

import structlog
from langchain_core.prompts import PromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter

from globe_news_post_processor.config import Config


class BaseLLMHandler(ABC):
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
    def process_article_batch(self, articles: List[Dict[str, Any]]) -> Tuple[
        List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
        pass

    @staticmethod
    def _load_few_shot_examples(filename: str) -> List[Dict[str, str]]:
        examples_path = os.path.join('globe_news_post_processor', 'post_process_pipeline', 'langchain', 'prompts',
                                     filename)
        try:
            with open(examples_path, 'r') as f:
                data = json.load(f)
            if not isinstance(data, list) or not all(
                    isinstance(item, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in item.items())
                    for item in data):
                raise ValueError("Invalid few-shot examples format")
            return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading few-shot examples: {str(e)}")

    @staticmethod
    def _load_system_prompt(filename: str) -> str:
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
        Create a rate limiter for the LLM.

        :returns: Runnable: LLM runnable with rate limiting configuration.
        """
        return InMemoryRateLimiter(
            requests_per_second=0.5,
            check_every_n_seconds=0.1,
            max_bucket_size=5
        )