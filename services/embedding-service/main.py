from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import os
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Embedding Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Global model instance
model = None

class EmbeddingRequest(BaseModel):
    texts: List[str]
    normalize: bool = True

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model_name: str
    dimensions: int

class SimilarityRequest(BaseModel):
    text1: str
    text2: str

class SimilarityResponse(BaseModel):
    similarity: float
    text1_embedding: List[float]
    text2_embedding: List[float]

@app.on_event("startup")
async def startup_event():
    """Initialize the embedding model"""
    global model
    try:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Test embedding generation
        test_embedding = model.encode(["test"])
        
        return {
            "status": "healthy",
            "service": "embedding-service",
            "model": EMBEDDING_MODEL,
            "dimensions": len(test_embedding[0]),
            "model_loaded": True
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.post("/embed", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for input texts"""
    try:
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        if not request.texts:
            raise HTTPException(status_code=400, detail="No texts provided")
        
        # Generate embeddings
        embeddings = model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            convert_to_numpy=True
        )
        
        # Convert to list format
        embeddings_list = embeddings.tolist()
        
        return EmbeddingResponse(
            embeddings=embeddings_list,
            model_name=EMBEDDING_MODEL,
            dimensions=len(embeddings_list[0]) if embeddings_list else 0
        )
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/similarity", response_model=SimilarityResponse)
async def calculate_similarity(request: SimilarityRequest):
    """Calculate semantic similarity between two texts"""
    try:
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Generate embeddings for both texts
        embeddings = model.encode([request.text1, request.text2])
        
        # Calculate cosine similarity
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        similarity = cosine_similarity(
            embeddings[0].reshape(1, -1),
            embeddings[1].reshape(1, -1)
        )[0][0]
        
        return SimilarityResponse(
            similarity=float(similarity),
            text1_embedding=embeddings[0].tolist(),
            text2_embedding=embeddings[1].tolist()
        )
        
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-embed")
async def batch_generate_embeddings(texts: List[str], batch_size: int = 32):
    """Generate embeddings in batches for large datasets"""
    try:
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        if not texts:
            raise HTTPException(status_code=400, detail="No texts provided")
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = model.encode(batch, convert_to_numpy=True)
            all_embeddings.extend(batch_embeddings.tolist())
            
            # Allow other tasks to run
            await asyncio.sleep(0)
        
        return {
            "embeddings": all_embeddings,
            "total_processed": len(texts),
            "model_name": EMBEDDING_MODEL,
            "dimensions": len(all_embeddings[0]) if all_embeddings else 0
        }
        
    except Exception as e:
        logger.error(f"Error in batch embedding generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model/info")
async def get_model_info():
    """Get information about the loaded model"""
    try:
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Get model dimensions by encoding a test string
        test_embedding = model.encode(["test"])
        
        return {
            "model_name": EMBEDDING_MODEL,
            "dimensions": len(test_embedding[0]),
            "max_seq_length": getattr(model, 'max_seq_length', 'unknown'),
            "model_type": type(model).__name__,
            "device": str(model.device) if hasattr(model, 'device') else 'unknown'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/encode-query")
async def encode_query(query: str, instruction: Optional[str] = None):
    """Encode a query with optional instruction for retrieval"""
    try:
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Add instruction if provided (useful for some models)
        text_to_encode = f"{instruction} {query}" if instruction else query
        
        embedding = model.encode([text_to_encode])
        
        return {
            "query_embedding": embedding[0].tolist(),
            "original_query": query,
            "instruction": instruction,
            "dimensions": len(embedding[0])
        }
        
    except Exception as e:
        logger.error(f"Error encoding query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)