import asyncio
from typing import List, Tuple, Dict, Any

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import GlobeArticle, CuratedGlobeArticle, FailedGlobeArticle, FailedLLMRequest
from globe_news_post_processor.post_process_pipeline.langchain import LLMHandlerFactory
from globe_news_post_processor.post_process_pipeline.translator import ArticleTranslator


# TODO: Change ArticlePostProcessor to only process one article at a time, GlobeNewsPostProcessor will handle batches
class ArticlePostProcessor:
    def __init__(self, config: Config):
        self._config = config
        self._translator = ArticleTranslator(config)
        self._llm_handler = LLMHandlerFactory.create_handler(config)

    def process_batch(self, articles: List[GlobeArticle]) -> Tuple[
        List[CuratedGlobeArticle], List[FailedGlobeArticle]]:

        # Convert GlobeArticle objects to dictionaries for processing
        dict_articles = [article.model_dump() for article in articles]

        # Call the process_article_batch method of the LLM handler
        llm_processed_articles, llm_process_fails, token_usage = self._llm_handler.process_article_batch(dict_articles)

        # Translate article titles and descriptions
        translated_articles, failed_translations = asyncio.run(self._translate_articles_async(llm_processed_articles))

        post_processed_items = [CuratedGlobeArticle.model_validate(article) for article in translated_articles]
        failed_articles = [FailedGlobeArticle.model_validate(article) for article in
                           llm_process_fails + failed_translations]

        return post_processed_items, failed_articles

    async def _translate_articles_async(self, articles: List[Dict[str, Any]]) -> Tuple[
        List[Dict[str, Any]], List[Dict[str, Any]]]:
        tasks = []
        for article in articles:
            # Translate both title and description
            tasks.append(self._translator.translate_async(article['title'], from_lang=article['language']))
            tasks.append(self._translator.translate_async(article['description'], from_lang=article['language']))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Initialize lists for successful translations and failures
        translated_articles = []
        failed_translations = []

        for i, article in enumerate(articles):
            title_result = results[i * 2]
            description_result = results[i * 2 + 1]
            article_modified = article.copy()  # Work with a copy to avoid modifying the original prematurely

            if isinstance(title_result, Exception) or isinstance(description_result, Exception):
                # If any translation failed, record the error
                article_modified['error_message'] = f"Title Error: {str(title_result)}" if isinstance(title_result,
                                                                                                      Exception) else ""
                article_modified['error_message'] += f" Description Error: {str(description_result)}" if isinstance(
                    description_result, Exception) else ""
                failed_translations.append(article_modified)
            else:
                # If both translations succeeded, update the article
                article_modified['title_translated'] = title_result
                article_modified['description_translated'] = description_result
                translated_articles.append(article_modified)

        return translated_articles, failed_translations
