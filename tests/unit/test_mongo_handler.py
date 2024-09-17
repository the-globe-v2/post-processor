# path: tests/unit/test_mongo_handler.py

import pytest
from bson import ObjectId
from pymongo.errors import PyMongoError

from globe_news_post_processor.database.mongo_handler import MongoHandler, MongoHandlerError


@pytest.fixture
def mock_mongo_client(mocker):
    mock_client = mocker.patch('pymongo.MongoClient')
    mock_db = mocker.MagicMock()
    mock_collection = mocker.MagicMock()
    mock_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    mock_db.list_collection_names.return_value = ['articles', 'failed_articles']
    mock_client.return_value.list_database_names.return_value = ['test_db']
    return mock_client.return_value


@pytest.fixture
def mongo_handler(mock_config, mock_mongo_client):
    return MongoHandler(mock_config, client=mock_mongo_client)


@pytest.mark.unit
def test_init_success(mongo_handler, mock_mongo_client, log_output):
    assert mongo_handler._db.name == mock_mongo_client[mongo_handler._config.MONGO_DB].name
    assert "articles" in mongo_handler._db.list_collection_names()
    assert "failed_articles" in mongo_handler._db.list_collection_names()
    assert log_output.entries[0]["event"] == "MongoDB connection and permissions verified successfully"


@pytest.mark.slow
def test_init_failure(mock_config, mocker):
    mocker.patch('pymongo.MongoClient', side_effect=PyMongoError("Connection failed"))
    with pytest.raises(MongoHandlerError):
        MongoHandler(mock_config)


@pytest.mark.unit
def test_update_articles_success(mongo_handler, sample_curated_article):
    mongo_handler._articles.update_one.return_value.modified_count = 1

    curated_articles = [
        sample_curated_article
    ]

    updated_ids = mongo_handler.update_articles(curated_articles)

    assert len(updated_ids) == 1
    assert updated_ids[0] == ObjectId("666f6f2d6261722d71757578")
    assert mongo_handler._articles.update_one.called


@pytest.mark.unit
def test_move_failed_articles_success(mongo_handler, sample_failed_article, log_output):
    mongo_handler._articles.find_one.return_value = {"_id": "666f6f2d6261722d71757578", "title": "Failed Article"}
    mongo_handler._failed_articles.insert_one.return_value.inserted_id = "666f6f2d6261722d71757578"
    mongo_handler._articles.delete_one.return_value.deleted_count = 1

    failed_articles = [
        sample_failed_article
    ]

    moved_ids = mongo_handler.move_failed_articles(failed_articles)

    assert len(moved_ids) == 1
    assert moved_ids[0] == ObjectId("666f6f2d6261722d71757578")
    assert mongo_handler._articles.find_one.called
    assert mongo_handler._failed_articles.insert_one.called
    assert mongo_handler._articles.delete_one.called


@pytest.mark.unit
def test_move_failed_articles_not_found(mongo_handler, sample_failed_article, log_output):
    mongo_handler._articles.find_one.return_value = None

    failed_articles = [
        sample_failed_article
    ]

    moved_ids = mongo_handler.move_failed_articles(failed_articles)

    assert len(moved_ids) == 0
    assert mongo_handler._articles.find_one.called
    assert mongo_handler._failed_articles.insert_one.call_count == 1  # Called once in permission check
    assert mongo_handler._articles.delete_one.call_count == 1  # Called once in permission check
    assert log_output.entries[1]["event"] == "Article 666f6f2d6261722d71757578 not found in articles collection"


@pytest.mark.unit
def test_move_failed_article_duplicate(mongo_handler, sample_failed_article, log_output):
    mongo_handler._articles.find_one.return_value = {"_id": "666f6f2d6261722d71757578", "title": "Failed Article"}
    mongo_handler._failed_articles.insert_one.return_value.inserted_id = None

    failed_articles = [
        sample_failed_article
    ]

    moved_ids = mongo_handler.move_failed_articles(failed_articles)

    assert len(moved_ids) == 0
    assert mongo_handler._articles.find_one.called
    assert mongo_handler._failed_articles.insert_one.called
    assert mongo_handler._articles.delete_one.call_count == 0
    assert log_output.entries[1][
               "event"] == "Failed to insert article 666f6f2d6261722d71757578 into failed_articles collection"


