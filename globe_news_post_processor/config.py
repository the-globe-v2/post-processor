from typing import Dict, List, Literal
from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # Common Configuration
    LOG_LEVEL: Literal['debug', 'info', 'warning', 'error'] = 'info'
    LOGGING_DIR: str = Field(default='logs')
    MONGO_URI: str
    MONGO_DB: str
    BATCH_SIZE: int = 20

    # LLM Configuration
    LLM_PROVIDER: Literal['azure_openai'] = 'azure_openai'
    LLM_API_KEY: SecretStr
    LLM_ENDPOINT: HttpUrl
    LLM_API_VERSION: str = '2024-04-01-preview'
    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 100
    MAX_RETRIES: int = 2
    SYSTEM_PROMPT_FILE: str = 'azure_openai_system_prompt.txt'
    FEW_SHOT_EXAMPLES_FILE: str = 'few_shot_examples.json'

    # Azure Translator Configuration
    AZURE_TRANSLATOR_API_KEY: SecretStr
    AZURE_TRANSLATOR_ENDPOINT: HttpUrl
    AZURE_TRANSLATOR_LOCATION: str



def get_config() -> Config:
    config = Config()  # type: ignore
    if config.LLM_PROVIDER != 'azure_openai':
        raise ValueError(f"Unsupported LLM provider: {config.LLM_PROVIDER}")
    return config