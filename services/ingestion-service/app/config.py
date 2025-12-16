import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "ingestion-service"
    host: str = "0.0.0.0"
    port: int = 8001
    
    # External APIs
    coinmarketcap_api_key: str = os.getenv("COINMARKETCAP_API_KEY", "")
    coingecko_api_key: str = os.getenv("COINGECKO_API_KEY", "")
    news_api_key: str = os.getenv("NEWS_API_KEY", "")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # Message queues
    fact_extraction_queue: str = "fact_extraction_queue"
    ingestion_status_channel: str = "ingestion_status"
    
    # Rate limiting
    api_rate_limit: int = 100  # requests per minute
    
    class Config:
        env_file = ".env"

settings = Settings()