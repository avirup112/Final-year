import redis.asyncio as redis
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageProducer:
    """Redis Streams message producer for crypto data"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        self.stream_name = "raw.crypto"
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def publish_crypto_data(self, data: Dict[str, Any], source: str, symbol: str) -> str:
        """Publish crypto data to Redis stream"""
        try:
            message = {
                "source": source,
                "symbol": symbol,
                "data": json.dumps(data),
                "timestamp": datetime.utcnow().isoformat(),
                "message_id": f"{source}_{symbol}_{int(datetime.utcnow().timestamp())}"
            }
            
            # Add to Redis stream
            message_id = await self.redis_client.xadd(self.stream_name, message)
            
            logger.debug(f"Published {source} data for {symbol} to stream {self.stream_name}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise
    
    async def publish_news_data(self, articles: list, query: str) -> str:
        """Publish news data to Redis stream"""
        try:
            message = {
                "source": "news_api",
                "query": query,
                "data": json.dumps(articles),
                "timestamp": datetime.utcnow().isoformat(),
                "message_id": f"news_{query}_{int(datetime.utcnow().timestamp())}"
            }
            
            message_id = await self.redis_client.xadd(self.stream_name, message)
            
            logger.debug(f"Published news data for query '{query}' to stream {self.stream_name}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish news message: {e}")
            raise
    
    async def publish_batch(self, messages: list) -> list:
        """Publish multiple messages in batch"""
        try:
            message_ids = []
            
            # Use pipeline for batch operations
            pipe = self.redis_client.pipeline()
            
            for msg in messages:
                pipe.xadd(self.stream_name, msg)
            
            results = await pipe.execute()
            message_ids.extend(results)
            
            logger.info(f"Published batch of {len(messages)} messages to {self.stream_name}")
            return message_ids
            
        except Exception as e:
            logger.error(f"Failed to publish batch: {e}")
            raise
    
    async def get_stream_info(self) -> Dict[str, Any]:
        """Get information about the stream"""
        try:
            info = await self.redis_client.xinfo_stream(self.stream_name)
            return {
                "stream_name": self.stream_name,
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": info.get("groups", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get stream info: {e}")
            return {"error": str(e)}
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            stream_info = await self.get_stream_info()
            
            # Get pending messages count (approximate)
            try:
                pending_count = await self.redis_client.xpending(self.stream_name, "crypto_processors")
            except:
                pending_count = 0
            
            return {
                "stream_name": self.stream_name,
                "total_messages": stream_info.get("length", 0),
                "pending_messages": pending_count,
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e), "status": "unhealthy"}
    
    async def health_check(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def create_consumer_group(self, group_name: str = "crypto_processors"):
        """Create consumer group for the stream"""
        try:
            await self.redis_client.xgroup_create(
                self.stream_name, 
                group_name, 
                id="0", 
                mkstream=True
            )
            logger.info(f"Created consumer group '{group_name}' for stream '{self.stream_name}'")
        except Exception as e:
            if "BUSYGROUP" not in str(e):  # Group already exists
                logger.error(f"Failed to create consumer group: {e}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")