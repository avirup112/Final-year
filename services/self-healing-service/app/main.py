from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import redis
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import logging
import json
import os
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Self-Healing Orchestrator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password123@localhost:27017/crypto_knowledge?authSource=admin")

# Service endpoints
SERVICES = {
    "ingestion-service": "http://ingestion-service:8001",
    "fact-extraction-service": "http://fact-extraction-service:8002", 
    "embedding-service": "http://embedding-service:8003",
    "storage-service": "http://storage-service:8004",
    "vector-retrieval-service": "http://vector-retrieval-service:8005",
    "llm-generator-service": "http://llm-generator-service:8006",
    "cache-service": "http://cache-service:8008"
}

# Initialize connections
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
mongo_client = AsyncIOMotorClient(MONGODB_URL)
db = mongo_client.crypto_knowledge

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class HealingAction(str, Enum):
    RESTART = "restart"
    SCALE_UP = "scale_up"
    CIRCUIT_BREAK = "circuit_break"
    FALLBACK = "fallback"
    DATA_REPAIR = "data_repair"
    CACHE_CLEAR = "cache_clear"

class ServiceHealth(BaseModel):
    service_name: str
    status: ServiceStatus
    response_time: float
    last_check: datetime
    error_count: int
    metadata: Dict[str, Any] = {}

class HealingEvent(BaseModel):
    service_name: str
    issue_type: str
    action_taken: HealingAction
    timestamp: datetime
    success: bool
    details: Dict[str, Any] = {}

# Global state
service_health: Dict[str, ServiceHealth] = {}
healing_in_progress: Dict[str, bool] = {}
circuit_breakers: Dict[str, Dict] = {}

@app.on_event("startup")
async def startup_event():
    try:
        redis_client.ping()
        await mongo_client.admin.command('ping')
        
        for service_name in SERVICES.keys():
            circuit_breakers[service_name] = {
                "failure_count": 0,
                "last_failure": None,
                "state": "closed",
                "failure_threshold": 5,
                "recovery_timeout": 60
            }
        
        asyncio.create_task(continuous_health_monitoring())
        asyncio.create_task(self_healing_loop())
        
        logger.info("Self-healing orchestrator initialized")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")

