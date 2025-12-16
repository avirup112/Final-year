import asyncio
import json
import redis.asyncio as redis
from typing import Dict, Any, Callable, Optional
from shared.utils import setup_logging

logger = setup_logging("message_queue")

class MessageQueue:
    """Redis-based message queue for inter-service communication"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.subscribers = {}
    
    async def connect(self):
        """Connect to Redis"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Connected to Redis message queue")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis message queue")
    
    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to channel"""
        if not self.redis_client:
            await self.connect()
        
        try:
            message_str = json.dumps(message, default=str)
            await self.redis_client.publish(channel, message_str)
            logger.debug(f"Published message to {channel}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message to {channel}: {str(e)}")
            raise
    
    async def subscribe(self, channel: str, handler: Callable):
        """Subscribe to channel with message handler"""
        if not self.redis_client:
            await self.connect()
        
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        self.subscribers[channel] = pubsub
        logger.info(f"Subscribed to channel: {channel}")
        
        async def message_listener():
            try:
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            await handler(data)
                        except Exception as e:
                            logger.error(f"Error processing message from {channel}: {str(e)}")
            except Exception as e:
                logger.error(f"Error in message listener for {channel}: {str(e)}")
        
        # Start listener in background
        asyncio.create_task(message_listener())
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from channel"""
        if channel in self.subscribers:
            await self.subscribers[channel].unsubscribe(channel)
            await self.subscribers[channel].close()
            del self.subscribers[channel]
            logger.info(f"Unsubscribed from channel: {channel}")
    
    async def push_to_queue(self, queue_name: str, item: Dict[str, Any]):
        """Push item to Redis list (queue)"""
        if not self.redis_client:
            await self.connect()
        
        try:
            item_str = json.dumps(item, default=str)
            await self.redis_client.lpush(queue_name, item_str)
            logger.debug(f"Pushed item to queue {queue_name}")
        except Exception as e:
            logger.error(f"Failed to push to queue {queue_name}: {str(e)}")
            raise
    
    async def pop_from_queue(self, queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """Pop item from Redis list (queue)"""
        if not self.redis_client:
            await self.connect()
        
        try:
            if timeout > 0:
                result = await self.redis_client.brpop(queue_name, timeout=timeout)
                if result:
                    return json.loads(result[1])
            else:
                result = await self.redis_client.rpop(queue_name)
                if result:
                    return json.loads(result)
            return None
        except Exception as e:
            logger.error(f"Failed to pop from queue {queue_name}: {str(e)}")
            raise
    
    async def get_queue_length(self, queue_name: str) -> int:
        """Get length of queue"""
        if not self.redis_client:
            await self.connect()
        
        return await self.redis_client.llen(queue_name)