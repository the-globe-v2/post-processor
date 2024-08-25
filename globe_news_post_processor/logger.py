import os
import logging
import structlog
from logging.handlers import RotatingFileHandler


def configure_logging(log_level: str, logging_dir: str = 'logs', environment: str = 'dev') -> None:
    logger_level = logging.INFO if environment == 'prod' else getattr(logging, log_level.upper(), logging.INFO)

    # Ignore DEBUG messages from specific loggers
    for logger_name in ['urllib3', 'asyncio', 'httpcore', 'pymongo']:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    # Ignore DEBUG messages from specific loggers
    for logger_name in ['openai', 'httpx']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False

    # Ensure the logging directory exists
    log_dir = os.path.dirname(f'{logging_dir}/globe_news_scraper.log')
    os.makedirs(log_dir, exist_ok=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,  # type: ignore[attr-defined]
        cache_logger_on_first_use=True,
    )

    # Set up formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer() if environment == 'dev' else structlog.processors.JSONRenderer(),
    )

    # Add handler to the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logger_level)

    # Remove all existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add StreamHandler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Add FileHandler
    file_handler = RotatingFileHandler(
        f'{logging_dir}/globe_news_scraper.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
