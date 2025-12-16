import asyncio
import chromadb
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from datetime import datetime
from shared.models import CryptoFact
from shared.utils import setup_logging
from shared.message_queue import MessageQueue
from shared.database_adapter import DatabaseSchemaAdapter
from .config import settings

logger = setup_logging(settings.service_name)

class EmbeddingProcessor:
    """Processes facts to generate embeddings and store in ChromaDB"""
    
    def __init__(self):
        self.model = SentenceTransformer(settings.embedding_model)
        self.chroma_client = None
        self.collection = None
        self.message_queue = MessageQueue(settings.redis_url)
        self.db_adapter = None
        
    async def initialize(self):
        """Initialize ChromaDB connection and message queue"""
        try:
            self.chroma_client = chromadb.HttpClient(host=settings.chroma_url)
            self.collection = self.chroma_client.get_or_create_collection(
                name="crypto_facts",
                metadata={"description": "Crypto knowledge facts with embeddings"}
            )
            await self.message_queue.connect()
            logger.info("EmbeddingProcessor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EmbeddingProcessor: {e}")
            raise
    
    async def process_fact(self, fact: CryptoFact) -> bool:
        """Process a single fact to generate and store embedding"""
        try:
            # Ensure retrieval_time is set
            if not hasattr(fact, 'retrieval_time') or fact.retrieval_time is None:
                fact.update_retrieval_time()
            
            # Generate embedding
            embedding = self.model.encode(fact.content).tolist()
            fact.embedding = embedding
            
            # Store in ChromaDB
            await self._store_in_chromadb(fact)
            
            # Publish to storage queue for database persistence
            await self.message_queue.publish(settings.storage_queue, {
                "action": "store_fact",
                "fact": fact.dict(),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Processed fact {fact.id} for symbol {fact.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process fact {fact.id}: {e}")
            return False
    
    async def _store_in_chromadb(self, fact: CryptoFact):
        """Store fact with embedding in ChromaDB"""
        try:
            self.collection.add(
                embeddings=[fact.embedding],
                documents=[fact.content],
                metadatas=[{
                    "id": fact.id,
                    "symbol": fact.symbol,
                    "fact_type": fact.fact_type.value,
                    "source": fact.source.value,
                    "confidence_score": fact.confidence_score,
                    "timestamp": fact.timestamp.isoformat(),
                    "retrieval_time": fact.retrieval_time.isoformat(),
                    "verified": fact.verified
                }],
                ids=[fact.id]
            )
            logger.debug(f"Stored fact {fact.id} in ChromaDB")
        except Exception as e:
            logger.error(f"Failed to store fact {fact.id} in ChromaDB: {e}")
            raise
    
    async def batch_process_facts(self, facts: List[CryptoFact]) -> Dict[str, int]:
        """Process multiple facts in batch"""
        results = {"success": 0, "failed": 0}
        
        # Process in batches
        batch_size = settings.batch_size
        for i in range(0, len(facts), batch_size):
            batch = facts[i:i + batch_size]
            
            # Ensure all facts have retrieval_time
            for fact in batch:
                if not hasattr(fact, 'retrieval_time') or fact.retrieval_time is None:
                    fact.update_retrieval_time()
            
            # Generate embeddings for batch
            texts = [fact.content for fact in batch]
            embeddings = self.model.encode(texts).tolist()
            
            # Process each fact in batch
            for fact, embedding in zip(batch, embeddings):
                fact.embedding = embedding
                if await self.process_fact(fact):
                    results["success"] += 1
                else:
                    results["failed"] += 1
        
        logger.info(f"Batch processing completed: {results}")
        return results
    
    async def query_similar_facts(
        self, 
        query_text: str, 
        n_results: int = 10,
        symbol_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query for similar facts using semantic search"""
        try:
            # Generate query embedding
            query_embedding = self.model.encode(query_text).tolist()
            
            # Prepare where clause for filtering
            where_clause = {}
            if symbol_filter:
                where_clause["symbol"] = symbol_filter
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to query similar facts: {e}")
            return []
    
    async def start_processing_queue(self):
        """Start processing facts from the embedding queue"""
        logger.info("Starting embedding queue processing...")
        
        while True:
            try:
                # Pop fact from queue
                message = await self.message_queue.pop_from_queue(
                    settings.embedding_queue, 
                    timeout=5
                )
                
                if message:
                    # Parse fact from message
                    fact_data = message.get('fact')
                    if fact_data:
                        fact = CryptoFact(**fact_data)
                        await self.process_fact(fact)
                
            except Exception as e:
                logger.error(f"Error processing embedding queue: {e}")
                await asyncio.sleep(1)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of embedding service components"""
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        try:
            # Check ChromaDB
            collection_count = self.collection.count()
            health["components"]["chromadb"] = {
                "status": "healthy",
                "collection_count": collection_count
            }
        except Exception as e:
            health["components"]["chromadb"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "degraded"
        
        try:
            # Check message queue
            queue_length = await self.message_queue.get_queue_length(settings.embedding_queue)
            health["components"]["message_queue"] = {
                "status": "healthy",
                "queue_length": queue_length
            }
        except Exception as e:
            health["components"]["message_queue"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "degraded"
        
        return health