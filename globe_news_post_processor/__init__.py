from typing import List, Tuple, Dict

import structlog

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import GlobeArticle, CuratedGlobeArticle, FailedGlobeArticle
from globe_news_post_processor.database.mongo_handler import MongoHandler
from globe_news_post_processor.post_process_pipeline import ArticlePostProcessor


class GlobeNewsPostProcessor:
    def __init__(self, config: Config):
        self._config = config
        self._logger = structlog.get_logger()
        self._mongo_handler = MongoHandler(config)
        self._article_post_processor = ArticlePostProcessor(config)

    def process_pending_articles(self) -> None:
        batch_size = self._config.BATCH_SIZE
        while articles := self._fetch_article_batch(batch_size):
            curated_articles, failed_articles, total_token_usage = self._process_batch(articles)
            self._update_articles(curated_articles, failed_articles)
            self._logger.info(f"Batch processed. Total token usage: {total_token_usage}")

    def _fetch_article_batch(self, batch_size: int) -> List[GlobeArticle]:
        article_batch = self._mongo_handler.get_unprocessed_articles(batch_size)
        self._logger.debug(f"Fetched {len(article_batch)} articles.")
        return article_batch

    def _process_batch(self, articles: List[GlobeArticle]) -> Tuple[
        List[CuratedGlobeArticle], List[FailedGlobeArticle], Dict[str, int]]:
        curated_articles = []
        failed_articles = []
        total_token_usage = {'input_tokens': 0, 'output_tokens': 0}

        for article in articles:
            result = self._article_post_processor.process_article(article)
            if isinstance(result, tuple):  # Successful processing
                curated_article, token_usage = result
                curated_articles.append(curated_article)
                total_token_usage['input_tokens'] += token_usage['input_tokens']
                total_token_usage['output_tokens'] += token_usage['output_tokens']
            else:  # Failed processing
                failed_articles.append(result)

        return curated_articles, failed_articles, total_token_usage

    def _update_articles(self, curated_articles: List[CuratedGlobeArticle],
                         failed_articles: List[FailedGlobeArticle]) -> None:
        successful_ids = self._mongo_handler.update_articles(curated_articles)
        moved_ids = self._mongo_handler.move_failed_articles(failed_articles)

        self._logger.info(f"Successfully updated {len(successful_ids)} articles.")
        self._logger.info(f"Moved {len(moved_ids)} failed articles to failed_articles collection.")