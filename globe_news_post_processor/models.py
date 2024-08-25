# path: globe_news_post_processor/models.py
from bson import ObjectId
from pydantic import BaseModel, HttpUrl, Field, model_validator, field_validator, ConfigDict
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.language_code import LanguageAlpha2
from typing import Optional, List, Annotated, Literal, Any
from datetime import datetime


class GlobeArticle(BaseModel):
    """
    Represents a news article with various attributes.

    This class encapsulates all relevant information about a news article,
    including its content, metadata, and source information.

    Attributes:
        id (ObjectId): The unique identifier of the article in MongoDB.
        title (str): The headline or title of the article.
        url (Annotated[str, HttpUrl]): The web address where the article can be found.
        description (str): A brief summary or description of the article's content.
        date_published (datetime): The date and time when the article was originally published.
        provider (str): The name of the news outlet or platform that published the article.
        language (Optional[LanguageAlpha2]): The primary language of the article's content, in ISO 639-1 format.
        content (str): The main body text of the article.
        origin_country (CountryAlpha2): The country where the article was published, in ISO 3166-1 alpha-2 format.
        keywords (List[str]): A list of relevant keywords or tags associated with the article.
        source_api (str): The name or identifier of the API from which the article data was retrieved.
        schema_version (str): The version of the data schema used to structure this article's information.
        date_scraped (datetime): The date and time when the article was collected by the scraper.
        category (Optional[str]): The topical category or section under which the article is classified.
        authors (Optional[List[str]]): A list of the article's authors or contributors.
        related_countries (Optional[List[CountryAlpha2]]): Countries mentioned or relevant to the article's content.
        image_url (Optional[Annotated[str, HttpUrl]): The URL of the main image associated with the article.
        post_processed (bool): (irrelevant to this module) Will be true once the article is curated by globe_news_locator.
    """

    id: ObjectId = Field(..., alias='_id')
    title: str
    title_translated: Optional[str]
    url: Annotated[str, HttpUrl]
    description: str
    description_translated: Optional[str]
    date_published: datetime
    provider: str
    language: Optional[LanguageAlpha2]
    content: str
    origin_country: CountryAlpha2
    keywords: List[str]
    source_api: str
    schema_version: str
    date_scraped: datetime
    category: Optional[str] = None
    authors: Optional[List[str]] = None
    related_countries: Optional[List[CountryAlpha2]] = None
    image_url: Optional[Annotated[str, HttpUrl]] = None
    post_processed: bool

    model_config = ConfigDict(arbitrary_types_allowed=True)


class CuratedGlobeArticle(GlobeArticle):
    """
    Enhanced model for post-processed Globe articles, ensuring data integrity and curation.

    Inherits all attributes from GlobeArticle and applies additional post-processing logic,
    specifically removing the origin country from the list of related countries if present
    and ensuring the 'post_processed' flag is always set to True.

    Attributes:
        Inherits all attributes from the GlobeArticle class.
    Methods:
        set_post_processed_to_true: Ensures the 'post_processed' flag is always set
        remove_origin_country: Ensures the origin country is not listed among related countries.
    """

    # Since CuratedGlobeArticle isn't instantiated directly from MongoDB but rather from GlobeArticle,
    # we need to specify the 'id' field as an alias to '_id' to match the MongoDB document structure.
    id: ObjectId = Field(..., alias='id')

    @field_validator('post_processed', mode='before')
    def set_post_processed_to_true(cls, v: Any) -> bool:
        """
        Ensure the 'post_processed' flag is always set to True.
        """
        return True

    @model_validator(mode='after')
    def remove_origin_country(cls, model: Any) -> Any:
        """
        Remove the origin country from the list of related countries if present.
        """
        if model.origin_country and model.related_countries:
            model.related_countries = [
                country for country in model.related_countries
                if country != model.origin_country
            ]
        return model


class FailedGlobeArticle(GlobeArticle):
    """
    Data model for storing GlobeArticle objects that failed to be processed.
    """
    id: ObjectId = Field(..., alias='id')
    failure_reason: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class LLMArticleData(BaseModel):
    """
    Data model used by langchain to parse the LLM output and extract relevant information.
    """
    category: Literal['POLITICS', 'ECONOMY', 'TECHNOLOGY', 'SOCIETY', 'CULTURE', 'SPORTS', 'ENVIRONMENT']
    related_countries: List[CountryAlpha2]
    keywords: List[str] = Field(..., max_length=5)

