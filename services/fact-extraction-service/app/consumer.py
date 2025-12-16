import redis.asyncio as redis
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .extractor import FactExtractor
from .schemas import ExtractedFact, QueueStats

logger = logging.getLogger(__name__)

class CryptoDataConsumer:
    """Consumes raw crypto data from Redis streams and processes it"""
    
    def __init__(self, redis_url: str, extractor: FactExtractor):
        self.redis_url = redis_url
        self.extractor = extractor
        self.redis_client = None
        
        # Queue configuration
        self.input_stream = "raw.crypto"
        self.output_stream = "facts.extracted"
        self.consumer_group = "fact_extractors"
        self.consumer_name = "extractor_1"
        
        # Statistics
        self.stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "facts_published": 0,
            "last_processed": None,
            "processing_rate": 0.0,
            "start_time": datetime.utcnow()
        }
        
        self.running = False
        
    async def initialize(self):
        """Initialize Redis connection and consumer group"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            
            # Create consumer group if it doesn't exist
            try:
                await self.redis_client.xgroup_create(
                    self.input_stream,
                    self.consumer_group,
                    id="0",
                    mkstream=True
                )
                logger.info(f"Created consumer group '{self.consumer_group}'")
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Failed to create consumer group: {e}")
            
            logger.info("Consumer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize consumer: {e}")
            raise
    
    async def start_consuming(self):
        """Start consuming messages from the input stream"""
        self.running = True
        logger.info(f"Starting to consume from stream '{self.input_stream}'")
        
        while self.running:
            try:
                # Read messages from stream
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.input_stream: ">"},
                    count=10,
                    block=1000  # Block for 1 second
                )
                
                if messages:
                    await self._process_messages(messages)
                
            except asyncio.CancelledError:
                logger.info("Consumer cancelled")
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_messages(self, messages):
        """Process messages from Redis stream"""
        for stream_name, stream_messages in messages:
            for message_id, fields in stream_messages:
                try:
                    await self._process_single_message(message_id, fields)
                    
                    # Acknowledge message
                    await self.redis_client.xack(
                        self.input_stream,
                        self.consumer_group,
                        message_id
                    )
                    
                    self.stats["messages_processed"] += 1
                    self.stats["last_processed"] = datetime.utcnow()
                    
                except Exception as e:
                    logger.error(f"Failed to process message {message_id}: {e}")
                    self.stats["messages_failed"] += 1
    
    async def _process_single_message(self, message_id: str, fields: Dict[str, str]):
        """Process a single message"""
        try:
            # Parse message fields
            raw_data = {
                "source": fields.get("source", ""),
                "symbol": fields.get("symbol", ""),
                "data": json.loads(fields.get("data", "{}")),
                "timestamp": fields.get("timestamp", ""),
                "message_id": fields.get("message_id", message_id)
            }
            
            # Extract facts
            facts = await self.extractor.extract_facts(raw_data)
            
            # Publish facts to output stream
            for fact in facts:
                await self._publish_fact(fact)
                self.stats["facts_published"] += 1
            
            logger.debug(f"Processed message {message_id}: extracted {len(facts)} facts")
            
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            raise
    
    async def _publish_fact(self, fact: ExtractedFact):
        """Publish extracted fact to output stream"""
        try:
            fact_data = {
                "token": fact.token,
                "attribute": fact.attribute,
                "value": json.dumps(fact.value) if not isinstance(fact.value, str) else fact.value,
                "timestamp": fact.timestamp.isoformat(),
                "source": fact.source.value,
                "confidence": str(fact.confidence),
                "fact_type": fact.fact_type.value,
                "metadata": json.dumps(fact.metadata),
                "extracted_at": datetime.utcnow().isoformat()
            }
            
            message_id = await self.redis_client.xadd(self.output_stream, fact_data)
            
            logger.debug(f"Published fact for {fact.token} to {self.output_stream}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish fact: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        runtime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
        processing_rate = self.stats["messages_processed"] / max(runtime / 60, 1)  # per minute
        
        return {
            **self.stats,
            "processing_rate_per_minute": processing_rate,
            "runtime_seconds": runtime,
            "success_rate": (
                self.stats["messages_processed"] / 
                max(self.stats["messages_processed"] + self.stats["messages_failed"], 1)
            ) * 100
        }
    
    async def get_queue_status(self) -> QueueStats:
        """Get queue status information"""
        try:
            # Get input stream info
            input_info = await self.redis_client.xinfo_stream(self.input_stream)
            input_length = input_info.get("length", 0)
            
            # Get output stream info
            try:
                output_info = await self.redis_client.xinfo_stream(self.output_stream)
                output_length = output_info.get("length", 0)
            except:
                output_length = 0
            
            # Get pending messages
            try:
                pending_info = await self.redis_client.xpending(
                    self.input_stream, 
                    self.consumer_group
                )
                pending_count = pending_info[0] if pending_info else 0
            except:
                pending_count = 0
            
            # Calculate rates
            stats = await self.get_stats()
            processing_rate = stats["processing_rate_per_minute"]
            error_rate = (stats["messages_failed"] / max(stats["messages_processed"] + stats["messages_failed"], 1)) * 100
            
            return QueueStats(
                input_queue_length=input_length,
                output_queue_length=output_length,
                processing_rate=processing_rate,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return QueueStats(
                input_queue_length=0,
                output_queue_length=0,
                processing_rate=0.0,
                error_rate=100.0
            )
    
    async def health_check(self) -> bool:
        """Check if consumer is healthy"""
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Consumer health check failed: {e}")
            return False
    
    async def stop(self):
        """Stop the consumer"""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Consumer stopped")
    
    async def reprocess_failed_messages(self, max_messages: int = 100):
        """Reprocess failed/pending messages"""
        try:
            # Get pending messages for this consumer
            pending_messages = await self.redis_client.xpending_range(
                self.input_stream,
                self.consumer_group,
                min="-",
                max="+",
                count=max_messages,
                consumer=self.consumer_name
            )
            
            reprocessed = 0
            for message_info in pending_messages:
                message_id = message_info[0]
                
                try:
                    # Claim the message
                    claimed = await self.redis_client.xclaim(
                        self.input_stream,
                        self.consumer_group,
                        self.consumer_name,
                        min_idle_time=60000,  # 1 minute
                        message_ids=[message_id]
                    )
                    
                    if claimed:
                        # Reprocess the message
                        for stream_name, stream_messages in claimed:
                            for msg_id, fields in stream_messages:
                                await self._process_single_message(msg_id, fields)
                                await self.redis_client.xack(
                                    self.input_stream,
                                    self.consumer_group,
                                    msg_id
                                )
                                reprocessed += 1
                                
                except Exception as e:
                    logger.error(f"Failed to reprocess message {message_id}: {e}")
            
            logger.info(f"Reprocessed {reprocessed} failed messages")
            return reprocessed
            
        except Exception as e:
            logger.error(f"Failed to reprocess messages: {e}")
            return 0