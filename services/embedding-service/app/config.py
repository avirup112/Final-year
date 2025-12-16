import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "embedding-service"
    host: str = "0.0.0.0"
    port: int = 8003
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # ChromaDB
    chroma_url: str = os.getenv("CHROMA_URL", "http://chromadb:8000")
    
    # Message queues
    embedding_queue: str = "embedding_queue"
    storage_queue: str = "storage_queue"
    
    # Embedding model
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    
    class Config:
        env_file = ".env"

settings = Settings()