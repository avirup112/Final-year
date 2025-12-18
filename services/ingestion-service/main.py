from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import logging
from coingecko import fetch_market_data

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ingestion-service")

app = FastAPI(title="Ingestion Service", version="1.0.0")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ingestion-service"}

@app.get("/fetch/coingecko")
async def get_coingecko_data(limit: int = 50):
    """Fetch live data from CoinGecko"""
    logger.info("📥 Received request for CoinGecko data")
    data = await fetch_market_data(limit)
    if not data:
        raise HTTPException(status_code=503, detail="Failed to fetch data from CoinGecko")
    return data

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8012, reload=True)