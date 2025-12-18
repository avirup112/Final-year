import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "llm-generator-service"
    host: str = "0.0.0.0"
    port: int = 8006
    
    # Groq API
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = "mixtral-8x7b-32768"
    groq_temperature: float = 0.1
    groq_max_tokens: int = 2000
    
    # Vector retrieval service
    vector_service_url: str = "http://vector-retrieval-service:8005"
    
    # Hallucination detection
    hallucination_threshold: float = 0.3
    fact_verification_enabled: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()