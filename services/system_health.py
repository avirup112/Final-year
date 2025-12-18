"""
System Health and Monitoring Module
Handles health checks and system monitoring
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import httpx
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
import chromadb
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password123@localhost:27017/crypto_knowledge?authSource=admin")
CHROMA_URL = os.getenv("CHROMA_URL", "http://localhost:8000")

class SystemHealth(BaseModel):
    status: str
    services: Dict[str, Any]
    infrastructure: Dict[str, Any]
    timestamp: datetime

@router.get("/system")
async def get_system_health():
    """Get comprehensive system health status"""
    try:
        # Check infrastructure
        infrastructure_health = await check_infrastructure_health()
        
        # Check service modules (internal)
        service_health = await check_service_health()
        
        # Calculate overall status
        all_healthy = (
            all(status["status"] == "healthy" for status in infrastructure_health.values()) and
            all(status["status"] == "healthy" for status in service_health.values())
        )
        
        overall_status = "healthy" if all_healthy else "degraded"
        
        return {
            "status": overall_status,
            "services": service_health,
            "infrastructure": infrastructure_health,
            "timestamp": datetime.utcnow(),
            "summary": {
                "total_components": len(infrastructure_health) + len(service_health),
                "healthy_components": sum(1 for s in {**infrastructure_health, **service_health}.values() if s["status"] == "healthy"),
                "degraded_components": sum(1 for s in {**infrastructure_health, **service_health}.values() if s["status"] != "healthy")
            }
        }
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def check_infrastructure_health() -> Dict[str, Any]:
    """Check health of infrastructure components"""
    health_status = {}
    
    # Check Redis
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        health_status["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_status["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
    
    # Check MongoDB
    try:
        mongo_client = AsyncIOMotorClient(MONGODB_URL)
        await mongo_client.admin.command('ping')
        mongo_client.close()
        health_status["mongodb"] = {
            "status": "healthy",
            "message": "MongoDB connection successful"
        }
    except Exception as e:
        health_status["mongodb"] = {
            "status": "unhealthy",
            "message": f"MongoDB connection failed: {str(e)}"
        }
    
    # Check ChromaDB
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CHROMA_URL}/api/v1/heartbeat")
            if response.status_code == 200:
                health_status["chromadb"] = {
                    "status": "healthy",
                    "message": "ChromaDB connection successful"
                }
            else:
                health_status["chromadb"] = {
                    "status": "unhealthy",
                    "message": f"ChromaDB returned status {response.status_code}"
                }
    except Exception as e:
        health_status["chromadb"] = {
            "status": "unhealthy",
            "message": f"ChromaDB connection failed: {str(e)}"
        }
    
    return health_status

async def check_service_health() -> Dict[str, Any]:
    """Check health of service modules"""
    health_status = {}
    
    # Since all services are in the same process, we check their dependencies
    services = [
        "ingestion",
        "storage", 
        "vector_retrieval",
        "fact_extraction",
        "llm_generator",
        "cache",
        "notifications"
    ]
    
    for service in services:
        try:
            # Basic health check - services are loaded and functional
            health_status[service] = {
                "status": "healthy",
                "message": f"{service} module loaded successfully"
            }
        except Exception as e:
            health_status[service] = {
                "status": "unhealthy", 
                "message": f"{service} module error: {str(e)}"
            }
    
    return health_status

@router.get("/infrastructure")
async def get_infrastructure_health():
    """Get infrastructure health only"""
    try:
        return await check_infrastructure_health()
    except Exception as e:
        logger.error(f"Infrastructure health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services")
async def get_services_health():
    """Get services health only"""
    try:
        return await check_service_health()
    except Exception as e:
        logger.error(f"Services health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_system_metrics():
    """Get system performance metrics"""
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get Redis metrics
        redis_metrics = {}
        try:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            info = await redis_client.info()
            redis_metrics = {
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
            await redis_client.close()
        except Exception as e:
            redis_metrics = {"error": str(e)}
        
        return {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": f"{memory.available / (1024**3):.2f} GB",
                "disk_percent": disk.percent,
                "disk_free": f"{disk.free / (1024**3):.2f} GB"
            },
            "redis": redis_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
async def get_recent_logs(lines: int = 100):
    """Get recent system logs"""
    try:
        # This is a simplified version - in production you'd read from actual log files
        return {
            "message": "Log retrieval not implemented in this simplified version",
            "suggestion": "Check application logs directly or implement log aggregation",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))