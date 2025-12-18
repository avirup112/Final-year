from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn
import logging
from auditor import run_audit
from contextlib import asynccontextmanager

# Configure Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("healing-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_audit, 'interval', minutes=2) # Run audit every 2 minutes
    scheduler.start()
    logger.info("⏰ Healing Scheduler Started")
    yield
    scheduler.shutdown()

app = FastAPI(title="Self-Healing Orchestrator", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "healing-service", "role": "orchestrator"}

@app.post("/trigger")
async def trigger_manual_audit():
    """Manually trigger a healing cycle"""
    await run_audit()
    return {"status": "triggered"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8014, reload=True)
