# tests/unit/test_post_processor_unit.py

import pytest

from globe_news_post_processor.models import CuratedGlobeArticle, FailedGlobeArticle, LLMArticleData
from globe_news_post_processor.post_process_pipeline import ArticlePostProcessor


@pytest.mark.unit
def test_process_article(mock_config, sample_globe_article, mocker):
    processor = ArticlePostProcessor(mock_config)
    mocker.patch.object(processor._llm_handler, 'process_article', return_value=(LLMArticleData(
        category='TECHNOLOGY',
        related_countries=['US', 'GB', 'CA'],
        keywords=['test', 'article', 'technology']
    ), {'input_tokens': 100, 'output_tokens': 50}))
    mocker.patch.object(processor._translator, 'translate', return_value='Translated text')

    result, token_usage = processor.process_article(sample_globe_article)

    assert isinstance(result, CuratedGlobeArticle)
    assert result.category == 'TECHNOLOGY'
    assert result.related_countries == ['US', 'CA']
    assert result.keywords == ['test', 'article', 'technology']
    assert result.title_translated == 'Test Article'
    assert result.description_translated == 'This is a test article'
    assert token_usage == {'input_tokens': 100, 'output_tokens': 50}


@pytest.mark.unit
def test_process_article_failure(mock_config, sample_globe_article, mocker):
    processor = ArticlePostProcessor(mock_config)
    mocker.patch.object(processor._llm_handler, 'process_article', side_effect=Exception('Test error'))

    result = processor.process_article(sample_globe_article)

    assert isinstance(result, FailedGlobeArticle)
    assert result.failure_reason == 'Test error'
