import asyncio
import aiohttp
from typing import List, Dict, Any
from datetime import datetime
from shared.models import CryptoDataSource, FactType, CryptoFact
from shared.utils import setup_logger, make_http_request, sanitize_text
from shared.message_queue import MessageQueue
from .config import settings

logger = setup_logger(settings.service_name)

class CryptoDataIngester:
    """Handles ingestion from various crypto data sources"""
    
    def __init__(self):
        self.message_queue = MessageQueue(settings.redis_url)
        self.session = None
    
    async def start(self):
        """Initialize ingester"""
        await self.message_queue.connect()
        self.session = aiohttp.ClientSession()
        logger.info("Crypto data ingester started")
    
    async def stop(self):
        """Cleanup ingester"""
        if self.session:
            await self.session.close()
        await self.message_queue.disconnect()
        logger.info("Crypto data ingester stopped")
    
    async def ingest_coinmarketcap_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Ingest data from CoinMarketCap API"""
        if not settings.coinmarketcap_api_key:
            logger.warning("CoinMarketCap API key not configured")
            return []
        
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {
            'X-CMC_PRO_API_KEY': settings.coinmarketcap_api_key,
            'Accept': 'application/json'
        }
        params = {'symbol': ','.join(symbols)}
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                raw_data = []
                for symbol, info in data.get('data', {}).items():
                    raw_data.append({
                        'source': CryptoDataSource.COINMARKETCAP,
                        'symbol': symbol,
                        'data': info,
                        'timestamp': datetime.utcnow()
                    })
                
                logger.info(f"Ingested {len(raw_data)} records from CoinMarketCap")
                return raw_data
                
        except Exception as e:
            logger.error(f"Failed to ingest CoinMarketCap data: {str(e)}")
            return []
    
    async def ingest_coingecko_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Ingest data from CoinGecko API"""
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': ','.join(symbols),
            'vs_currencies': 'usd',
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                raw_data = []
                for symbol, info in data.items():
                    raw_data.append({
                        'source': CryptoDataSource.COINGECKO,
                        'symbol': symbol.upper(),
                        'data': info,
                        'timestamp': datetime.utcnow()
                    })
                
                logger.info(f"Ingested {len(raw_data)} records from CoinGecko")
                return raw_data
                
        except Exception as e:
            logger.error(f"Failed to ingest CoinGecko data: {str(e)}")
            return []
    
    async def ingest_news_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Ingest crypto news from News API"""
        if not settings.news_api_key:
            logger.warning("News API key not configured")
            return []
        
        url = "https://newsapi.org/v2/everything"
        headers = {'X-API-Key': settings.news_api_key}
        
        raw_data = []
        for symbol in symbols:
            params = {
                'q': f'{symbol} cryptocurrency',
                'sortBy': 'publishedAt',
                'pageSize': 10,
                'language': 'en'
            }
            
            try:
                async with self.session.get(url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    for article in data.get('articles', []):
                        raw_data.append({
                            'source': CryptoDataSource.NEWS_API,
                            'symbol': symbol,
                            'data': article,
                            'timestamp': datetime.utcnow()
                        })
                        
            except Exception as e:
                logger.error(f"Failed to ingest news for {symbol}: {str(e)}")
        
        logger.info(f"Ingested {len(raw_data)} news articles")
        return raw_data
    
    async def process_ingestion_request(self, symbols: List[str], sources: List[CryptoDataSource]):
        """Process ingestion request for multiple sources"""
        all_raw_data = []
        
        # Ingest from requested sources
        if CryptoDataSource.COINMARKETCAP in sources:
            cmc_data = await self.ingest_coinmarketcap_data(symbols)
            all_raw_data.extend(cmc_data)
        
        if CryptoDataSource.COINGECKO in sources:
            cg_data = await self.ingest_coingecko_data(symbols)
            all_raw_data.extend(cg_data)
        
        if CryptoDataSource.NEWS_API in sources:
            news_data = await self.ingest_news_data(symbols)
            all_raw_data.extend(news_data)
        
        # Send raw data to fact extraction queue
        for raw_item in all_raw_data:
            await self.message_queue.push_to_queue(
                settings.fact_extraction_queue,
                raw_item
            )
        
        # Publish status update
        await self.message_queue.publish(
            settings.ingestion_status_channel,
            {
                'status': 'completed',
                'symbols': symbols,
                'sources': [s.value for s in sources],
                'items_ingested': len(all_raw_data),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Completed ingestion: {len(all_raw_data)} items queued for processing")