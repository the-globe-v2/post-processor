# path: globe_news_post_processor/database/mongo_handler.py

from datetime import datetime, timezone
from typing import List, Optional

import structlog
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import GlobeArticle, CuratedGlobeArticle, FailedGlobeArticle


class MongoHandlerError(Exception):
    """Custom exception for errors in the MongoHandler class."""
    pass


class MongoHandler:
    """
    Handles MongoDB operations for the Globe News Post Processor.

    This class manages connections to MongoDB and provides methods for
    fetching, updating, and moving articles in the database.
    """

    def __init__(self, config: Config, client: Optional[MongoClient] = None):
        """
        Initialize the MongoHandler with the provided configuration.

        :param config: Configuration object containing MongoDB settings.
        :param client: Optional MongoClient instance to use for the connection.
        :raises MongoHandlerError: If the MongoDB connection or any checks fail.
        """
        self._logger = structlog.get_logger()
        self._config = config
        try:
            self._client = client or MongoClient(config.MONGO_URI)
            self._db = self._client[config.MONGO_DB]
            self._articles = self._db.articles
            self._failed_articles = self._db.failed_articles

            # Check connection
            self._client.admin.command('ping')

            # Check database existence
            if config.MONGO_DB not in self._client.list_database_names():
                raise MongoHandlerError(f"Database '{config.MONGO_DB}' does not exist")

            # Check existence of collections
            for collection in ['articles', 'failed_articles']:
                if collection not in self._db.list_collection_names():
                    raise MongoHandlerError(f"Collection '{collection}' does not exist")

            # Check permissions
            self._check_permissions()

            self._logger.info("MongoDB connection and permissions verified successfully")
        except PyMongoError as e:
            raise MongoHandlerError(f"Failed to initialize MongoDB connection: {str(e)}")
        except Exception as e:
            raise MongoHandlerError(f"Unexpected error occurred: {str(e)}")

    def get_unprocessed_articles(self, batch_size: int) -> List[GlobeArticle]:
        """
        Fetch articles that have not been post-processed, limited to batch size and sorted by latest.

        :param batch_size: Number of articles to fetch.
        :return: List of unprocessed GlobeArticle objects.
        """
        try:
            # Query for unprocessed articles with matching schema version
            cursor = self._articles.find(
                {
                    "post_processed": {"$ne": True},
                    "schema_version": self._config.SCHEMA_VERSION
                },
                limit=batch_size
            ).sort([("post_processed", 1), ("date_scraped", -1)])

            # Convert MongoDB documents to GlobeArticle objects
            return [GlobeArticle(**doc) for doc in cursor]
        except PyMongoError as e:
            self._logger.error(f"Error fetching unprocessed articles: {str(e)}")
            return []
        except Exception as e:
            self._logger.error(f"Unexpected error occurred: {str(e)}")
            return []

    def update_articles(self, curated_articles: List[CuratedGlobeArticle]) -> List[ObjectId]:
        """
        Update the processed articles in the database with curated information.

        :param curated_articles: List of CuratedGlobeArticle objects to update.
        :return: List of ObjectIds of successfully updated articles.
        """
        updated_ids = []
        try:
            for curated_article in curated_articles:
                # Update each article with new information
                result = self._articles.update_one(
                    {"_id": curated_article.id},
                    {
                        "$set": {
                            "post_processed": True,
                            "category": curated_article.category,
                            "related_countries": curated_article.related_countries,
                            "title_translated": curated_article.title_translated,
                            "description_translated": curated_article.description_translated
                        },
                        "$addToSet": {
                            "keywords": {
                                "$each": curated_article.keywords
                            }
                        }
                    }
                )
                if result.modified_count > 0:
                    updated_ids.append(curated_article.id)
        except PyMongoError as e:
            self._logger.error(f"Error updating article: {str(e)}")

        return updated_ids

    def move_failed_articles(self, failed_articles: List[FailedGlobeArticle]) -> List[ObjectId]:
        """
        Move failed articles to a separate collection and remove them from the main collection.

        :param failed_articles: List of FailedGlobeArticle objects to move.
        :return: List of ObjectIds of successfully moved articles.
        """
        moved_ids = []
        try:
            for failed_article in failed_articles:
                # Find the article in the articles collection
                article = self._articles.find_one({"_id": failed_article.id})

                if article:
                    # Add failure reason to the article document
                    article["failure_reason"] = failed_article.failure_reason

                    # Insert the article into the failed_articles collection
                    result = self._failed_articles.insert_one(article)

                    if result.inserted_id:
                        # If insertion was successful, remove the article from the original collection
                        delete_result = self._articles.delete_one({"_id": failed_article.id})

                        if delete_result.deleted_count > 0:
                            moved_ids.append(failed_article.id)
                        else:
                            self._logger.warning(
                                f"Failed to delete article {failed_article.id} from articles collection")
                    else:
                        self._logger.warning(
                            f"Failed to insert article {failed_article.id} into failed_articles collection")
                else:
                    self._logger.warning(f"Article {failed_article.id} not found in articles collection")

        except PyMongoError as e:
            # Handle duplicate key errors (article already exists in failed_articles collection)
            if e._OperationFailure__code == 11000:  # type: ignore
                error_val = list(e._OperationFailure__details['keyValue'].values())[0]  # type: ignore
                self._logger.warning(
                    f"Article {error_val} already exists in failed_articles collection, deleting original.")  # type: ignore
                self._articles.delete_one(e._OperationFailure__details["keyValue"])  # type: ignore
            else:
                self._logger.error(f"Error moving failed articles: {str(e)}")

        return moved_ids

    def _check_permissions(self) -> None:
        """
        Check the necessary permissions for the MongoDB operations.

        This method checks if the MongoDB user has the required permissions to perform
        read, write on  'articles' and 'failed_articles' collection.

        :raises OperationFailure: If any of the permissions checks fail.
        """
        # Check read permission
        self._articles.find_one()

        # Check write permission
        test_doc = {
            "_id": "test",
            "title": "Test Article Title",
            "url": "https://example.com/test-article",
            "description": "This is a test article description.",
            "date_published": datetime.now(timezone.utc),
            "provider": "Test News Provider",
            "content": "This is the main content of the test article.",
            "origin_country": "FR",
            "source_api": "test_api",
            "schema_version": "1.1",
            "date_scraped": datetime.now(timezone.utc),
            "post_processed": False,
            "language": "fr",
            "keywords": ["test", "article"],
            "category": "SOCIETY",
            "authors": ["Test Author"],
            "related_countries": ["DE", "ES"],
            "image_url": "https://example.com/test-image.jpg"
        }
        failed_doc = test_doc.copy()
        failed_doc.update({
            "related_countries": None,
            "keywords": [],
            "post_processed": False,
            "failure_reason": "Test failure reason"
        })

        self._articles.insert_one(test_doc)
        self._articles.delete_one({"_id": "test"})
        self._failed_articles.insert_one(failed_doc)
        self._failed_articles.delete_one({"_id": "test"})
