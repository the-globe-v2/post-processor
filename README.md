# Globe Post Processor

# General

**The Globe Post Processor** is part of a larger three-process structure designed to enhance news articles with additional information for use in the Globe App. This module takes articles from a MongoDB database, processes them using Large Language Models (LLMs), and enriches them with metadata such as related countries, keywords, and categories.

## Key Features

- Uses Langchain to communicate with LLMs (currently Azure OpenAI’s GPT-4o-mini)
- Extracts related countries, keywords, and categories from article content
- Translates article titles and descriptions to English if necessary
- Uploads processed articles back to the database with additional metadata
- Handles processing failures gracefully

## [System Architecture](https://www.notion.so/Globe-Post-Processor-6f84c388a8c64a809c62b869db2aaf89?pvs=21)

The Globe Post Processor is part of a three-step process:

1. **Article Scraping**: Articles are initially scraped and stored in the database (handled by GlobeNewsScraper, not part of this module).
2. **Post-Processing** (this module):
    - Articles are fetched from the database
    - LLM processes the content to extract metadata
    - Titles and descriptions are translated if not in English
    - Processed articles are uploaded back to the database
3. **Display**: Processed articles are used by the Globe App for display in a 3D, interactive Globe (handled by separate module).

## Installation

1. Clone the repository
2. Install dependencies:
    
    ```
    pip install -r requirements.txt
    ```
    
3. Copy `.env.template` to `.env` and fill in the required configuration values or set them as environment variables.

## Usage

To run the post-processor:

```
python main.py --env PROD | DEV
```

For more detailed usage instructions, see [Setup Guide](https://www.notion.so/Globe-Post-Processor-6f84c388a8c64a809c62b869db2aaf89?pvs=21).

## Documentation

For more detailed documentation, please refer to the following:

- [Configuration](https://www.notion.so/Globe-Post-Processor-6f84c388a8c64a809c62b869db2aaf89?pvs=21)
- [LLM Handler Documentation](https://www.notion.so/Globe-Post-Processor-6f84c388a8c64a809c62b869db2aaf89?pvs=21)
- [Azure Translator AI](https://www.notion.so/Globe-Post-Processor-6f84c388a8c64a809c62b869db2aaf89?pvs=21)
- [Setup Guide](https://www.notion.so/Globe-Post-Processor-6f84c388a8c64a809c62b869db2aaf89?pvs=21)
- [System Architecture](https://www.notion.so/Globe-Post-Processor-6f84c388a8c64a809c62b869db2aaf89?pvs=21)
- [Logging](https://www.notion.so/Globe-Post-Processor-6f84c388a8c64a809c62b869db2aaf89?pvs=21)

## Performance Considerations

The Globe Post Processor's performance is constrained by Azure OpenAI's API rate limit of about 30,000 tokens per minute for Pay-As-You-Go plans, allowing processing of one article every two seconds on average. While OpenAI offers higher token-per-minute rates at increased costs, `GPT-4o-mini` provides the best balance of price and performance. Self-hosted models like [phi3.5](https://ollama.com/library/phi3.5) or [Gemma2B](https://ollama.com/library/gemma2:2b) lack the necessary accuracy for reliable article data extraction.

## Future Improvements

- Add monitoring and telemetry for better performance tracking
- Implement support for additional LLM providers in case any others become competitive.
- https://github.com/the-globe-v2/post-processor/issues