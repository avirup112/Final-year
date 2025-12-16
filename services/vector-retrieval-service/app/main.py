from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import chromadb
from chromadb.config import Settings
import os
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import asyncio
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vector Retrieval Service - RAG Core", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CHROMA_URL = os.getenv("CHROMA_URL", "http://localhost:8000")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service:8003")

# Initialize ChromaDB client
try:
    chroma_host = CHROMA_URL.replace("http://", "").replace("https://", "").split(":")[0]
    chroma_port = int(CHROMA_URL.split(":")[-1])
    chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB client: {e}")
    chroma_client = None

class QueryModel(BaseModel):
    query_text: str
    n_results: int = 5
    collection_name: str = "crypto_facts"
    include_metadata: bool = True
    similarity_threshold: float = 0.7

class StoreModel(BaseModel):
    texts: List[str]
    metadatas: List[Dict[str, Any]]
    ids: List[str]
    collection_name: str = "crypto_facts"

class RAGQueryModel(BaseModel):
    question: str
    n_results: int = 5
    collection_name: str = "crypto_facts"
    context_window: int = 3
    rerank: bool = True

class RAGResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: float
    context_used: List[str]

@app.on_event("startup")
async def startup_event():
    """Initialize ChromaDB collections and test connections"""
    try:
        if chroma_client:
            # Test connection
            chroma_client.heartbeat()
            
            # Get or create collections
            collections = chroma_client.list_collections()
            collection_names = [col.name for col in collections]
            
            required_collections = ["crypto_facts", "crypto_news", "crypto_analysis"]
            
            for collection_name in required_collections:
                if collection_name not in collection_names:
                    chroma_client.create_collection(
                        name=collection_name,
                        metadata={
                            "description": f"Collection for {collection_name.replace('_', ' ')}",
                            "created_at": str(asyncio.get_event_loop().time())
                        }
                    )
                    logger.info(f"Created collection: {collection_name}")
            
            logger.info("ChromaDB initialized successfully")
        else:
            logger.error("ChromaDB client not available")
            
    except Exception as e:
        logger.error(f"Startup failed: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if chroma_client:
            chroma_client.heartbeat()
            return {
                "status": "healthy", 
                "service": "vector-retrieval-service",
                "chroma_connected": True
            }
        else:
            return {
                "status": "degraded",
                "service": "vector-retrieval-service", 
                "chroma_connected": False
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings from embedding service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/embed",
                json={"texts": texts},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["embeddings"]
    except Exception as e:
        logger.error(f"Failed to get embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding service error: {str(e)}")

@app.post("/store")
async def store_vectors(data: StoreModel):
    """Store vectors in ChromaDB with embeddings"""
    try:
        if not chroma_client:
            raise HTTPException(status_code=503, detail="ChromaDB not available")
            
        # Get embeddings for texts
        embeddings = await get_embeddings(data.texts)
        
        # Get or create collection
        try:
            collection = chroma_client.get_collection(data.collection_name)
        except:
            collection = chroma_client.create_collection(data.collection_name)
        
        # Store in ChromaDB
        collection.add(
            documents=data.texts,
            metadatas=data.metadatas,
            ids=data.ids,
            embeddings=embeddings
        )
        
        logger.info(f"Stored {len(data.texts)} vectors in collection {data.collection_name}")
        
        return {
            "status": "stored",
            "count": len(data.texts),
            "collection": data.collection_name
        }
        
    except Exception as e:
        logger.error(f"Error storing vectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_vectors(query: QueryModel):
    """Query vectors using semantic similarity"""
    try:
        if not chroma_client:
            raise HTTPException(status_code=503, detail="ChromaDB not available")
            
        collection = chroma_client.get_collection(query.collection_name)
        
        # Get embedding for query
        query_embedding = await get_embeddings([query.query_text])
        
        # Query ChromaDB
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=query.n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Filter by similarity threshold
        filtered_results = {
            "documents": [],
            "metadatas": [],
            "distances": [],
            "ids": []
        }
        
        if results["distances"] and results["distances"][0]:
            for i, distance in enumerate(results["distances"][0]):
                similarity = 1 - distance  # Convert distance to similarity
                if similarity >= query.similarity_threshold:
                    filtered_results["documents"].append(results["documents"][0][i])
                    filtered_results["metadatas"].append(results["metadatas"][0][i] if query.include_metadata else {})
                    filtered_results["distances"].append(distance)
                    filtered_results["ids"].append(results["ids"][0][i])
        
        return {
            "results": filtered_results["documents"],
            "metadatas": filtered_results["metadatas"],
            "similarities": [1 - d for d in filtered_results["distances"]],
            "ids": filtered_results["ids"],
            "total_found": len(filtered_results["documents"])
        }
        
    except Exception as e:
        logger.error(f"Error querying vectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag-query")
async def rag_query(query: RAGQueryModel):
    """Advanced RAG query with context building and reranking"""
    try:
        if not chroma_client:
            raise HTTPException(status_code=503, detail="ChromaDB not available")
            
        # Step 1: Get initial results
        collection = chroma_client.get_collection(query.collection_name)
        query_embedding = await get_embeddings([query.question])
        
        # Get more results for reranking
        initial_results = collection.query(
            query_embeddings=query_embedding,
            n_results=query.n_results * 2,  # Get more for reranking
            include=["documents", "metadatas", "distances"]
        )
        
        if not initial_results["documents"] or not initial_results["documents"][0]:
            return {
                "context": [],
                "sources": [],
                "total_found": 0,
                "confidence_score": 0.0
            }
        
        # Step 2: Build context with relevance scoring
        context_items = []
        for i, (doc, metadata, distance) in enumerate(zip(
            initial_results["documents"][0],
            initial_results["metadatas"][0],
            initial_results["distances"][0]
        )):
            similarity = 1 - distance
            context_items.append({
                "text": doc,
                "metadata": metadata,
                "similarity": similarity,
                "rank": i
            })
        
        # Step 3: Rerank if requested
        if query.rerank:
            # Simple reranking based on keyword overlap and recency
            context_items = await rerank_results(query.question, context_items)
        
        # Step 4: Select top results
        top_results = context_items[:query.n_results]
        
        # Step 5: Build final context
        context_texts = [item["text"] for item in top_results]
        sources = [{
            "text": item["text"][:200] + "..." if len(item["text"]) > 200 else item["text"],
            "metadata": item["metadata"],
            "similarity": item["similarity"]
        } for item in top_results]
        
        # Calculate overall confidence
        avg_similarity = sum(item["similarity"] for item in top_results) / len(top_results) if top_results else 0
        
        return {
            "context": context_texts,
            "sources": sources,
            "total_found": len(context_texts),
            "confidence_score": avg_similarity,
            "query_embedding_generated": True
        }
        
    except Exception as e:
        logger.error(f"Error in RAG query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def rerank_results(question: str, context_items: List[Dict]) -> List[Dict]:
    """Rerank results based on relevance and recency"""
    try:
        question_lower = question.lower()
        question_words = set(question_lower.split())
        
        for item in context_items:
            text_lower = item["text"].lower()
            text_words = set(text_lower.split())
            
            # Keyword overlap score
            overlap = len(question_words.intersection(text_words))
            keyword_score = overlap / len(question_words) if question_words else 0
            
            # Recency score (if timestamp available)
            recency_score = 0.5  # Default
            if "timestamp" in item["metadata"]:
                # Add recency scoring logic here
                pass
            
            # Combined score
            item["rerank_score"] = (
                item["similarity"] * 0.6 +
                keyword_score * 0.3 +
                recency_score * 0.1
            )
        
        # Sort by rerank score
        context_items.sort(key=lambda x: x["rerank_score"], reverse=True)
        return context_items
        
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        return context_items  # Return original order if reranking fails

@app.get("/collections")
async def list_collections():
    """List all available collections"""
    try:
        if not chroma_client:
            raise HTTPException(status_code=503, detail="ChromaDB not available")
            
        collections = chroma_client.list_collections()
        
        collection_info = []
        for col in collections:
            try:
                count = col.count()
                collection_info.append({
                    "name": col.name,
                    "metadata": col.metadata,
                    "count": count
                })
            except:
                collection_info.append({
                    "name": col.name,
                    "metadata": col.metadata,
                    "count": 0
                })
        
        return {"collections": collection_info}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Delete a collection"""
    try:
        if not chroma_client:
            raise HTTPException(status_code=503, detail="ChromaDB not available")
            
        chroma_client.delete_collection(collection_name)
        return {"status": "deleted", "collection": collection_name}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)