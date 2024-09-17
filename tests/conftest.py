# tests/conftest.py

from datetime import datetime, timezone

import pytest
import structlog
from bson import ObjectId
from pydantic import HttpUrl
from structlog.testing import LogCapture

from globe_news_post_processor.config import Config
from globe_news_post_processor.models import GlobeArticle, CuratedGlobeArticle, FailedGlobeArticle


@pytest.fixture
def mock_config():
    return Config(
        LOG_LEVEL='debug',
        LOGGING_DIR='./test_logs',
        MONGO_URI='mongodb://localhost:27017',
        MONGO_DB='test_db',
        LLM_PROVIDER='azure_openai',
        LLM_API_KEY='mock_key',
        LLM_ENDPOINT=HttpUrl('https://mock-endpoint.openai.azure.com'),
        LLM_API_VERSION='2024-04-01-preview',
        AZURE_TRANSLATOR_API_KEY='mock_translator_key',
        AZURE_TRANSLATOR_ENDPOINT=HttpUrl('https://api.cognitive.microsofttranslator.com'),
        AZURE_TRANSLATOR_LOCATION='eastus'
    )


@pytest.fixture(name="log_output")
def fixture_log_output():
    return LogCapture()


@pytest.fixture(autouse=True)
def fixture_configure_structlog(log_output):
    structlog.configure(
        processors=[log_output]
    )
    yield
    # Reset configuration after each test
    structlog.reset_defaults()


@pytest.fixture
def capturing_logger_factory():
    return structlog.testing.CapturingLoggerFactory()


@pytest.fixture
def sample_globe_article():
    return GlobeArticle(
        _id=ObjectId("666f6f2d6261722d71757578"),
        title="Test Article",
        title_translated=None,
        url="https://example.com/test",
        description="This is a test article",
        description_translated=None,
        date_published=datetime.now(timezone.utc),
        provider="Test Provider",
        language="en",
        content="This is the content of the test article.",
        origin_country="GB",
        keywords=["test", "article"],
        source_api="TestAPI",
        schema_version="1.1",
        date_scraped=datetime.now(timezone.utc),  # Corrected the field name
        category=None,
        authors=["John Doe"],
        related_countries=None,
        image_url="https://example.com/image.jpg",
        post_processed=False
    )


@pytest.fixture
def sample_curated_article():
    return CuratedGlobeArticle(
        id=ObjectId("666f6f2d6261722d71757578"),
        title="Article 1",
        url="https://example.com/1",
        description="Curated description 1",
        date_published=datetime.now(timezone.utc),
        date_scraped=datetime.now(timezone.utc),
        provider="Test Provider",
        language="cs",
        content="Article content 1",
        origin_country="CZ",
        schema_version="1.1",
        keywords=["curated", "article"],
        source_api="TestAPI",
        category="POLITICS",
        related_countries=["DE", "SK", "PL"],
        title_translated="Translated Title 1",
        description_translated="Translated Description 1",
        post_processed=True,
    )


@pytest.fixture
def sample_failed_article():
    return FailedGlobeArticle(
        id=ObjectId("666f6f2d6261722d71757578"),
        title="Failed Test Article",
        title_translated=None,
        url="https://example.com/failed",
        description="This is a failed test article",
        description_translated=None,
        date_published=datetime.now(timezone.utc),
        provider="Failed Provider",
        language="en",
        content="This is the content of the failed test article.",
        origin_country="US",
        keywords=["failed", "test"],
        source_api="FailedAPI",
        schema_version="1.1",
        date_scraped=datetime.now(timezone.utc),
        category=None,
        authors=["Bob Johnson"],
        related_countries=None,
        image_url="https://example.com/failed-image.jpg",
        post_processed=False,
        failure_reason="Test failure reason"
    )
