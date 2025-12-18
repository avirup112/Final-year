from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
from datetime import datetime

logger = logging.getLogger("storage-service")

class Database:
    client: AsyncIOMotorClient = None
    db = None
    fallback_mode = False
    memory_store = {} # Simple in-memory fallback
    
    async def connect(self):
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        try:
            # Short timeout to detect failure quickly
            self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=2000)
            await self.client.server_info()
            self.db = self.client.crypto_knowledge
            logger.info("✅ Connected to MongoDB")
            self.fallback_mode = False
        except Exception as e:
            logger.warning(f"⚠️ MongoDB connection failed: {e}. Switching to InMemory/File Mode.")
            self.fallback_mode = True
            
    async def close(self):
        if self.client:
            self.client.close()

    async def save_fact(self, fact: dict):
        if self.fallback_mode:
            # Memory Storage
            fact_id = fact.get("id")
            if not fact_id: return
            self.memory_store[fact_id] = fact
            return {"status": "saved_to_memory", "id": fact_id}
        else:
            # MongoDB Storage with upsert
            await self.db.facts.update_one(
                {"id": fact["id"]},
                {"$set": fact},
                upsert=True
            )
            # Log history (Self-Healing Requirement)
            history_entry = {
                "fact_id": fact["id"],
                "content": fact["content"],
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": fact.get("metadata", {})
            }
            await self.db.history.insert_one(history_entry)
            return {"status": "saved_to_mongo", "id": fact["id"]}

    async def get_total_facts(self):
        if self.fallback_mode:
            return len(self.memory_store)
        return await self.db.facts.count_documents({})

db = Database()
