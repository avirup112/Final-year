from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import logging
import os
from pydantic import BaseModel

from .service import CryptoDataIngester
from .producer import MessageProducer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Crypto Ingestion Service",
    description="Ingests crypto data from CoinGecko, CoinMarketCap, and News APIs",
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
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", "300"))  # 5 minutes default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Global instances
ingester = None
producer = None
background_task = None

class FetchRequest(BaseModel):
    symbols: Optional[List[str]] = ["bitcoin", "ethereum", "cardano", "polkadot", "chainlink"]
    sources: Optional[List[str]] = ["coingecko", "coinmarketcap", "news"]
    force: bool = False

class FetchResponse(BaseModel):
    status: str
    message: str
    symbols_processed: int
    sources_used: List[str]
    timestamp: datetime

@app.on_event("startup")
async def startup_event():
    """Initialize ingestion service components"""
    global ingester, producer, background_task
    
    try:
        # Initialize message producer
        producer = MessageProducer(REDIS_URL)
        await producer.initialize()
        
        # Initialize crypto data ingester
        ingester = CryptoDataIngester(producer)
        await ingester.initialize()
        
        # Start background fetching task
        background_task = asyncio.create_task(background_fetch_loop())
        
        logger.info("Crypto Ingestion Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start ingestion service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global background_task, producer
    
    if background_task:
        background_task.cancel()
        
    if producer:
        await producer.close()
        
    logger.info("Crypto Ingestion Service shut down")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if components are healthy
        producer_healthy = producer and await producer.health_check()
        ingester_healthy = ingester and await ingester.health_check()
        
        status = "healthy" if (producer_healthy and ingester_healthy) else "degraded"
        
        return {
            "status": status,
            "service": "ingestion-service",
            "timestamp": datetime.utcnow(),
            "components": {
                "producer": "healthy" if producer_healthy else "unhealthy",
                "ingester": "healthy" if ingester_healthy else "unhealthy"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.post("/fetch-now", response_model=FetchResponse)
async def fetch_now(request: FetchRequest, background_tasks: BackgroundTasks):
    """Manually trigger data fetch"""
    try:
        if not ingester:
            raise HTTPException(status_code=503, detail="Ingester not initialized")
        
        logger.info(f"Manual fetch triggered for symbols: {request.symbols}")
        
        # Start fetch in background
        background_tasks.add_task(
            ingester.fetch_and_publish,
            request.symbols,
            request.sources,
            request.force
        )
        
        return FetchResponse(
            status="accepted",
            message="Data fetch started",
            symbols_processed=len(request.symbols),
            sources_used=request.sources,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Manual fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    """Get detailed service status"""
    try:
        api_keys_status = {
            "coinmarketcap": bool(os.getenv("COINMARKETCAP_API_KEY")),
            "coingecko": bool(os.getenv("COINGECKO_API_KEY")),  # Optional for CoinGecko
            "news_api": bool(os.getenv("NEWS_API_KEY"))
        }
        
        ingester_stats = await ingester.get_stats() if ingester else {}
        
        return {
            "service": "ingestion-service",
            "status": "running",
            "fetch_interval": FETCH_INTERVAL,
            "api_keys_configured": api_keys_status,
            "ingester_stats": ingester_stats,
            "background_task_running": background_task and not background_task.done()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status")
async def get_queue_status():
    """Get message queue status"""
    try:
        if not producer:
            raise HTTPException(status_code=503, detail="Producer not initialized")
            
        queue_stats = await producer.get_queue_stats()
        return queue_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/update")
async def update_config(fetch_interval: Optional[int] = None):
    """Update service configuration"""
    try:
        global FETCH_INTERVAL
        
        if fetch_interval and fetch_interval > 0:
            FETCH_INTERVAL = fetch_interval
            logger.info(f"Updated fetch interval to {FETCH_INTERVAL} seconds")
        
        return {
            "status": "updated",
            "fetch_interval": FETCH_INTERVAL,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def background_fetch_loop():
    """Background task to fetch data periodically"""
    logger.info(f"Starting background fetch loop with {FETCH_INTERVAL}s interval")
    
    default_symbols = ["bitcoin", "ethereum", "cardano", "polkadot", "chainlink", 
                      "solana", "avalanche-2", "polygon", "cosmos", "near"]
    default_sources = ["coingecko", "coinmarketcap", "news"]
    
    while True:
        try:
            if ingester:
                logger.info("Starting scheduled data fetch")
                await ingester.fetch_and_publish(default_symbols, default_sources)
                logger.info("Scheduled data fetch completed")
            
            await asyncio.sleep(FETCH_INTERVAL)
            
        except asyncio.CancelledError:
            logger.info("Background fetch loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background fetch loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)