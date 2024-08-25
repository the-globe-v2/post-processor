# path: globe_news_post_processor/post_process_pipeline/langchain/llm_handlers/azure_openai.py

import time
from typing import List, Tuple, Dict, Any, cast
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import pydantic.v1.types
from bson import ObjectId
from openai import RateLimitError
from langchain_core.runnables import Runnable
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import FewShotPromptTemplate

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import LLMArticleData
from globe_news_post_processor.post_process_pipeline.langchain.llm_handlers.base import BaseLLMHandler


class AzureOpenAIHandlerError(Exception):
    """Base class for exceptions in the AzureOpenAIHandler module."""

    def __init__(self, message: str, article_id: ObjectId):
        self.message = message
        self.article_id = article_id
        super().__init__(self.message)


class AzureOpenAIHandler(BaseLLMHandler):
    def __init__(self, config: Config):
        super().__init__(config)

        self._api_key = config.LLM_API_KEY.get_secret_value()
        self._endpoint = str(config.LLM_ENDPOINT)
        self._api_version = config.LLM_API_VERSION

        self._llm = self._initialize_llm()
        self._structured_llm = self._create_structured_llm()

    def _initialize_llm(self) -> AzureChatOpenAI:
        """
        Initialize the Azure OpenAI chat model with the configuration settings.

        :returns:
            AzureChatOpenAI: Initialized Azure OpenAI chat model.
        """
        return AzureChatOpenAI(
            api_key=cast(pydantic.v1.types.SecretStr, self._api_key),  # pydantic.v1.types.SecretStr expected, v2 given
            azure_endpoint=cast(str, self._endpoint),  # str expected, Url given
            api_version=self._api_version,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            max_retries=self._max_retries,
            rate_limiter=self._rate_limiter
        )

    def _create_structured_llm(self) -> Runnable:
        """
            Create a structured output version of the LLM, this directly maps the LLM response to a pydantic model and
            raises errors when the LLMs response is not structured as expected.

            :returns:
                 Runnable: LLM runnable with structured output configuration.
        """
        return self._llm.with_structured_output(LLMArticleData, method='json_mode', include_raw=True)


    def process_article_batch(self, articles: List[Dict[str, Any]]) -> Tuple[
        List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
        """
        Process a batch of articles using the LLM.

        This function processes multiple articles concurrently using a ThreadPoolExecutor.
        It handles rate limiting and other errors, retrying failed requests with exponential backoff.
        IT IS IMPERATIVE THAT THE ORDER OF THE OUTPUT MATCHES THE ORDER OF THE INPUT.

        :param articles: (Dict[Any]) A dictionary containing the article IDs and content to be processed.

        :returns: Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]
                - A list of successfully processed articles as dictionaries.
                - A list of failed articles as dictionaries with an error_message key.
                - A dictionary with total token usage information.
        """
        # Set up the prompt template for the LLM, including the system prompt and few-shot examples
        prompt = FewShotPromptTemplate(
            prefix=self._system_prompt,
            example_prompt=self._example_prompt,
            examples=self._few_shot_examples,
            input_variables=["input"],
            suffix="\n{input}",
        )

        # Create the processing chain
        chain = prompt | self._structured_llm

        successful_articles: List[Dict[str, Any]] = []  # type: ignore
        failed_articles: List[Dict[str, Any]] = []  # type: ignore
        total_usage = {'input_tokens': 0, 'output_tokens': 0}
        usage_lock = Lock()  # Lock to ensure thread-safe updates to total_usage

        def process_single_article(article_id: ObjectId, content: str, max_retries: int = 4,
                                   initial_wait: int = 8) -> LLMArticleData:
            for attempt in range(max_retries):
                try:
                    # Invoke the LLM chain
                    invoke_result = chain.invoke({'input': content})
                    parsed_result = cast(LLMArticleData, invoke_result['parsed'])

                    # Update token usage in a thread-safe manner
                    with usage_lock:
                        total_usage['input_tokens'] += invoke_result['raw'].usage_metadata['input_tokens']
                        total_usage['output_tokens'] += invoke_result['raw'].usage_metadata['output_tokens']
                    self._logger.debug(
                        f"Processed article {article_id} with {invoke_result['raw'].usage_metadata['total_tokens']} tokens")
                    return parsed_result
                except RateLimitError as rle:
                    if attempt < max_retries - 1:
                        # Implement exponential backoff for rate limit errors
                        wait_time = initial_wait * (2 ** attempt)
                        self._logger.warning(
                            f"Rate limit hit, retrying in {wait_time} seconds. Retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                    else:
                        # Raise custom error if max retries reached for rate limit
                        raise AzureOpenAIHandlerError(f"Max retries reached for rate limit: {str(rle)}", article_id)
                except Exception as inv_e:
                    # Raise custom error for any other exception
                    raise AzureOpenAIHandlerError(f"Error processing article: {str(inv_e)}", article_id)

            # This line should never be reached due to the exception in the last iteration of the loop
            raise AzureOpenAIHandlerError("Unexpected: Max retries reached without throwing an exception", article_id)

        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=min(10, len(articles))) as executor:
            # Submit tasks to the executor
            future_to_article = {
                executor.submit(
                    process_single_article,
                    article_id=article['id'],
                    content=article['content'],
                    max_retries=4,
                    initial_wait=8
                ): article
                for article in articles
            }

            # Process completed futures
            for future in as_completed(future_to_article):
                article: Dict[str, Any] = future_to_article[future]
                try:
                    result = cast(LLMArticleData, future.result())
                    article.update(result.model_dump())
                    successful_articles.append(article)
                except AzureOpenAIHandlerError as e:
                    # Handle custom errors from process_single_article
                    self._logger.error(f"Failed to process article {e.article_id}: {e.message}")
                    article['error_message'] = e.message
                    failed_articles.append(article)
                except Exception as e:
                    # Handle unexpected errors
                    self._logger.error(f"Unexpected error in thread for article {article['id']}: {str(e)}")
                    article['error_message'] = f"Unexpected thread error: {str(e)}"
                    failed_articles.append(article)

        return successful_articles, failed_articles, total_usage
