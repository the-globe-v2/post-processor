# path: globe_news_post_processor/post_process_pipeline/post_processor.py

import structlog
from typing import Dict, Tuple

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import GlobeArticle, CuratedGlobeArticle, FailedGlobeArticle, LLMArticleData
from globe_news_post_processor.post_process_pipeline.langchain import LLMHandlerFactory
from globe_news_post_processor.post_process_pipeline.translator import ArticleTranslator


class ArticlePostProcessor:
    """
    A class for post-processing articles using LLM and translation services.
    """

    def __init__(self, config: Config):
        """
        Initialize the ArticlePostProcessor.

        :param config: Configuration object containing necessary settings.
        """
        self._config = config
        self._logger = structlog.get_logger()
        self._translator = ArticleTranslator(config)
        self._llm_handler = LLMHandlerFactory.create_handler(config)

    def process_article(self, article: GlobeArticle) -> Tuple[CuratedGlobeArticle, Dict[str, int]] | FailedGlobeArticle:
        """
        Process a single article, including LLM processing and translation if needed.

        :param article: The GlobeArticle to be processed.
        :return: A tuple containing the CuratedGlobeArticle and token usage, or a FailedGlobeArticle if processing fails.
        """
        try:
            # Process the article using the LLM handler
            llm_result, token_usage = self._llm_handler.process_article(article.model_dump())

            # Translate the title and description if needed
            translated_title, translated_description = self._translate_if_needed(article)

            # Create and return the curated article
            curated_article = self._create_curated_article(article, llm_result, translated_title,
                                                           translated_description)

            return curated_article, token_usage
        except Exception as e:
            # Log the error and return a FailedGlobeArticle if processing fails
            self._logger.error(f"Error post processing article {article.id}: {str(e)}")
            return FailedGlobeArticle(**article.model_dump(), failure_reason=str(e))

    def _translate_if_needed(self, article: GlobeArticle) -> Tuple[str, str]:
        """
        Translate the article title and description if they're not in English.

        :param article: The GlobeArticle to potentially translate.
        :return: A tuple containing the (possibly translated) title and description.
        """
        if article.language != 'en' and article.language:
            # Translate title and description if the article is not in English
            title = self._translator.translate(article.title, from_lang=article.language)
            description = self._translator.translate(article.description, from_lang=article.language)
        else:
            # Use original title and description if the article is in English or language is not specified
            title, description = article.title, article.description
        return title, description

    @staticmethod
    def _create_curated_article(article: GlobeArticle, llm_result: LLMArticleData,
                                translated_title: str, translated_description: str) -> CuratedGlobeArticle:
        """
        Create a CuratedGlobeArticle from the original article and processed data.

        :param article: The original GlobeArticle.
        :param llm_result: The LLMArticleData containing processed information.
        :param translated_title: The translated title (if applicable).
        :param translated_description: The translated description (if applicable).
        :return: A CuratedGlobeArticle with all the processed and translated information.
        """
        # Create a new CuratedGlobeArticle, excluding some fields from the original article
        # and adding new information from the LLM processing and translation
        return CuratedGlobeArticle(
            **article.model_dump(exclude={'category', 'related_countries', 'keywords',
                                          'title_translated', 'description_translated'}),
            category=llm_result.category,
            related_countries=llm_result.related_countries,
            keywords=llm_result.keywords,
            title_translated=translated_title,
            description_translated=translated_description
        )
