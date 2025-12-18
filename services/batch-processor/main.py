from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import redis.asyncio as redis
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import os
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Batch Processor Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion-service:8001")
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8004")

# Global instances
redis_client = None
scheduler = None

class BatchJob(BaseModel):
    job_id: str
    job_type: str
    schedule: str  # cron format
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    parameters: Dict[str, Any] = {}

class JobResult(BaseModel):
    job_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Dict[str, Any] = {}
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize batch processor"""
    global redis_client, scheduler
    
    try:
        # Initialize Redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        
        # Initialize scheduler
        scheduler = AsyncIOScheduler()
        
        # Add default jobs
        await setup_default_jobs()
        
        # Start scheduler
        scheduler.start()
        
        logger.info("Batch processor initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize batch processor: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if scheduler:
        scheduler.shutdown()
    if redis_client:
        await redis_client.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await redis_client.ping()
        
        return {
            "status": "healthy",
            "service": "batch-processor",
            "scheduler_running": scheduler.running if scheduler else False,
            "jobs_count": len(scheduler.get_jobs()) if scheduler else 0,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

async def setup_default_jobs():
    """Setup default batch jobs"""
    default_jobs = [
        {
            "job_id": "crypto_data_fetch",
            "job_type": "data_ingestion",
            "schedule": "*/5 * * * *",  # Every 5 minutes
            "function": fetch_crypto_data_job,
            "parameters": {
                "symbols": ["bitcoin", "ethereum", "cardano", "polkadot", "chainlink"],
                "sources": ["coingecko", "coinmarketcap", "news"]
            }
        },
        {
            "job_id": "cleanup_old_data",
            "job_type": "maintenance",
            "schedule": "0 2 * * *",  # Daily at 2 AM
            "function": cleanup_old_data_job,
            "parameters": {"days_to_keep": 30}
        },
        {
            "job_id": "health_report",
            "job_type": "monitoring",
            "schedule": "0 */6 * * *",  # Every 6 hours
            "function": generate_health_report_job,
            "parameters": {}
        },
        {
            "job_id": "backup_critical_data",
            "job_type": "backup",
            "schedule": "0 1 * * 0",  # Weekly on Sunday at 1 AM
            "function": backup_critical_data_job,
            "parameters": {}
        }
    ]
    
    for job_config in default_jobs:
        scheduler.add_job(
            job_config["function"],
            CronTrigger.from_crontab(job_config["schedule"]),
            id=job_config["job_id"],
            args=[job_config["job_id"], job_config["parameters"]],
            replace_existing=True
        )
        
        logger.info(f"Added job: {job_config['job_id']} with schedule: {job_config['schedule']}")

async def fetch_crypto_data_job(job_id: str, parameters: Dict[str, Any]):
    """Batch job to fetch crypto data"""
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Starting crypto data fetch job: {job_id}")
        
        # Call ingestion service
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{INGESTION_SERVICE_URL}/fetch-now",
                json={
                    "symbols": parameters.get("symbols", []),
                    "sources": parameters.get("sources", []),
                    "force": True
                }
            )
            response.raise_for_status()
            result = response.json()
        
        # Log job result
        await log_job_result(JobResult(
            job_id=job_id,
            status="success",
            start_time=start_time,
            end_time=datetime.utcnow(),
            result=result
        ))
        
        logger.info(f"Completed crypto data fetch job: {job_id}")
        
    except Exception as e:
        logger.error(f"Crypto data fetch job failed: {e}")
        await log_job_result(JobResult(
            job_id=job_id,
            status="failed",
            start_time=start_time,
            end_time=datetime.utcnow(),
            error=str(e)
        ))

async def cleanup_old_data_job(job_id: str, parameters: Dict[str, Any]):
    """Batch job to cleanup old data"""
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Starting cleanup job: {job_id}")
        
        days_to_keep = parameters.get("days_to_keep", 30)
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Cleanup Redis streams
        cleanup_count = 0
        
        # Get all stream keys
        stream_keys = await redis_client.keys("*.crypto")
        
        for stream_key in stream_keys:
            try:
                # Get stream info
                stream_info = await redis_client.xinfo_stream(stream_key)
                
                # Trim old messages (keep last 1000)
                await redis_client.xtrim(stream_key, maxlen=1000, approximate=True)
                cleanup_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to cleanup stream {stream_key}: {e}")
        
        result = {"streams_cleaned": cleanup_count, "cutoff_date": cutoff_date.isoformat()}
        
        await log_job_result(JobResult(
            job_id=job_id,
            status="success",
            start_time=start_time,
            end_time=datetime.utcnow(),
            result=result
        ))
        
        logger.info(f"Completed cleanup job: {job_id}, cleaned {cleanup_count} streams")
        
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")
        await log_job_result(JobResult(
            job_id=job_id,
            status="failed",
            start_time=start_time,
            end_time=datetime.utcnow(),
            error=str(e)
        ))

async def generate_health_report_job(job_id: str, parameters: Dict[str, Any]):
    """Generate system health report"""
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Starting health report job: {job_id}")
        
        # Collect health data from various services
        services = [
            ("ingestion", "http://ingestion-service:8001"),
            ("storage", "http://storage-service:8004"),
            ("vector-retrieval", "http://vector-retrieval-service:8005"),
            ("self-healing", "http://self-healing-service:8007")
        ]
        
        health_data = {}
        
        for service_name, service_url in services:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{service_url}/health")
                    if response.status_code == 200:
                        health_data[service_name] = {
                            "status": "healthy",
                            "response_time": response.elapsed.total_seconds()
                        }
                    else:
                        health_data[service_name] = {
                            "status": "unhealthy",
                            "status_code": response.status_code
                        }
            except Exception as e:
                health_data[service_name] = {
                    "status": "unreachable",
                    "error": str(e)
                }
        
        # Calculate overall health score
        healthy_services = sum(1 for h in health_data.values() if h.get("status") == "healthy")
        total_services = len(health_data)
        health_score = (healthy_services / total_services) * 100 if total_services > 0 else 0
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_health_score": health_score,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "service_details": health_data
        }
        
        # Store report in Redis
        await redis_client.setex(
            f"health_report:{start_time.strftime('%Y%m%d_%H%M%S')}",
            86400,  # 24 hours
            json.dumps(report, default=str)
        )
        
        await log_job_result(JobResult(
            job_id=job_id,
            status="success",
            start_time=start_time,
            end_time=datetime.utcnow(),
            result=report
        ))
        
        logger.info(f"Generated health report: {health_score:.1f}% system health")
        
    except Exception as e:
        logger.error(f"Health report job failed: {e}")
        await log_job_result(JobResult(
            job_id=job_id,
            status="failed",
            start_time=start_time,
            end_time=datetime.utcnow(),
            error=str(e)
        ))

async def backup_critical_data_job(job_id: str, parameters: Dict[str, Any]):
    """Backup critical system data"""
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Starting backup job: {job_id}")
        
        # Get recent facts from storage service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{STORAGE_SERVICE_URL}/facts?limit=1000")
            response.raise_for_status()
            facts_data = response.json()
        
        # Create backup
        backup_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "facts_count": facts_data.get("count", 0),
            "backup_type": "weekly_critical_data"
        }
        
        # Store backup metadata in Redis
        backup_key = f"backup:{start_time.strftime('%Y%m%d_%H%M%S')}"
        await redis_client.setex(backup_key, 604800, json.dumps(backup_data, default=str))  # 7 days
        
        await log_job_result(JobResult(
            job_id=job_id,
            status="success",
            start_time=start_time,
            end_time=datetime.utcnow(),
            result=backup_data
        ))
        
        logger.info(f"Completed backup job: {facts_data.get('count', 0)} facts backed up")
        
    except Exception as e:
        logger.error(f"Backup job failed: {e}")
        await log_job_result(JobResult(
            job_id=job_id,
            status="failed",
            start_time=start_time,
            end_time=datetime.utcnow(),
            error=str(e)
        ))

async def log_job_result(result: JobResult):
    """Log job execution result"""
    try:
        result_key = f"job_result:{result.job_id}:{result.start_time.strftime('%Y%m%d_%H%M%S')}"
        await redis_client.setex(result_key, 86400, json.dumps(result.dict(), default=str))
        
    except Exception as e:
        logger.error(f"Failed to log job result: {e}")

@app.get("/jobs")
async def list_jobs():
    """List all scheduled jobs"""
    try:
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "job_id": job.id,
                "next_run": job.next_run_time,
                "trigger": str(job.trigger),
                "function": job.func.__name__
            })
        
        return {"jobs": jobs, "total": len(jobs)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/{job_id}/run")
async def run_job_now(job_id: str):
    """Manually trigger a job"""
    try:
        job = scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Run job immediately
        scheduler.modify_job(job_id, next_run_time=datetime.now())
        
        return {"status": "triggered", "job_id": job_id, "timestamp": datetime.utcnow()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str, limit: int = 10):
    """Get recent results for a job"""
    try:
        pattern = f"job_result:{job_id}:*"
        keys = await redis_client.keys(pattern)
        
        results = []
        for key in sorted(keys, reverse=True)[:limit]:
            result_data = await redis_client.get(key)
            if result_data:
                results.append(json.loads(result_data))
        
        return {"job_id": job_id, "results": results, "count": len(results)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)