from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class FactType(str, Enum):
    PRICE = "price"
    VOLUME = "volume"
    MARKET_CAP = "market_cap"
    TECHNICAL = "technical"
    NEWS = "news"
    REGULATORY = "regulatory"
    SENTIMENT = "sentiment"
    ANOMALY = "anomaly"

class DataSource(str, Enum):
    COINGECKO = "coingecko"
    COINMARKETCAP = "coinmarketcap"
    NEWS_API = "news_api"

class ExtractedFact(BaseModel):
    """Structured fact extracted from raw crypto data"""
    token: str = Field(..., description="Cryptocurrency token symbol")
    attribute: str = Field(..., description="The attribute being described (price, volume, etc.)")
    value: Any = Field(..., description="The value of the attribute")
    timestamp: datetime = Field(..., description="When this fact was observed")
    source: DataSource = Field(..., description="Source of the data")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score 0-1")
    fact_type: FactType = Field(..., description="Type of fact")
    raw_data: Optional[Dict[str, Any]] = Field(default=None, description="Original raw data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('token')
    def validate_token(cls, v):
        return v.upper().strip()
    
    @validator('attribute')
    def validate_attribute(cls, v):
        return v.lower().strip()

class RawCryptoData(BaseModel):
    """Raw crypto data from message queue"""
    source: str
    symbol: str
    data: Dict[str, Any]
    timestamp: str
    message_id: str

class AnomalyDetection(BaseModel):
    """Anomaly detection result"""
    is_anomaly: bool
    anomaly_type: str
    severity: float = Field(ge=0.0, le=1.0)
    description: str
    expected_range: Optional[Dict[str, float]] = None

class ExtractionResult(BaseModel):
    """Result of fact extraction process"""
    facts: List[ExtractedFact]
    anomalies: List[AnomalyDetection]
    processing_time: float
    success: bool
    error_message: Optional[str] = None

class ExtractionStats(BaseModel):
    """Statistics for extraction service"""
    total_processed: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    facts_extracted: int = 0
    anomalies_detected: int = 0
    average_processing_time: float = 0.0
    last_processed: Optional[datetime] = None
    
class QueueStats(BaseModel):
    """Queue statistics"""
    input_queue_length: int
    output_queue_length: int
    processing_rate: float  # messages per minute
    error_rate: float  # percentage
    
class ValidationError(BaseModel):
    """Data validation error"""
    field: str
    error: str
    value: Any