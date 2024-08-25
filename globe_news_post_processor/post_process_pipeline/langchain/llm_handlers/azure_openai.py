from typing import Dict, Any, Tuple, cast

import pydantic.v1.types
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import Runnable
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import FewShotPromptTemplate
from globe_news_post_processor.config import Config
from globe_news_post_processor.models import LLMArticleData
from globe_news_post_processor.post_process_pipeline.langchain.llm_handlers.base import BaseLLMHandler


class AzureOpenAIHandler(BaseLLMHandler):
    def __init__(self, config: Config):
        super().__init__(config)

        # This is really stupid, but I am using pydantic v2 and AzureChatOpenAI is expecting pydantic v1
        self._api_key = pydantic.v1.types.SecretStr(config.LLM_API_KEY.get_secret_value())
        self._endpoint = str(config.LLM_ENDPOINT)
        self._api_version = config.LLM_API_VERSION

        self._llm = self._initialize_llm()
        self._structured_llm = self._create_structured_llm()

    def process_article(self, article: Dict[str, Any]) -> Tuple[LLMArticleData, Dict[str, int]]:
        prompt = FewShotPromptTemplate(
            prefix=self._system_prompt,
            example_prompt=self._example_prompt,
            examples=self._few_shot_examples,
            input_variables=["input"],
            suffix="\n{input}",
        )

        chain = prompt | self._structured_llm

        try:
            invoke_result = chain.invoke({'input': article['content']})
            parsed_result = invoke_result['parsed']
            token_usage = {
                'input_tokens': invoke_result['raw'].usage_metadata['input_tokens'],
                'output_tokens': invoke_result['raw'].usage_metadata['output_tokens']
            }
            # If the parsing of the LLM response failed, raise the parsing error
            if not parsed_result:
                raise invoke_result['parsing_error']

            self._logger.debug(
                f"Processed article {article['id']} with {invoke_result['raw'].usage_metadata['total_tokens']} tokens")
            return parsed_result, token_usage
        except OutputParserException as ope:
            self._logger.warning(
                f"Failed to parse LLMArticleData from LLM response to article {article['id']}: {ope.llm_output}")
            raise
        except Exception as e:
            self._logger.error(f"Unknown error processing LLM response to article {article['id']}: {str(e)}")
            raise

    def _initialize_llm(self) -> AzureChatOpenAI:
        return AzureChatOpenAI(
            api_key=self._api_key,
            azure_endpoint=self._endpoint,
            api_version=self._api_version,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            max_retries=self._max_retries,
            rate_limiter=self._rate_limiter
        )

    def _create_structured_llm(self) -> Runnable:
        return self._llm.with_structured_output(LLMArticleData, method='json_mode', include_raw=True)
