import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
import json
from .producer import MessageProducer

logger = logging.getLogger(__name__)

class CryptoDataIngester:
    """Main service class for ingesting crypto data from multiple APIs"""
    
    def __init__(self, producer: MessageProducer):
        self.producer = producer
        
        # API Configuration
        self.coinmarketcap_api_key = os.getenv("COINMARKETCAP_API_KEY")
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY")  # Optional
        self.news_api_key = os.getenv("NEWS_API_KEY")
        
        # API Base URLs
        self.coinmarketcap_base = "https://pro-api.coinmarketcap.com/v1"
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.news_api_base = "https://newsapi.org/v2"
        
        # Rate limiting
        self.last_fetch_times = {}
        self.min_fetch_interval = 60  # 1 minute between fetches per source
        
        # Statistics
        self.stats = {
            "total_fetches": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "last_fetch_time": None,
            "sources_status": {
                "coinmarketcap": "unknown",
                "coingecko": "unknown", 
                "news_api": "unknown"
            }
        }
    
    async def initialize(self):
        """Initialize the ingester"""
        try:
            # Create consumer group for processing
            await self.producer.create_consumer_group()
            
            # Test API connections
            await self._test_api_connections()
            
            logger.info("CryptoDataIngester initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ingester: {e}")
            raise
    
    async def _test_api_connections(self):
        """Test connections to all APIs"""
        # Test CoinGecko (no API key required)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.coingecko_base}/ping")
                if response.status_code == 200:
                    self.stats["sources_status"]["coingecko"] = "healthy"
                    logger.info("CoinGecko API connection successful")
        except Exception as e:
            self.stats["sources_status"]["coingecko"] = "unhealthy"
            logger.warning(f"CoinGecko API test failed: {e}")
        
        # Test CoinMarketCap (requires API key)
        if self.coinmarketcap_api_key:
            try:
                headers = {"X-CMC_PRO_API_KEY": self.coinmarketcap_api_key}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.coinmarketcap_base}/cryptocurrency/map",
                        headers=headers,
                        params={"limit": 1}
                    )
                    if response.status_code == 200:
                        self.stats["sources_status"]["coinmarketcap"] = "healthy"
                        logger.info("CoinMarketCap API connection successful")
            except Exception as e:
                self.stats["sources_status"]["coinmarketcap"] = "unhealthy"
                logger.warning(f"CoinMarketCap API test failed: {e}")
        
        # Test News API (requires API key)
        if self.news_api_key:
            try:
                params = {
                    "apiKey": self.news_api_key,
                    "q": "bitcoin",
                    "pageSize": 1
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{self.news_api_base}/everything", params=params)
                    if response.status_code == 200:
                        self.stats["sources_status"]["news_api"] = "healthy"
                        logger.info("News API connection successful")
            except Exception as e:
                self.stats["sources_status"]["news_api"] = "unhealthy"
                logger.warning(f"News API test failed: {e}")
    
    async def fetch_and_publish(self, symbols: List[str], sources: List[str], force: bool = False):
        """Fetch data from specified sources and publish to queue"""
        try:
            self.stats["total_fetches"] += 1
            
            tasks = []
            
            # Fetch from each source
            if "coingecko" in sources:
                tasks.append(self._fetch_coingecko_data(symbols, force))
            
            if "coinmarketcap" in sources and self.coinmarketcap_api_key:
                tasks.append(self._fetch_coinmarketcap_data(symbols, force))
            
            if "news" in sources and self.news_api_key:
                tasks.append(self._fetch_news_data(symbols, force))
            
            # Execute all fetches concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful vs failed
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            
            self.stats["successful_fetches"] += successful
            self.stats["failed_fetches"] += failed
            self.stats["last_fetch_time"] = datetime.utcnow().isoformat()
            
            logger.info(f"Fetch completed: {successful} successful, {failed} failed")
            
        except Exception as e:
            self.stats["failed_fetches"] += 1
            logger.error(f"Fetch and publish failed: {e}")
            raise
    
    async def _fetch_coingecko_data(self, symbols: List[str], force: bool = False):
        """Fetch data from CoinGecko API"""
        source = "coingecko"
        
        if not force and not self._should_fetch(source):
            logger.debug(f"Skipping {source} fetch due to rate limiting")
            return
        
        try:
            # Convert symbols to CoinGecko IDs format
            symbol_ids = ",".join(symbols)
            
            params = {
                "ids": symbol_ids,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true"
            }
            
            if self.coingecko_api_key:
                params["x_cg_demo_api_key"] = self.coingecko_api_key
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.coingecko_base}/simple/price",
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Publish each symbol's data
                for symbol in symbols:
                    if symbol in data:
                        await self.producer.publish_crypto_data(
                            data[symbol], 
                            source, 
                            symbol
                        )
                
                self._update_fetch_time(source)
                self.stats["sources_status"][source] = "healthy"
                logger.info(f"Successfully fetched CoinGecko data for {len(data)} symbols")
                
        except Exception as e:
            self.stats["sources_status"][source] = "unhealthy"
            logger.error(f"CoinGecko fetch failed: {e}")
            raise
    
    async def _fetch_coinmarketcap_data(self, symbols: List[str], force: bool = False):
        """Fetch data from CoinMarketCap API"""
        source = "coinmarketcap"
        
        if not force and not self._should_fetch(source):
            logger.debug(f"Skipping {source} fetch due to rate limiting")
            return
        
        try:
            headers = {"X-CMC_PRO_API_KEY": self.coinmarketcap_api_key}
            
            # Get latest quotes
            params = {
                "slug": ",".join(symbols),
                "convert": "USD"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.coinmarketcap_base}/cryptocurrency/quotes/latest",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Publish each symbol's data
                if "data" in data:
                    for coin_id, coin_data in data["data"].items():
                        symbol = coin_data.get("slug", coin_id)
                        await self.producer.publish_crypto_data(
                            coin_data,
                            source,
                            symbol
                        )
                
                self._update_fetch_time(source)
                self.stats["sources_status"][source] = "healthy"
                logger.info(f"Successfully fetched CoinMarketCap data for {len(data.get('data', {}))} symbols")
                
        except Exception as e:
            self.stats["sources_status"][source] = "unhealthy"
            logger.error(f"CoinMarketCap fetch failed: {e}")
            raise
    
    async def _fetch_news_data(self, symbols: List[str], force: bool = False):
        """Fetch news data from News API"""
        source = "news_api"
        
        if not force and not self._should_fetch(source):
            logger.debug(f"Skipping {source} fetch due to rate limiting")
            return
        
        try:
            # Create search queries for crypto symbols
            crypto_terms = ["cryptocurrency", "bitcoin", "ethereum", "crypto", "blockchain"]
            
            for term in crypto_terms:
                params = {
                    "apiKey": self.news_api_key,
                    "q": term,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 20,
                    "from": (datetime.utcnow() - timedelta(hours=24)).isoformat()
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.news_api_base}/everything",
                        params=params
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if "articles" in data and data["articles"]:
                        await self.producer.publish_news_data(
                            data["articles"],
                            term
                        )
            
            self._update_fetch_time(source)
            self.stats["sources_status"][source] = "healthy"
            logger.info("Successfully fetched news data")
            
        except Exception as e:
            self.stats["sources_status"][source] = "unhealthy"
            logger.error(f"News API fetch failed: {e}")
            raise
    
    def _should_fetch(self, source: str) -> bool:
        """Check if enough time has passed since last fetch"""
        last_fetch = self.last_fetch_times.get(source)
        if not last_fetch:
            return True
        
        time_since_last = datetime.utcnow() - last_fetch
        return time_since_last.total_seconds() >= self.min_fetch_interval
    
    def _update_fetch_time(self, source: str):
        """Update the last fetch time for a source"""
        self.last_fetch_times[source] = datetime.utcnow()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get ingester statistics"""
        return {
            **self.stats,
            "api_keys_configured": {
                "coinmarketcap": bool(self.coinmarketcap_api_key),
                "coingecko": bool(self.coingecko_api_key),
                "news_api": bool(self.news_api_key)
            },
            "last_fetch_times": {
                source: time.isoformat() if time else None
                for source, time in self.last_fetch_times.items()
            }
        }
    
    async def health_check(self) -> bool:
        """Check if ingester is healthy"""
        try:
            # Check if at least one API source is healthy
            healthy_sources = [
                status for status in self.stats["sources_status"].values()
                if status == "healthy"
            ]
            return len(healthy_sources) > 0
        except Exception:
            return False