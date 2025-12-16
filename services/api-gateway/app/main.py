from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crypto Knowledge API Gateway",
    description="Unified API gateway for the crypto knowledge system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "crypto-knowledge-secret-key")
API_KEY = os.getenv("API_KEY", "crypto-knowledge-api-key")

# Service URLs
SERVICES = {
    "ingestion": os.getenv("INGESTION_SERVICE_URL", "http://ingestion-service:8001"),
    "fact-extraction": os.getenv("FACT_EXTRACTION_SERVICE_URL", "http://fact-extraction-service:8002"),
    "embedding": os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service:8003"),
    "storage": os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8004"),
    "vector-retrieval": os.getenv("VECTOR_RETRIEVAL_SERVICE_URL", "http://vector-retrieval-service:8005"),
    "llm-generator": os.getenv("LLM_GENERATOR_SERVICE_URL", "http://llm-generator-service:8006"),
    "self-healing": os.getenv("SELF_HEALING_SERVICE_URL", "http://self-healing-service:8007"),
    "cache": os.getenv("CACHE_SERVICE_URL", "http://cache-service:8008")
}

# Security
security = HTTPBearer()

class AuthRequest(BaseModel):
    api_key: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class QueryRequest(BaseModel):
    question: str
    n_results: int = 5
    collection_name: str = "crypto_facts"

class FetchRequest(BaseModel):
    symbols: list = ["bitcoin", "ethereum", "cardano"]
    sources: list = ["coingecko", "coinmarketcap", "news"]
    force: bool = False

def verify_api_key(api_key: str) -> bool:
    """Verify API key"""
    return api_key == API_KEY

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def proxy_request(service_name: str, endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Proxy request to microservice"""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    service_url = SERVICES[service_name]
    url = f"{service_url}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=data)
            elif method == "PUT":
                response = await client.put(url, json=data)
            elif method == "DELETE":
                response = await client.delete(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Service error: {response.text}"
                )
                
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Gateway health check"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.utcnow(),
        "services_configured": len(SERVICES)
    }

@app.post("/auth/token", response_model=TokenResponse)
async def authenticate(auth_request: AuthRequest):
    """Authenticate and get access token"""
    if not verify_api_key(auth_request.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    access_token = create_access_token(data={"sub": "crypto-knowledge-user"})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400  # 24 hours
    )

@app.get("/services/status")
async def get_services_status(user: dict = Depends(verify_token)):
    """Get status of all services"""
    status_results = {}
    
    for service_name, service_url in SERVICES.items():
        try:
            result = await proxy_request(service_name, "/health")
            status_results[service_name] = {
                "status": "healthy",
                "url": service_url,
                "response": result
            }
        except Exception as e:
            status_results[service_name] = {
                "status": "unhealthy",
                "url": service_url,
                "error": str(e)
            }
    
    return {
        "timestamp": datetime.utcnow(),
        "services": status_results
    }

@app.post("/knowledge/query")
async def query_knowledge(
    request: QueryRequest,
    user: dict = Depends(verify_token)
):
    """Query the knowledge system"""
    try:
        result = await proxy_request(
            "vector-retrieval",
            "/rag-query",
            "POST",
            request.dict()
        )
        
        return {
            "status": "success",
            "query": request.question,
            "results": result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Knowledge query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/fetch")
async def trigger_data_fetch(
    request: FetchRequest,
    user: dict = Depends(verify_token)
):
    """Trigger data ingestion"""
    try:
        result = await proxy_request(
            "ingestion",
            "/fetch-now",
            "POST",
            request.dict()
        )
        
        return {
            "status": "success",
            "fetch_request": request.dict(),
            "result": result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/facts")
async def get_facts(
    category: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(verify_token)
):
    """Get stored facts"""
    try:
        endpoint = f"/facts?limit={limit}"
        if category:
            endpoint += f"&category={category}"
            
        result = await proxy_request("storage", endpoint)
        
        return {
            "status": "success",
            "facts": result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Facts retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embeddings/generate")
async def generate_embeddings(
    texts: list,
    user: dict = Depends(verify_token)
):
    """Generate embeddings for texts"""
    try:
        result = await proxy_request(
            "embedding",
            "/embed",
            "POST",
            {"texts": texts, "normalize": True}
        )
        
        return {
            "status": "success",
            "embeddings": result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/health")
async def get_system_health(user: dict = Depends(verify_token)):
    """Get overall system health"""
    try:
        result = await proxy_request("self-healing", "/system/health")
        
        return {
            "status": "success",
            "system_health": result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/healing-events")
async def get_healing_events(
    limit: int = 50,
    user: dict = Depends(verify_token)
):
    """Get recent healing events"""
    try:
        result = await proxy_request("self-healing", f"/healing/events?limit={limit}")
        
        return {
            "status": "success",
            "healing_events": result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Healing events retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections")
async def get_collections(user: dict = Depends(verify_token)):
    """Get available vector collections"""
    try:
        result = await proxy_request("vector-retrieval", "/collections")
        
        return {
            "status": "success",
            "collections": result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Collections retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Public endpoints (no authentication required)
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Crypto Knowledge API Gateway",
        "version": "1.0.0",
        "description": "Unified API for crypto knowledge system",
        "endpoints": {
            "authentication": "/auth/token",
            "knowledge_query": "/knowledge/query",
            "data_fetch": "/data/fetch",
            "system_health": "/system/health",
            "documentation": "/docs"
        },
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)