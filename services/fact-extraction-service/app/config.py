import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "fact-extraction-service"
    host: str = "0.0.0.0"
    port: int = 8002
    
    # Groq API
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = "mixtral-8x7b-32768"
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # Message queues
    fact_extraction_queue: str = "fact_extraction_queue"
    embedding_queue: str = "embedding_queue"
    extraction_status_channel: str = "extraction_status"
    
    # Processing settings
    batch_size: int = 10
    max_retries: int = 3
    
    class Config:
        env_file = ".env"

settings = Settings()