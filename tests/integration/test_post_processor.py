# tests/integration/test_post_processor.py

import pytest
from globe_news_post_processor import GlobeNewsPostProcessor, CuratedGlobeArticle, FailedGlobeArticle


@pytest.mark.slow
@pytest.mark.integration
def test_process_pending_articles(mock_config, sample_globe_article, mocker):
    mocker.patch('globe_news_post_processor.MongoHandler')
    mocker.patch('globe_news_post_processor.ArticlePostProcessor.process_article', return_value=(
        mocker.Mock(spec=CuratedGlobeArticle), {'input_tokens': 100, 'output_tokens': 50}
    ))

    processor = GlobeNewsPostProcessor(mock_config)
    mocker.patch.object(processor._mongo_handler, 'get_unprocessed_articles', return_value=[sample_globe_article])
    mocker.patch.object(processor._mongo_handler, 'update_articles', return_value=['123'])

    processor.process_pending_articles()

    processor._mongo_handler.get_unprocessed_articles.assert_called_once()
    processor._mongo_handler.update_articles.assert_called_once()


@pytest.mark.integration
def test_process_pending_articles_with_failure(mock_config, sample_globe_article, mocker):
    mocker.patch('globe_news_post_processor.MongoHandler')
    mocker.patch('globe_news_post_processor.ArticlePostProcessor.process_article',
                 return_value=mocker.Mock(spec=FailedGlobeArticle))

    processor = GlobeNewsPostProcessor(mock_config)
    mocker.patch.object(processor._mongo_handler, 'get_unprocessed_articles', return_value=[sample_globe_article])
    mocker.patch.object(processor._mongo_handler, 'move_failed_articles', return_value=['456'])

    processor.process_pending_articles()

    processor._mongo_handler.get_unprocessed_articles.assert_called_once()
    processor._mongo_handler.move_failed_articles.assert_called_once()