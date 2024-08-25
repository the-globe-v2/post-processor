import asyncio
import httpx
import uuid
import structlog
from pydantic_extra_types.language_code import LanguageAlpha2

from globe_news_post_processor.config import Config


class ArticleTranslatorError(Exception):
    """Base class for exceptions in this module."""


class ArticleTranslator:
    def __init__(self, config: Config):
        """
        Class to handle translation of articles, using the Azure Translator API.
        When rate limits are reached, backoff and retry after the specified time.

        Refer here for more information on the Azure Translator API:
        https://learn.microsoft.com/en-us/azure/ai-services/translator/reference/rest-api-guide

        :param config:
        """
        self._logger = structlog.get_logger()
        self._api_key = config.AZURE_TRANSLATOR_API_KEY.get_secret_value()
        self._endpoint = config.AZURE_TRANSLATOR_ENDPOINT
        self._location = config.AZURE_TRANSLATOR_LOCATION
        self._path = '/translate'
        self._initial_backoff = 1.0  # Initial backoff delay in seconds
        self._max_backoff = 60.0  # Maximum backoff delay in seconds

    async def translate_async(self, text: str, from_lang: LanguageAlpha2,
                              to_lang: LanguageAlpha2 = LanguageAlpha2('en')) -> str:
        """
        Translate the given text asynchronously from the source language to the target language.
        :param text: (str) Text to be translated.
        :param from_lang: (str) Source language code.
        :param to_lang: (str) Target language code. Default is 'en' (English).
        :return: (str) Translated text
        """
        constructed_url = str(self._endpoint) + self._path
        params = {
            'api-version': '3.0',
            'from': str(from_lang),
            'to': [str(to_lang)]
        }
        headers = {
            'Ocp-Apim-Subscription-Key': str(self._api_key),
            'Ocp-Apim-Subscription-Region': str(self._location),
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        body = [{'text': text}]

        backoff = self._initial_backoff
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    response = await client.post(constructed_url, params=params, headers=headers, json=body)
                    response.raise_for_status()
                    translated_text: str = response.json()[0]['translations'][0]['text']
                    if not translated_text:
                        raise ArticleTranslatorError("Translation failed:") from ValueError("Empty response received")
                    else:
                        self._logger.debug(f"Successfully translated text from {from_lang} to {to_lang}")
                        return translated_text
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            backoff = float(retry_after)
                        else:
                            backoff = min(backoff * 2, self._max_backoff)
                        self._logger.warning(
                            f"Azure Translator Service rate limit hit, retrying after {backoff} seconds.")
                        await asyncio.sleep(backoff)
                    else:
                        self._logger.error(f"Translation failed: {e}")
                        raise ArticleTranslatorError(f"Translation failed: {e}")

    def _validate_translation(self, text: str) -> str:
        """
        Validate the translated text.
        """
        return ''