from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Optional
import os
import logging
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Storage Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password123@localhost:27017/crypto_knowledge?authSource=admin")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.crypto_knowledge

class FactModel(BaseModel):
    content: str
    source: str
    category: str
    confidence_score: float
    metadata: dict = {}

@app.on_event("startup")
async def startup_event():
    try:
        await client.admin.command('ping')
        logger.info("Connected to MongoDB successfully")
        await db.facts.create_index("timestamp")
        await db.facts.create_index("category")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")

@app.get("/health")
async def health_check():
    try:
        await client.admin.command('ping')
        return {"status": "healthy", "service": "storage-service"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/facts")
async def store_fact(fact: FactModel):
    try:
        fact_dict = fact.dict()
        fact_dict["timestamp"] = datetime.utcnow()
        result = await db.facts.insert_one(fact_dict)
        return {"id": str(result.inserted_id), "status": "stored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/facts")
async def get_facts(category: Optional[str] = None, limit: int = 100):
    try:
        query = {"category": category} if category else {}
        cursor = db.facts.find(query).sort("timestamp", -1).limit(limit)
        facts = []
        async for fact in cursor:
            fact["_id"] = str(fact["_id"])
            facts.append(fact)
        return {"facts": facts, "count": len(facts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)