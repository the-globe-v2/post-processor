import argparse
import time
from datetime import datetime
import structlog
from croniter import croniter

from globe_news_post_processor import GlobeNewsPostProcessor
from globe_news_post_processor.config import get_config
from globe_news_post_processor.logger import configure_logging


def process_articles(config):
    logger = structlog.get_logger()
    logger.info("Starting GlobeNewsPostProcessor")

    try:
        processor = GlobeNewsPostProcessor(config)
        processor.process_pending_articles()
    except Exception as e:
        logger.critical("Error while running GlobeNewsPostProcessor", error=str(e))


def main():
    parser = argparse.ArgumentParser(description="GlobeNewsPostProcessor")
    parser.add_argument('--env', type=str, choices=['dev', 'prod', 'test'], default='dev',
                        help="Specify the environment (dev, prod or test)")
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the logging level")
    parser.add_argument('--cron-schedule', type=str, default="30 2 * * *",
                        help="Set the cron schedule (e.g., '30 2 * * *' for daily at 2:30 AM)")
    parser.add_argument('--run-now', action='store_true',
                        help="Run the post processor immediately on startup")

    args = parser.parse_args()

    # Get configuration, prioritizing command-line arguments, then environment variables, then defaults
    config = get_config()

    # Override configuration with command-line arguments
    config.ENV = args.env or config.ENV
    config.LOG_LEVEL = args.log_level or config.LOG_LEVEL
    cron_schedule = args.cron_schedule or config.CRON_SCHEDULE
    run_now = args.run_now or config.RUN_ON_STARTUP

    # Configure logging
    configure_logging(log_level=config.LOG_LEVEL, logging_dir=config.LOGGING_DIR, environment=config.ENV)
    logger = structlog.get_logger()

    # Log the configuration
    logger.info("GlobeNewsPostProcessor Configuration",
                env=config.ENV,
                log_level=config.LOG_LEVEL,
                cron_schedule=cron_schedule,
                run_now=run_now)

    # Run once immediately on startup if specified
    if run_now:
        logger.info("Running initial post processing")
        process_articles(config)

    # Set up the cron iterator
    cron = croniter(cron_schedule, datetime.now())

    # Main loop
    while True:
        next_run = cron.get_next(datetime)
        logger.info(f"Next run scheduled for: {next_run}")

        while datetime.now() < next_run:
            time.sleep(60)  # Sleep for 60 seconds before checking again

        logger.info("Starting scheduled post processing, and checking for new articles")
        process_articles(config)


if __name__ == "__main__":
    main()