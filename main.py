import argparse
import logging
import structlog

from globe_news_post_processor.logger import configure_logging
from globe_news_post_processor import GlobeNewsPostProcessor
from globe_news_post_processor.config import get_config


def main() -> None:
    parser = argparse.ArgumentParser(description="GlobeNewsPostProcessor")
    parser.add_argument('--env', type=str, choices=['dev', 'prod', 'test'], default='dev',
                        help="Specify the environment (dev, prod or test)")
    args = parser.parse_args()

    config = get_config()
    configure_logging(log_level='debug', logging_dir=config.LOGGING_DIR, environment=args.env)

    logger = structlog.get_logger()
    logger.info("Starting GlobeNewsPostProcessor", environment=args.env)

    try:
        processor = GlobeNewsPostProcessor(config)
        processor.process_pending_articles()
    except Exception as e:
        logger.exception("An error occurred during processing", error=str(e))
    else:
        logger.info("GlobeNewsPostProcessor completed successfully")

if __name__ == "__main__":
    main()