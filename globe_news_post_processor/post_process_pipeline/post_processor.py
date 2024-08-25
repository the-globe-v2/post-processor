import structlog
from typing import Dict, Any, Tuple

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import GlobeArticle, CuratedGlobeArticle, FailedGlobeArticle, LLMArticleData
from globe_news_post_processor.post_process_pipeline.langchain import LLMHandlerFactory
from globe_news_post_processor.post_process_pipeline.translator import ArticleTranslator


class ArticlePostProcessor:
    def __init__(self, config: Config):
        self._config = config
        self._logger = structlog.get_logger()
        self._translator = ArticleTranslator(config)
        self._llm_handler = LLMHandlerFactory.create_handler(config)

    def process_article(self, article: GlobeArticle) -> Tuple[CuratedGlobeArticle, Dict[str, int]] | FailedGlobeArticle:
        try:
            llm_result, token_usage = self._llm_handler.process_article(article.model_dump())

            translated_title, translated_description = self._translate_if_needed(article)

            curated_article = self._create_curated_article(article, llm_result, translated_title,
                                                           translated_description)

            return curated_article, token_usage
        except Exception as e:
            self._logger.error(f"Error post processing article {article.id}: {str(e)}")
            return FailedGlobeArticle(**article.model_dump(), failure_reason=str(e))

    def _translate_if_needed(self, article: GlobeArticle) -> Tuple[str, str]:
        if article.language != 'en' and article.language:
            title = self._translator.translate(article.title, from_lang=article.language)
            description = self._translator.translate(article.description, from_lang=article.language)
        else:
            title, description = article.title, article.description
        return title, description

    @staticmethod
    def _create_curated_article(article: GlobeArticle, llm_result: LLMArticleData,
                                translated_title: str, translated_description: str) -> CuratedGlobeArticle:
        return CuratedGlobeArticle(
            **article.model_dump(exclude={'category', 'related_countries', 'keywords',
                                          'title_translated', 'description_translated'}),
            category=llm_result.category,
            related_countries=llm_result.related_countries,
            keywords=llm_result.keywords,
            title_translated=translated_title,
            description_translated=translated_description
        )
