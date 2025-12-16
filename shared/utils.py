import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json

def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Setup structured logging for services"""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'%(asctime)s - {service_name} - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def generate_fact_id(content: str, source: str, timestamp: datetime) -> str:
    """Generate unique ID for crypto facts"""
    data = f"{content}_{source}_{timestamp.isoformat()}"
    return hashlib.md5(data.encode()).hexdigest()

def is_cache_valid(cached_time: datetime, ttl_minutes: int = 5) -> bool:
    """Check if cached data is still valid"""
    return datetime.utcnow() - cached_time < timedelta(minutes=ttl_minutes)

async def make_http_request(
    url: str, 
    method: str = "GET", 
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Make async HTTP request with error handling"""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        try:
            async with session.request(method, url, headers=headers, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            raise Exception(f"HTTP request failed: {str(e)}")

def sanitize_text(text: str) -> str:
    """Clean and sanitize text for processing"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = " ".join(text.split())
    
    # Remove special characters that might cause issues
    text = text.replace('\x00', '')
    
    return text.strip()

def calculate_confidence_score(
    source_reliability: float,
    content_quality: float,
    freshness_score: float
) -> float:
    """Calculate overall confidence score for facts"""
    weights = {
        'reliability': 0.4,
        'quality': 0.4,
        'freshness': 0.2
    }
    
    score = (
        source_reliability * weights['reliability'] +
        content_quality * weights['quality'] +
        freshness_score * weights['freshness']
    )
    
    return min(max(score, 0.0), 1.0)

class CircuitBreaker:
    """Simple circuit breaker implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e