@app.get("/health")
async def health_check():
    try:
        redis_client.ping()
        await mongo_client.admin.command('ping')
        return {
            "status": "healthy",
            "service": "self-healing-service",
            "monitoring_active": True
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

async def check_service_health(service_name: str, service_url: str) -> ServiceHealth:
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{service_url}/health")
            response_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                status = ServiceStatus.HEALTHY
                error_count = 0
            else:
                status = ServiceStatus.DEGRADED
                error_count = 1
                
            return ServiceHealth(
                service_name=service_name,
                status=status,
                response_time=response_time,
                last_check=datetime.now(),
                error_count=error_count,
                metadata={"status_code": response.status_code}
            )
            
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Health check failed for {service_name}: {e}")
        
        return ServiceHealth(
            service_name=service_name,
            status=ServiceStatus.UNHEALTHY,
            response_time=response_time,
            last_check=datetime.now(),
            error_count=1,
            metadata={"error": str(e)}
        )

async def continuous_health_monitoring():
    while True:
        try:
            for service_name, service_url in SERVICES.items():
                health = await check_service_health(service_name, service_url)
                service_health[service_name] = health
                
                await update_circuit_breaker(service_name, health.status)
                
                redis_client.setex(
                    f"health:{service_name}",
                    300,
                    json.dumps(health.dict(), default=str)
                )
            
            await update_system_metrics()
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")
            await asyncio.sleep(60)

async def update_circuit_breaker(service_name: str, status: ServiceStatus):
    cb = circuit_breakers[service_name]
    
    if status == ServiceStatus.UNHEALTHY:
        cb["failure_count"] += 1
        cb["last_failure"] = datetime.now()
        
        if cb["failure_count"] >= cb["failure_threshold"]:
            cb["state"] = "open"
            logger.warning(f"Circuit breaker OPEN for {service_name}")
            
    elif status == ServiceStatus.HEALTHY:
        if cb["state"] == "half-open":
            cb["state"] = "closed"
            cb["failure_count"] = 0
            logger.info(f"Circuit breaker CLOSED for {service_name}")
        elif cb["state"] == "closed":
            cb["failure_count"] = max(0, cb["failure_count"] - 1)

async def self_healing_loop():
    while True:
        try:
            for service_name, health in service_health.items():
                if service_name in healing_in_progress and healing_in_progress[service_name]:
                    continue
                    
                if health.status == ServiceStatus.UNHEALTHY:
                    await trigger_healing_action(service_name, health)
                elif health.status == ServiceStatus.DEGRADED:
                    await trigger_preventive_action(service_name, health)
            
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Self-healing loop error: {e}")
            await asyncio.sleep(120)

async def trigger_healing_action(service_name: str, health: ServiceHealth):
    healing_in_progress[service_name] = True
    
    try:
        logger.warning(f"Triggering healing for unhealthy service: {service_name}")
        
        action = await determine_healing_action(service_name, health)
        success = await execute_healing_action(service_name, action, health)
        
        await log_healing_event(service_name, "service_unhealthy", action, success, health.metadata)
        
        if success:
            logger.info(f"Healing successful for {service_name}")
        else:
            logger.error(f"Healing failed for {service_name}")
            
    except Exception as e:
        logger.error(f"Healing action failed for {service_name}: {e}")
        await log_healing_event(service_name, "healing_error", HealingAction.RESTART, False, {"error": str(e)})
        
    finally:
        healing_in_progress[service_name] = False

async def trigger_preventive_action(service_name: str, health: ServiceHealth):
    try:
        logger.info(f"Triggering preventive action for degraded service: {service_name}")
        
        if health.response_time > 5.0:
            await execute_healing_action(service_name, HealingAction.CACHE_CLEAR, health)
            
        await log_healing_event(service_name, "preventive_maintenance", HealingAction.CACHE_CLEAR, True, health.metadata)
        
    except Exception as e:
        logger.error(f"Preventive action failed for {service_name}: {e}")

async def determine_healing_action(service_name: str, health: ServiceHealth) -> HealingAction:
    if "connection" in str(health.metadata.get("error", "")).lower():
        return HealingAction.RESTART
    elif health.response_time > 10.0:
        return HealingAction.CACHE_CLEAR
    elif health.error_count > 10:
        return HealingAction.CIRCUIT_BREAK
    else:
        return HealingAction.RESTART

async def execute_healing_action(service_name: str, action: HealingAction, health: ServiceHealth) -> bool:
    try:
        if action == HealingAction.RESTART:
            return await restart_service(service_name)
        elif action == HealingAction.CACHE_CLEAR:
            return await clear_service_cache(service_name)
        elif action == HealingAction.CIRCUIT_BREAK:
            return await activate_circuit_breaker(service_name)
        else:
            logger.warning(f"Unknown healing action: {action}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to execute {action} for {service_name}: {e}")
        return False

async def restart_service(service_name: str) -> bool:
    try:
        logger.info(f"Restarting service: {service_name}")
        await asyncio.sleep(10)
        
        if service_name in SERVICES:
            health = await check_service_health(service_name, SERVICES[service_name])
            return health.status != ServiceStatus.UNHEALTHY
            
        return True
        
    except Exception as e:
        logger.error(f"Service restart failed for {service_name}: {e}")
        return False

async def clear_service_cache(service_name: str) -> bool:
    try:
        logger.info(f"Clearing cache for service: {service_name}")
        
        pattern = f"cache:{service_name}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            
        return True
        
    except Exception as e:
        logger.error(f"Cache clear failed for {service_name}: {e}")
        return False

async def activate_circuit_breaker(service_name: str) -> bool:
    try:
        circuit_breakers[service_name]["state"] = "open"
        circuit_breakers[service_name]["last_failure"] = datetime.now()
        
        logger.warning(f"Circuit breaker activated for {service_name}")
        return True
        
    except Exception as e:
        logger.error(f"Circuit breaker activation failed for {service_name}: {e}")
        return False

async def log_healing_event(service_name: str, issue_type: str, action: HealingAction, success: bool, details: Dict):
    try:
        event = HealingEvent(
            service_name=service_name,
            issue_type=issue_type,
            action_taken=action,
            timestamp=datetime.now(),
            success=success,
            details=details
        )
        
        await db.healing_events.insert_one(event.dict())
        
    except Exception as e:
        logger.error(f"Failed to log healing event: {e}")

async def update_system_metrics():
    try:
        total = len(service_health)
        healthy = sum(1 for h in service_health.values() if h.status == ServiceStatus.HEALTHY)
        degraded = sum(1 for h in service_health.values() if h.status == ServiceStatus.DEGRADED)
        unhealthy = sum(1 for h in service_health.values() if h.status == ServiceStatus.UNHEALTHY)
        
        health_score = (healthy + degraded * 0.5) / total if total > 0 else 0
        
        metrics = {
            "total_services": total,
            "healthy_services": healthy,
            "degraded_services": degraded,
            "unhealthy_services": unhealthy,
            "overall_health_score": health_score,
            "last_updated": datetime.now()
        }
        
        redis_client.setex("system:metrics", 300, json.dumps(metrics, default=str))
        
    except Exception as e:
        logger.error(f"Failed to update system metrics: {e}")

@app.get("/system/health")
async def get_system_health():
    try:
        metrics_data = redis_client.get("system:metrics")
        if metrics_data:
            metrics = json.loads(metrics_data)
        else:
            metrics = {"error": "No metrics available"}
            
        return {
            "system_metrics": metrics,
            "service_health": {name: health.dict() for name, health in service_health.items()},
            "circuit_breakers": circuit_breakers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/healing/events")
async def get_healing_events(limit: int = 50):
    try:
        cursor = db.healing_events.find().sort("timestamp", -1).limit(limit)
        events = []
        async for event in cursor:
            event["_id"] = str(event["_id"])
            events.append(event)
            
        return {"events": events, "count": len(events)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/healing/trigger/{service_name}")
async def manual_healing_trigger(service_name: str, action: HealingAction):
    try:
        if service_name not in SERVICES:
            raise HTTPException(status_code=404, detail="Service not found")
            
        health = service_health.get(service_name)
        if not health:
            health = await check_service_health(service_name, SERVICES[service_name])
            
        success = await execute_healing_action(service_name, action, health)
        await log_healing_event(service_name, "manual_trigger", action, success, {"triggered_by": "manual"})
        
        return {"status": "triggered", "action": action, "success": success}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)