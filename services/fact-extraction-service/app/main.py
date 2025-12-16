from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
from datetime import datetime
import asyncio
import logging
import os

from .consumer import CryptoDataConsumer
from .extractor import FactExtractor
from .schemas import ExtractedFact, ExtractionStats

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fact Extraction Service",
    description="Extracts structured facts from raw crypto data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Global instances
consumer = None
extractor = None
background_task = None

@app.on_event("startup")
async def startup_event():
    """Initialize extraction service components"""
    global consumer, extractor, background_task
    
    try:
        # Initialize fact extractor
        extractor = FactExtractor(GROQ_API_KEY)
        await extractor.initialize()
        
        # Initialize consumer
        consumer = CryptoDataConsumer(REDIS_URL, extractor)
        await consumer.initialize()
        
        # Start background processing
        background_task = asyncio.create_task(consumer.start_consuming())
        
        logger.info("Fact Extraction Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start extraction service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global background_task, consumer
    
    if background_task:
        background_task.cancel()
        
    if consumer:
        await consumer.stop()
        
    logger.info("Fact Extraction Service shut down")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        consumer_healthy = consumer and await consumer.health_check()
        extractor_healthy = extractor and await extractor.health_check()
        
        status = "healthy" if (consumer_healthy and extractor_healthy) else "degraded"
        
        return {
            "status": status,
            "service": "fact-extraction-service",
            "timestamp": datetime.utcnow(),
            "components": {
                "consumer": "healthy" if consumer_healthy else "unhealthy",
                "extractor": "healthy" if extractor_healthy else "unhealthy"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/status")
async def get_status():
    """Get detailed service status"""
    try:
        stats = await consumer.get_stats() if consumer else {}
        extractor_stats = await extractor.get_stats() if extractor else {}
        
        return {
            "service": "fact-extraction-service",
            "status": "running",
            "groq_configured": bool(GROQ_API_KEY),
            "consumer_stats": stats,
            "extractor_stats": extractor_stats,
            "background_task_running": background_task and not background_task.done()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status")
async def get_queue_status():
    """Get queue status"""
    try:
        if not consumer:
            raise HTTPException(status_code=503, detail="Consumer not initialized")
            
        queue_stats = await consumer.get_queue_status()
        return queue_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/manual")
async def manual_extraction(raw_data: Dict[str, Any]):
    """Manually trigger fact extraction for raw data"""
    try:
        if not extractor:
            raise HTTPException(status_code=503, detail="Extractor not initialized")
        
        facts = await extractor.extract_facts(raw_data)
        
        return {
            "status": "success",
            "facts_extracted": len(facts),
            "facts": [fact.dict() for fact in facts],
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Manual extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/extraction")
async def get_extraction_stats():
    """Get extraction statistics"""
    try:
        if not extractor:
            raise HTTPException(status_code=503, detail="Extractor not initialized")
            
        stats = await extractor.get_detailed_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)