@pytest.mark.unit
def test_get_unprocessed_articles(mongo_handler, sample_globe_article):
    mock_articles = [
        {**sample_globe_article.model_dump(exclude="id"), "_id": ObjectId("666f6f2d6261722d71757578")},
        {**sample_globe_article.model_dump(exclude="id"), "_id": ObjectId("666f6f2d6261722d71757579")},
    ]
    mongo_handler._articles.find().sort.return_value = mock_articles

    unprocessed_articles = mongo_handler.get_unprocessed_articles(10)

    assert len(unprocessed_articles) == 2
    assert mongo_handler._articles.find.called
    assert mongo_handler._articles.find.call_args[0][0] == {
        "post_processed": {"$ne": True},
        "schema_version": mongo_handler._config.SCHEMA_VERSION
    }


@pytest.mark.unit
def test_get_unprocessed_articles_empty(mongo_handler):
    mongo_handler._articles.find().sort.return_value = []
    unprocessed_articles = mongo_handler.get_unprocessed_articles(10)
    assert len(unprocessed_articles) == 0


@pytest.mark.unit
def test_get_unprocessed_articles_exception(mongo_handler, log_output):
    mongo_handler._articles.find.side_effect = PyMongoError("Database error")
    unprocessed_articles = mongo_handler.get_unprocessed_articles(10)
    assert len(unprocessed_articles) == 0
    assert log_output.entries[-1]["event"] == "Error fetching unprocessed articles: Database error"


@pytest.mark.unit
def test_update_articles_partial_success(mongo_handler, sample_curated_article):
    mongo_handler._articles.update_one.side_effect = [
        type('obj', (object,), {'modified_count': 1})(),
        type('obj', (object,), {'modified_count': 0})(),
    ]
    curated_articles = [sample_curated_article, sample_curated_article]
    updated_ids = mongo_handler.update_articles(curated_articles)
    assert len(updated_ids) == 1
    assert updated_ids[0] == ObjectId("666f6f2d6261722d71757578")


@pytest.mark.unit
def test_update_articles_exception(mongo_handler, sample_curated_article, log_output):
    mongo_handler._articles.update_one.side_effect = PyMongoError("Update error")
    curated_articles = [sample_curated_article]
    updated_ids = mongo_handler.update_articles(curated_articles)
    assert len(updated_ids) == 0
    assert log_output.entries[-1]["event"] == "Error updating article: Update error"


@pytest.mark.unit
def test_move_failed_articles_delete_failure(mongo_handler, sample_failed_article, log_output):
    mongo_handler._articles.find_one.return_value = {"_id": "666f6f2d6261722d71757578", "title": "Failed Article"}
    mongo_handler._failed_articles.insert_one.return_value.inserted_id = "666f6f2d6261722d71757578"
    mongo_handler._articles.delete_one.return_value.deleted_count = 0
    failed_articles = [sample_failed_article]
    moved_ids = mongo_handler.move_failed_articles(failed_articles)
    assert len(moved_ids) == 0
    assert log_output.entries[-1][
               "event"] == "Failed to delete article 666f6f2d6261722d71757578 from articles collection"


@pytest.mark.unit
def test_move_failed_articles_duplicate_key(mongo_handler, sample_failed_article, log_output):
    class MockOperationFailure(PyMongoError):
        def __init__(self):
            self._OperationFailure__code = 11000
            self._OperationFailure__details = {"keyValue": {"_id": "666f6f2d6261722d71757578"}}

    mongo_handler._articles.find_one.return_value = {"_id": "666f6f2d6261722d71757578", "title": "Failed Article"}
    mongo_handler._failed_articles.insert_one.side_effect = MockOperationFailure()
    failed_articles = [sample_failed_article]
    moved_ids = mongo_handler.move_failed_articles(failed_articles)
    assert len(moved_ids) == 0
    assert log_output.entries[-1][
               "event"] == "Article 666f6f2d6261722d71757578 already exists in failed_articles collection, deleting original."
