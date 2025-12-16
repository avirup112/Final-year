from fastapi import FastAPI, HTTPException
from datetime import datetime
from shared.models import QueryRequest, QueryResponse
from shared.utils import setup_logging
from .config import settings
from .groq_client import GroqLLMGenerator

# Setup logging
logger = setup_logging(settings.service_name)

# Initialize FastAPI app
app = FastAPI(
    title="LLM Generator Service",
    description="Groq-powered LLM generator with hallucination detection",
    version="1.0.0"
)

# Global generator instance
generator = None

@app.on_event("startup")
async def startup_event():
    global generator
    generator = GroqLLMGenerator()
    logger.info(f"{settings.service_name} started on {settings.host}:{settings.port}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"{settings.service_name} shutting down")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/generate", response_model=QueryResponse)
async def generate_answer(request: QueryRequest):
    """Generate answer for crypto query using Groq LLM"""
    try:
        if not generator:
            raise HTTPException(status_code=503, detail="Generator not initialized")
        
        response = await generator.process_query(request)
        return response
        
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    """Get generator service status"""
    return {
        "service": settings.service_name,
        "status": "running",
        "groq_configured": bool(settings.groq_api_key),
        "model": settings.groq_model,
        "hallucination_detection": settings.fact_verification_enabled
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)