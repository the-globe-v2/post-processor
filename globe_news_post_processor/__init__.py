# path: globe_news_post_processor/__init__.py
"""
This module contains the main GlobeNewsPostProcessor class for processing Globe news articles.

It handles fetching unprocessed articles, processing them, and updating the database
with the results.
"""

from typing import List, Tuple

import structlog

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import GlobeArticle, CuratedGlobeArticle, FailedGlobeArticle
from globe_news_post_processor.database.mongo_handler import MongoHandler
from globe_news_post_processor.post_process_pipeline import ArticlePostProcessor


class GlobeNewsPostProcessor:
    """
    Main class for processing Globe news articles.

    This class coordinates the fetching, processing, and updating of Globe news articles.
    """

    def __init__(self, config: Config):
        """
        Initialize the GlobeNewsPostProcessor.

        :param config: (Config) Configuration object containing necessary settings.
        """
        self._config = config
        self._logger = structlog.get_logger()
        self._mongo_handler = MongoHandler(config)
        self._article_post_processor = ArticlePostProcessor(config)

    def process_pending_articles(self) -> None:
        """
        Process all articles that have yet to be post processed in batches.

        This method continuously fetches and processes batches of unprocessed articles
        until no more articles are available.
        """
        batch_size = self._config.BATCH_SIZE
        while articles := self._fetch_article_batch(batch_size):
            curated_articles, failed_articles = self._process_batch(articles)
            self._update_articles(curated_articles, failed_articles)

    def _fetch_article_batch(self, batch_size: int) -> List[GlobeArticle]:
        """
        Fetch a batch of unprocessed articles from the database.

        :param batch_size: (int) The number of articles to fetch in this batch.

        :return: List[GlobeArticle]: A list of unprocessed GlobeArticle objects.
        """
        article_batch = self._mongo_handler.get_unprocessed_articles(batch_size)
        self._logger.debug(f"Fetched {len(article_batch)} articles.")
        return article_batch

    def _process_batch(self, articles: List[GlobeArticle]) -> Tuple[
        List[CuratedGlobeArticle], List[FailedGlobeArticle]]:
        """
        Process a batch of articles.

        :param articles: (List[GlobeArticle]) A list of GlobeArticle objects to process.

        :returns: Tuple[List[CuratedGlobeArticle], List[FailedGlobeArticle]]: A tuple containing
            a list of successfully processed articles and a list of failed articles.
        """
        processed_articles, failed_articles = self._article_post_processor.process_batch(articles)
        self._logger.info(f"Processed {len(processed_articles)} articles.")
        self._logger.info(f"Failed to process {len(failed_articles)} articles.")
        return processed_articles, failed_articles

    def _update_articles(self, curated_articles: List[CuratedGlobeArticle],
                         failed_articles: List[FailedGlobeArticle]) -> None:
        """
        Update the database with processed and failed articles.

        :param curated_articles: (List[CuratedGlobeArticle]) A list of successfully processed articles.
        :param failed_articles: (List[FailedGlobeArticle]) A list of articles that failed processing.
        """
        successful_ids = self._mongo_handler.update_articles(curated_articles)
        moved_ids = self._mongo_handler.move_failed_articles(failed_articles)

        self._logger.info(f"Successfully updated {len(successful_ids)} articles.")
        self._logger.info(f"Moved {len(moved_ids)} failed articles to failed_articles collection.")