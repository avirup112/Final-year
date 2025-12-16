from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    RECOVERING = "recovering"

class CryptoDataSource(str, Enum):
    COINMARKETCAP = "coinmarketcap"
    COINGECKO = "coingecko"
    BINANCE = "binance"
    NEWS_API = "news_api"
    REDDIT = "reddit"
    TWITTER = "twitter"

class FactType(str, Enum):
    PRICE = "price"
    MARKET_CAP = "market_cap"
    NEWS = "news"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    REGULATORY = "regulatory"

class CryptoFact(BaseModel):
    id: Optional[str] = None
    symbol: str
    fact_type: FactType
    content: str
    source: CryptoDataSource
    confidence_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retrieval_time: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    verified: bool = False
    
    def is_data_fresh(self, max_age_minutes: int = 5) -> bool:
        """Check if the fact data is fresh"""
        age = datetime.utcnow() - self.retrieval_time
        return age.total_seconds() < (max_age_minutes * 60)
    
    def update_retrieval_time(self):
        """Update the retrieval time to current time"""
        self.retrieval_time = datetime.utcnow()

class IngestionRequest(BaseModel):
    source: CryptoDataSource
    symbols: List[str]
    data_types: List[FactType]
    priority: int = Field(default=1, ge=1, le=10)

class EmbeddingRequest(BaseModel):
    text: str
    fact_id: str
    model: str = "sentence-transformers/all-MiniLM-L6-v2"

class EmbeddingResponse(BaseModel):
    fact_id: str
    embedding: List[float]
    model: str

class QueryRequest(BaseModel):
    query: str
    symbols: Optional[List[str]] = None
    fact_types: Optional[List[FactType]] = None
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class QueryResponse(BaseModel):
    query: str
    facts: List[CryptoFact]
    generated_answer: str
    confidence_score: float
    hallucination_detected: bool
    sources: List[str]

class HealthCheck(BaseModel):
    service_name: str
    status: ServiceStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
    response_time_ms: Optional[float] = None

class HealingAction(BaseModel):
    service_name: str
    action_type: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = False
    error_message: Optional[str] = None

class NotificationEvent(BaseModel):
    event_type: str
    service_name: str
    message: str
    severity: str = Field(default="info")  # info, warning, error, critical
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)