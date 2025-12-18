from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
import redis.asyncio as redis
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import os
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Fact Extraction Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Redis client
redis_client = None

class RawDataModel(BaseModel):
    source: str
    symbol: str
    data: Dict[str, Any]
    timestamp: datetime

class ExtractedFact(BaseModel):
    content: str
    category: str
    confidence_score: float
    source: str
    symbol: str
    metadata: Dict[str, Any] = {}

class ExtractionRequest(BaseModel):
    raw_data: RawDataModel
    extraction_type: str = "crypto_facts"

@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection and start background processing"""
    global redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis successfully")
        
        # Start background task to process raw crypto data
        asyncio.create_task(process_raw_data_stream())
        
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
        groq_available = bool(GROQ_API_KEY)
        
        return {
            "status": "healthy",
            "service": "fact-extraction-service",
            "redis_connected": True,
            "groq_configured": groq_available,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

async def call_groq_api(prompt: str, model: str = "mixtral-8x7b-32768") -> str:
    """Call Groq API for fact extraction"""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Groq API key not configured")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert crypto analyst. Extract key facts from crypto data and present them as clear, concise statements. Focus on price movements, market trends, and significant events."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")

def create_extraction_prompt(raw_data: RawDataModel) -> str:
    """Create prompt for fact extraction"""
    data_str = json.dumps(raw_data.data, indent=2)
    
    prompt = f"""
Extract key cryptocurrency facts from the following {raw_data.source} data for {raw_data.symbol}:

Data:
{data_str}

Please extract 3-5 key facts in the following JSON format:
{{
    "facts": [
        {{
            "content": "Clear, concise fact statement",
            "category": "price|volume|market_cap|news|technical|fundamental",
            "confidence_score": 0.95,
            "metadata": {{"relevant_key": "value"}}
        }}
    ]
}}

Focus on:
- Price movements and trends
- Volume changes
- Market capitalization updates
- Significant news or events
- Technical indicators
- Fundamental analysis points

Ensure facts are:
- Specific and actionable
- Include numerical data when available
- Categorized correctly
- Assigned appropriate confidence scores (0.0-1.0)
"""
    return prompt

async def extract_facts_from_data(raw_data: RawDataModel) -> List[ExtractedFact]:
    """Extract facts from raw crypto data using Groq"""
    try:
        prompt = create_extraction_prompt(raw_data)
        groq_response = await call_groq_api(prompt)
        
        # Parse Groq response
        try:
            parsed_response = json.loads(groq_response)
            facts = []
            
            for fact_data in parsed_response.get("facts", []):
                fact = ExtractedFact(
                    content=fact_data["content"],
                    category=fact_data["category"],
                    confidence_score=fact_data["confidence_score"],
                    source=raw_data.source,
                    symbol=raw_data.symbol,
                    metadata={
                        **fact_data.get("metadata", {}),
                        "extraction_timestamp": datetime.utcnow().isoformat(),
                        "raw_data_timestamp": raw_data.timestamp.isoformat()
                    }
                )
                facts.append(fact)
            
            return facts
            
        except json.JSONDecodeError:
            # Fallback: create a single fact from the response
            logger.warning("Failed to parse Groq JSON response, using fallback")
            return [ExtractedFact(
                content=groq_response[:500],  # Truncate if too long
                category="general",
                confidence_score=0.7,
                source=raw_data.source,
                symbol=raw_data.symbol,
                metadata={"extraction_method": "fallback"}
            )]
            
    except Exception as e:
        logger.error(f"Fact extraction failed: {e}")
        return []

@app.post("/extract", response_model=List[ExtractedFact])
async def extract_facts(request: ExtractionRequest):
    """Extract facts from raw crypto data"""
    try:
        facts = await extract_facts_from_data(request.raw_data)
        
        # Publish extracted facts to embedding queue
        for fact in facts:
            await publish_to_embedding_queue(fact)
        
        logger.info(f"Extracted {len(facts)} facts from {request.raw_data.source} data for {request.raw_data.symbol}")
        return facts
        
    except Exception as e:
        logger.error(f"Fact extraction request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def publish_to_embedding_queue(fact: ExtractedFact):
    """Publish extracted fact to embedding service queue"""
    try:
        message = {
            "action": "generate_embedding",
            "fact": fact.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await redis_client.xadd("embedding.queue", message)
        logger.debug(f"Published fact to embedding queue: {fact.content[:50]}...")
        
    except Exception as e:
        logger.error(f"Failed to publish to embedding queue: {e}")

async def process_raw_data_stream():
    """Background task to process raw crypto data from Redis stream"""
    logger.info("Starting raw data stream processing...")
    
    while True:
        try:
            # Read from raw.crypto stream
            messages = await redis_client.xread(
                {"raw.crypto": "$"}, 
                count=10, 
                block=5000  # 5 second timeout
            )
            
            for stream_name, stream_messages in messages:
                for message_id, fields in stream_messages:
                    try:
                        # Parse message
                        raw_data = RawDataModel(
                            source=fields["source"],
                            symbol=fields["symbol"],
                            data=json.loads(fields["data"]),
                            timestamp=datetime.fromisoformat(fields["timestamp"])
                        )
                        
                        # Extract facts
                        facts = await extract_facts_from_data(raw_data)
                        
                        # Publish to embedding queue
                        for fact in facts:
                            await publish_to_embedding_queue(fact)
                        
                        logger.info(f"Processed {len(facts)} facts from {raw_data.source} for {raw_data.symbol}")
                        
                    except Exception as e:
                        logger.error(f"Failed to process message {message_id}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Stream processing error: {e}")
            await asyncio.sleep(10)  # Wait before retry

@app.get("/stats")
async def get_extraction_stats():
    """Get fact extraction statistics"""
    try:
        # Get stream info
        stream_info = await redis_client.xinfo_stream("raw.crypto")
        
        return {
            "service": "fact-extraction-service",
            "groq_configured": bool(GROQ_API_KEY),
            "raw_data_stream_length": stream_info.get("length", 0),
            "status": "processing",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        return {
            "service": "fact-extraction-service",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)