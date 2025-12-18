from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import json
import logging
from typing import Any, Optional, Dict, List
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Cache Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DEFAULT_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes

# Redis client
redis_client = None

class CacheItem(BaseModel):
    key: str
    value: Any
    ttl: Optional[int] = DEFAULT_TTL

class CacheResponse(BaseModel):
    key: str
    value: Any
    exists: bool
    ttl: Optional[int] = None

class CacheStats(BaseModel):
    total_keys: int
    memory_usage: str
    hit_rate: float
    connected_clients: int
    uptime: int

@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection"""
    if redis_client:
        await redis_client.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "service": "cache-service",
            "redis_connected": True,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {str(e)}")

def generate_cache_key(prefix: str, identifier: str) -> str:
    """Generate consistent cache key"""
    # Create hash of identifier for consistent key length
    hash_obj = hashlib.md5(identifier.encode())
    return f"cache:{prefix}:{hash_obj.hexdigest()}"

@app.post("/cache/set")
async def set_cache(item: CacheItem):
    """Set cache item"""
    try:
        # Serialize value to JSON
        serialized_value = json.dumps(item.value, default=str)
        
        # Set with TTL
        if item.ttl:
            await redis_client.setex(item.key, item.ttl, serialized_value)
        else:
            await redis_client.set(item.key, serialized_value)
        
        logger.info(f"Cache set: {item.key} (TTL: {item.ttl})")
        
        return {
            "status": "success",
            "key": item.key,
            "ttl": item.ttl,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Cache set failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/get/{key}", response_model=CacheResponse)
async def get_cache(key: str):
    """Get cache item"""
    try:
        # Get value
        value = await redis_client.get(key)
        
        if value is not None:
            # Deserialize JSON
            deserialized_value = json.loads(value)
            
            # Get TTL
            ttl = await redis_client.ttl(key)
            ttl = ttl if ttl > 0 else None
            
            return CacheResponse(
                key=key,
                value=deserialized_value,
                exists=True,
                ttl=ttl
            )
        else:
            return CacheResponse(
                key=key,
                value=None,
                exists=False,
                ttl=None
            )
            
    except Exception as e:
        logger.error(f"Cache get failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/cache/delete/{key}")
async def delete_cache(key: str):
    """Delete cache item"""
    try:
        result = await redis_client.delete(key)
        
        return {
            "status": "success",
            "key": key,
            "deleted": bool(result),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Cache delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/clear")
async def clear_cache(pattern: Optional[str] = None):
    """Clear cache items by pattern"""
    try:
        if pattern:
            # Delete keys matching pattern
            keys = await redis_client.keys(pattern)
            if keys:
                deleted_count = await redis_client.delete(*keys)
            else:
                deleted_count = 0
        else:
            # Clear all cache keys (only cache: prefixed)
            keys = await redis_client.keys("cache:*")
            if keys:
                deleted_count = await redis_client.delete(*keys)
            else:
                deleted_count = 0
        
        return {
            "status": "success",
            "pattern": pattern or "cache:*",
            "deleted_count": deleted_count,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats():
    """Get cache statistics"""
    try:
        info = await redis_client.info()
        
        # Calculate hit rate (approximate)
        keyspace_hits = info.get("keyspace_hits", 0)
        keyspace_misses = info.get("keyspace_misses", 0)
        total_commands = keyspace_hits + keyspace_misses
        hit_rate = (keyspace_hits / total_commands * 100) if total_commands > 0 else 0
        
        return CacheStats(
            total_keys=info.get("db0", {}).get("keys", 0),
            memory_usage=f"{info.get('used_memory_human', 'N/A')}",
            hit_rate=round(hit_rate, 2),
            connected_clients=info.get("connected_clients", 0),
            uptime=info.get("uptime_in_seconds", 0)
        )
        
    except Exception as e:
        logger.error(f"Cache stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/keys")
async def list_cache_keys(pattern: str = "cache:*", limit: int = 100):
    """List cache keys"""
    try:
        keys = await redis_client.keys(pattern)
        
        # Limit results
        limited_keys = keys[:limit] if len(keys) > limit else keys
        
        # Get key info
        key_info = []
        for key in limited_keys:
            ttl = await redis_client.ttl(key)
            key_type = await redis_client.type(key)
            
            key_info.append({
                "key": key,
                "type": key_type,
                "ttl": ttl if ttl > 0 else None
            })
        
        return {
            "pattern": pattern,
            "total_found": len(keys),
            "returned": len(limited_keys),
            "keys": key_info,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"List keys failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Specialized cache methods for crypto knowledge system

@app.post("/cache/crypto/price")
async def cache_crypto_price(symbol: str, price_data: dict, ttl: int = 300):
    """Cache crypto price data"""
    key = generate_cache_key("crypto_price", symbol)
    
    cache_item = CacheItem(
        key=key,
        value={
            "symbol": symbol,
            "data": price_data,
            "cached_at": datetime.utcnow().isoformat()
        },
        ttl=ttl
    )
    
    return await set_cache(cache_item)

@app.get("/cache/crypto/price/{symbol}")
async def get_cached_crypto_price(symbol: str):
    """Get cached crypto price data"""
    key = generate_cache_key("crypto_price", symbol)
    return await get_cache(key)

@app.post("/cache/query/result")
async def cache_query_result(query: str, result: dict, ttl: int = 600):
    """Cache query result"""
    key = generate_cache_key("query_result", query)
    
    cache_item = CacheItem(
        key=key,
        value={
            "query": query,
            "result": result,
            "cached_at": datetime.utcnow().isoformat()
        },
        ttl=ttl
    )
    
    return await set_cache(cache_item)

@app.get("/cache/query/result")
async def get_cached_query_result(query: str):
    """Get cached query result"""
    key = generate_cache_key("query_result", query)
    return await get_cache(key)

@app.post("/cache/embedding")
async def cache_embedding(text: str, embedding: List[float], ttl: int = 3600):
    """Cache text embedding"""
    key = generate_cache_key("embedding", text)
    
    cache_item = CacheItem(
        key=key,
        value={
            "text": text,
            "embedding": embedding,
            "dimensions": len(embedding),
            "cached_at": datetime.utcnow().isoformat()
        },
        ttl=ttl
    )
    
    return await set_cache(cache_item)

@app.get("/cache/embedding")
async def get_cached_embedding(text: str):
    """Get cached embedding"""
    key = generate_cache_key("embedding", text)
    return await get_cache(key)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)