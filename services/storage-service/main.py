from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import logging
from db import db

# Configure Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI(title="Storage Service", version="1.0.0")

class FactModel(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = {}

class BatchFacts(BaseModel):
    facts: List[FactModel]

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.close()

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "storage-service", 
        "mode": "fallback" if db.fallback_mode else "mongodb"
    }

@app.post("/facts")
async def store_facts(batch: BatchFacts):
    """Store a batch of facts"""
    count = 0
    for fact in batch.facts:
        await db.save_fact(fact.dict())
        count += 1
    return {"status": "success", "stored_count": count}

@app.get("/stats")
async def get_stats():
    count = await db.get_total_facts()
    return {"total_facts": count}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8013, reload=True)