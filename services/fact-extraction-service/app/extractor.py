import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import httpx
from groq import AsyncGroq

from .schemas import (
    ExtractedFact, FactType, DataSource, AnomalyDetection, 
    ExtractionResult, ValidationError, RawCryptoData
)

logger = logging.getLogger(__name__)

class FactExtractor:
    """Extracts structured facts from raw crypto data using Groq LLM"""
    
    def __init__(self, groq_api_key: str):
        self.groq_api_key = groq_api_key
        self.groq_client = None
        self.stats = {
            "total_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "facts_extracted": 0,
            "anomalies_detected": 0,
            "processing_times": [],
            "last_processed": None
        }
        
    async def initialize(self):
        """Initialize the fact extractor"""
        try:
            if self.groq_api_key:
                self.groq_client = AsyncGroq(api_key=self.groq_api_key)
                # Test connection
                await self._test_groq_connection()
                logger.info("Groq client initialized successfully")
            else:
                logger.warning("No Groq API key provided")
                
        except Exception as e:
            logger.error(f"Failed to initialize fact extractor: {e}")
            raise
    
    async def _test_groq_connection(self):
        """Test Groq API connection"""
        try:
            response = await self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            logger.info("Groq API connection test successful")
        except Exception as e:
            logger.error(f"Groq API connection test failed: {e}")
            raise
    
    async def extract_facts(self, raw_data: Dict[str, Any]) -> List[ExtractedFact]:
        """Extract facts from raw crypto data"""
        start_time = datetime.utcnow()
        
        try:
            self.stats["total_processed"] += 1
            
            # Parse raw data
            crypto_data = RawCryptoData(**raw_data)
            
            # Extract facts based on source
            facts = []
            if crypto_data.source == "coingecko":
                facts = await self._extract_coingecko_facts(crypto_data)
            elif crypto_data.source == "coinmarketcap":
                facts = await self._extract_coinmarketcap_facts(crypto_data)
            elif crypto_data.source == "news_api":
                facts = await self._extract_news_facts(crypto_data)
            else:
                logger.warning(f"Unknown data source: {crypto_data.source}")
            
            # Detect anomalies
            anomalies = await self._detect_anomalies(facts, crypto_data)
            
            # Update stats
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.stats["successful_extractions"] += 1
            self.stats["facts_extracted"] += len(facts)
            self.stats["anomalies_detected"] += len(anomalies)
            self.stats["processing_times"].append(processing_time)
            self.stats["last_processed"] = datetime.utcnow()
            
            # Keep only last 100 processing times
            if len(self.stats["processing_times"]) > 100:
                self.stats["processing_times"] = self.stats["processing_times"][-100:]
            
            logger.info(f"Extracted {len(facts)} facts from {crypto_data.source} for {crypto_data.symbol}")
            return facts
            
        except Exception as e:
            self.stats["failed_extractions"] += 1
            logger.error(f"Fact extraction failed: {e}")
            return []
    
    async def _extract_coingecko_facts(self, data: RawCryptoData) -> List[ExtractedFact]:
        """Extract facts from CoinGecko data"""
        facts = []
        timestamp = datetime.fromisoformat(data.timestamp)
        
        try:
            crypto_data = data.data
            
            # Price fact
            if "usd" in crypto_data:
                price = crypto_data["usd"]
                facts.append(ExtractedFact(
                    token=data.symbol,
                    attribute="price_usd",
                    value=price,
                    timestamp=timestamp,
                    source=DataSource.COINGECKO,
                    confidence=0.95,
                    fact_type=FactType.PRICE,
                    raw_data=crypto_data,
                    metadata={"currency": "USD"}
                ))
            
            # Market cap fact
            if "usd_market_cap" in crypto_data:
                market_cap = crypto_data["usd_market_cap"]
                facts.append(ExtractedFact(
                    token=data.symbol,
                    attribute="market_cap_usd",
                    value=market_cap,
                    timestamp=timestamp,
                    source=DataSource.COINGECKO,
                    confidence=0.95,
                    fact_type=FactType.MARKET_CAP,
                    raw_data=crypto_data,
                    metadata={"currency": "USD"}
                ))
            
            # Volume fact
            if "usd_24h_vol" in crypto_data:
                volume = crypto_data["usd_24h_vol"]
                facts.append(ExtractedFact(
                    token=data.symbol,
                    attribute="volume_24h_usd",
                    value=volume,
                    timestamp=timestamp,
                    source=DataSource.COINGECKO,
                    confidence=0.90,
                    fact_type=FactType.VOLUME,
                    raw_data=crypto_data,
                    metadata={"period": "24h", "currency": "USD"}
                ))
            
            # Price change fact
            if "usd_24h_change" in crypto_data:
                change = crypto_data["usd_24h_change"]
                facts.append(ExtractedFact(
                    token=data.symbol,
                    attribute="price_change_24h_percent",
                    value=change,
                    timestamp=timestamp,
                    source=DataSource.COINGECKO,
                    confidence=0.90,
                    fact_type=FactType.TECHNICAL,
                    raw_data=crypto_data,
                    metadata={"period": "24h", "unit": "percent"}
                ))
                
        except Exception as e:
            logger.error(f"Error extracting CoinGecko facts: {e}")
        
        return facts
    
    async def _extract_coinmarketcap_facts(self, data: RawCryptoData) -> List[ExtractedFact]:
        """Extract facts from CoinMarketCap data"""
        facts = []
        timestamp = datetime.fromisoformat(data.timestamp)
        
        try:
            crypto_data = data.data
            quote = crypto_data.get("quote", {}).get("USD", {})
            
            # Price fact
            if "price" in quote:
                price = quote["price"]
                facts.append(ExtractedFact(
                    token=data.symbol,
                    attribute="price_usd",
                    value=price,
                    timestamp=timestamp,
                    source=DataSource.COINMARKETCAP,
                    confidence=0.98,
                    fact_type=FactType.PRICE,
                    raw_data=crypto_data,
                    metadata={"currency": "USD"}
                ))
            
            # Market cap fact
            if "market_cap" in quote:
                market_cap = quote["market_cap"]
                facts.append(ExtractedFact(
                    token=data.symbol,
                    attribute="market_cap_usd",
                    value=market_cap,
                    timestamp=timestamp,
                    source=DataSource.COINMARKETCAP,
                    confidence=0.98,
                    fact_type=FactType.MARKET_CAP,
                    raw_data=crypto_data,
                    metadata={"currency": "USD"}
                ))
            
            # Volume fact
            if "volume_24h" in quote:
                volume = quote["volume_24h"]
                facts.append(ExtractedFact(
                    token=data.symbol,
                    attribute="volume_24h_usd",
                    value=volume,
                    timestamp=timestamp,
                    source=DataSource.COINMARKETCAP,
                    confidence=0.95,
                    fact_type=FactType.VOLUME,
                    raw_data=crypto_data,
                    metadata={"period": "24h", "currency": "USD"}
                ))
            
            # Price change facts
            for period in ["1h", "24h", "7d"]:
                change_key = f"percent_change_{period}"
                if change_key in quote:
                    change = quote[change_key]
                    facts.append(ExtractedFact(
                        token=data.symbol,
                        attribute=f"price_change_{period}_percent",
                        value=change,
                        timestamp=timestamp,
                        source=DataSource.COINMARKETCAP,
                        confidence=0.95,
                        fact_type=FactType.TECHNICAL,
                        raw_data=crypto_data,
                        metadata={"period": period, "unit": "percent"}
                    ))
                    
        except Exception as e:
            logger.error(f"Error extracting CoinMarketCap facts: {e}")
        
        return facts
    
    async def _extract_news_facts(self, data: RawCryptoData) -> List[ExtractedFact]:
        """Extract facts from news articles using Groq LLM"""
        facts = []
        timestamp = datetime.fromisoformat(data.timestamp)
        
        try:
            if not self.groq_client:
                logger.warning("Groq client not available for news extraction")
                return facts
            
            articles = data.data if isinstance(data.data, list) else [data.data]
            
            for article in articles:
                if not isinstance(article, dict):
                    continue
                    
                title = article.get("title", "")
                description = article.get("description", "")
                content = article.get("content", "")
                
                # Combine article text
                article_text = f"{title}. {description}. {content}"[:2000]  # Limit length
                
                if len(article_text.strip()) < 50:
                    continue
                
                # Use Groq to extract structured facts
                prompt = f"""
                Extract key cryptocurrency facts from this news article. Focus on factual information only.
                
                Article: {article_text}
                
                Extract facts in JSON format:
                [
                  {{
                    "token": "cryptocurrency symbol (e.g., BTC, ETH)",
                    "attribute": "specific attribute (e.g., regulatory_status, partnership, price_prediction)",
                    "value": "the factual value or statement",
                    "fact_type": "NEWS|REGULATORY|SENTIMENT",
                    "confidence": 0.0-1.0
                  }}
                ]
                
                Only include verifiable facts, not speculation or opinions.
                """
                
                try:
                    response = await self.groq_client.chat.completions.create(
                        model="mixtral-8x7b-32768",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=1000
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                    # Parse JSON response
                    try:
                        extracted_facts = json.loads(response_text)
                        
                        for fact_data in extracted_facts:
                            if not isinstance(fact_data, dict):
                                continue
                                
                            # Map fact type
                            fact_type_str = fact_data.get("fact_type", "NEWS")
                            fact_type = FactType.NEWS
                            if fact_type_str == "REGULATORY":
                                fact_type = FactType.REGULATORY
                            elif fact_type_str == "SENTIMENT":
                                fact_type = FactType.SENTIMENT
                            
                            facts.append(ExtractedFact(
                                token=fact_data.get("token", data.symbol).upper(),
                                attribute=fact_data.get("attribute", "news_mention"),
                                value=fact_data.get("value", ""),
                                timestamp=timestamp,
                                source=DataSource.NEWS_API,
                                confidence=min(max(fact_data.get("confidence", 0.7), 0.0), 1.0),
                                fact_type=fact_type,
                                raw_data=article,
                                metadata={
                                    "article_title": title,
                                    "article_url": article.get("url", ""),
                                    "published_at": article.get("publishedAt", "")
                                }
                            ))
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse Groq JSON response: {e}")
                        
                except Exception as e:
                    logger.error(f"Groq API call failed: {e}")
                    
        except Exception as e:
            logger.error(f"Error extracting news facts: {e}")
        
        return facts
    
    async def _detect_anomalies(self, facts: List[ExtractedFact], raw_data: RawCryptoData) -> List[AnomalyDetection]:
        """Detect anomalies in extracted facts"""
        anomalies = []
        
        try:
            # Check for missing critical fields
            price_facts = [f for f in facts if f.fact_type == FactType.PRICE]
            if not price_facts and raw_data.source in ["coingecko", "coinmarketcap"]:
                anomalies.append(AnomalyDetection(
                    is_anomaly=True,
                    anomaly_type="missing_price_data",
                    severity=0.8,
                    description=f"No price data found for {raw_data.symbol} from {raw_data.source}"
                ))
            
            # Check for extreme price changes
            for fact in facts:
                if fact.attribute.endswith("_percent") and isinstance(fact.value, (int, float)):
                    if abs(fact.value) > 50:  # More than 50% change
                        anomalies.append(AnomalyDetection(
                            is_anomaly=True,
                            anomaly_type="extreme_price_change",
                            severity=min(abs(fact.value) / 100, 1.0),
                            description=f"Extreme price change detected: {fact.value}% for {fact.token}"
                        ))
            
            # Check for zero or negative values where they shouldn't be
            for fact in facts:
                if fact.fact_type in [FactType.PRICE, FactType.MARKET_CAP, FactType.VOLUME]:
                    if isinstance(fact.value, (int, float)) and fact.value <= 0:
                        anomalies.append(AnomalyDetection(
                            is_anomaly=True,
                            anomaly_type="invalid_value",
                            severity=0.9,
                            description=f"Invalid {fact.attribute} value: {fact.value} for {fact.token}"
                        ))
                        
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
        
        return anomalies
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        avg_processing_time = 0
        if self.stats["processing_times"]:
            avg_processing_time = sum(self.stats["processing_times"]) / len(self.stats["processing_times"])
        
        return {
            **self.stats,
            "average_processing_time": avg_processing_time,
            "success_rate": (
                self.stats["successful_extractions"] / max(self.stats["total_processed"], 1)
            ) * 100
        }
    
    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed extraction statistics"""
        stats = await self.get_stats()
        
        return {
            "extraction_stats": stats,
            "groq_configured": bool(self.groq_client),
            "supported_sources": ["coingecko", "coinmarketcap", "news_api"],
            "fact_types": [ft.value for ft in FactType],
            "timestamp": datetime.utcnow()
        }
    
    async def health_check(self) -> bool:
        """Check if extractor is healthy"""
        try:
            if self.groq_client:
                # Test Groq connection
                await self._test_groq_connection()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False