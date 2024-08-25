# path: globe_news_post_processor/post_process_pipeline/translator.py

import uuid
import time
import requests
import structlog
from pydantic_extra_types.language_code import LanguageAlpha2

from globe_news_post_processor.config import Config


class ArticleTranslatorError(Exception):
    """Base class for exceptions in this module."""


class ArticleTranslator:
    """
    A class to handle article translation using Azure Translator Service.
    """

    def __init__(self, config: Config):
        """
        Initialize the ArticleTranslator with the given configuration.

        :param config: Configuration object containing Azure Translator Service settings
        """
        self._logger = structlog.get_logger()
        self._api_key = config.AZURE_TRANSLATOR_API_KEY.get_secret_value()
        self._endpoint = config.AZURE_TRANSLATOR_ENDPOINT
        self._location = config.AZURE_TRANSLATOR_LOCATION
        self._path = '/translate'
        self._initial_backoff = 1.0
        self._max_backoff = 60.0

    def translate(self, text: str, from_lang: LanguageAlpha2,
                  to_lang: LanguageAlpha2 = LanguageAlpha2('en')) -> str:
        """
        Translate the given text from one language to another using Azure Translator Service.

        :param text: The text to be translated
        :param from_lang: The source language code
        :param to_lang: The target language code (default is English)
        :return: The translated text
        :raises ArticleTranslatorError: If the translation fails
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
        while True:
            try:
                response = requests.post(constructed_url, params=params, headers=headers, json=body)
                response.raise_for_status()
                translated_text: str = response.json()[0]['translations'][0]['text']
                if not translated_text:
                    raise ArticleTranslatorError("Translation failed:") from ValueError("Empty response received")
                else:
                    self._logger.debug(f"Successfully translated text from {from_lang} to {to_lang}")
                    return translated_text
            except requests.HTTPError as e:
                if e.response.status_code == 429:
                    # Handle rate limiting with exponential backoff
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        backoff = float(retry_after)
                    else:
                        # If no Retry-After header, use exponential backoff
                        backoff = min(backoff * 2, self._max_backoff)
                    self._logger.warning(
                        f"Azure Translator Service rate limit hit, retrying after {backoff} seconds.")
                    time.sleep(backoff)
                else:
                    # Log and re-raise other HTTP errors
                    self._logger.error(f"Translation failed: {e}")
                    raise ArticleTranslatorError(f"Translation failed: {e}")