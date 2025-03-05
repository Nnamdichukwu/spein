from typing import Optional
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Spein"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_HOST: str = os.getenv("DATABASE_HOST")
    DATABASE_PORT: str = os.getenv("DATABASE_PORT")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD")
    DATABASE_USER: str = os.getenv("DATABASE_USER")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME")
    ROBOTSTXT_OBEY: bool = True
    CONCURRENT_REQUESTS: int = 16
    DOWNLOAD_DELAY: int = 1
    COOKIES_ENABLED: bool = False
    SPIDER_MIDDLEWARES: dict = {
        'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': None
    }
    MEDIA_ALLOW_REDIRECTS: bool = True
    DOWNLOADER_MIDDLEWARES: dict = {
        'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
        'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
    }
    DOWNLOAD_TIMEOUT: int = 180
    RETRY_TIMES: int = 3
    RETRY_HTTP_CODES: list = [500, 502, 503, 504, 522, 524, 408, 429]
   
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
