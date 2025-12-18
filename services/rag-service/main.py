"""
RAG Service - Microservice for Retrieval Augmented Generation
Provides vector storage, semantic search, and LLM-powered answer generation
Port: 8011
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
import os
import time
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables explicitly from root
root_dir = Path(__file__).parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="RAG Service",
    description="Retrieval Augmented Generation Service with ChromaDB and Groq LLM",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class Fact(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = {}

class AddFactsRequest(BaseModel):
    facts: List[Fact]

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class GenerateRequest(BaseModel):
    query: str
    use_rag: bool = True

# Global RAG components
chroma_client = None
collection = None
embedder = None
groq_client = None

@app.on_event("startup")
async def startup_event():
    """Initialize RAG components"""
    global chroma_client, collection, embedder, groq_client
    
    try:
        logger.info("🚀 Starting RAG Service...")
        
        # Initialize ChromaDB
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_or_create_collection(
            name="crypto_facts",
            metadata={"description": "Cryptocurrency facts and market data"}
        )
        logger.info("✅ ChromaDB initialized")
        
        # Initialize embedding model
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Sentence Transformer loaded")
        
        # Initialize Groq LLM
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("⚠️ GROQ_API_KEY not found - LLM features will be limited")
            groq_client = None
        else:
            groq_client = Groq(api_key=api_key)
            logger.info("✅ Groq LLM initialized")
        
        logger.info("🎉 RAG Service ready on port 8011!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "rag-service",
        "port": 8011,
        "chromadb": "connected" if chroma_client else "disconnected",
        "groq": "configured" if groq_client else "not_configured",
        "embedder": "loaded" if embedder else "not_loaded",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/facts/add")
async def add_facts(request: AddFactsRequest):
    """Add facts to vector database"""
    try:
        if not collection or not embedder:
            raise HTTPException(status_code=503, detail="RAG service not initialized")
        
        facts = request.facts
        if not facts:
            return {"status": "success", "added": 0}
        
        embeddings = []
        documents = []
        metadatas = []
        ids = []
        
        for fact in facts:
            # Create embedding
            embedding = embedder.encode(fact.content)
            embeddings.append(embedding.tolist())
            documents.append(fact.content)
            metadatas.append(fact.metadata)
            ids.append(fact.id)
        
        # Add to ChromaDB
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"✅ Added {len(facts)} facts to knowledge base")
        
        return {
            "status": "success",
            "added": len(facts),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to add facts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve")
async def retrieve_facts(request: QueryRequest):
    """Retrieve relevant facts from vector database"""
    try:
        if not collection or not embedder:
            raise HTTPException(status_code=503, detail="RAG service not initialized")
        
        # Create query embedding
        query_embedding = embedder.encode(request.query)
        
        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=request.top_k
        )
        
        # Format results
        retrieved_facts = []
        if results['documents'] and results['documents'][0]:
            retrieved_facts = [
                {
                    "content": doc,
                    "score": 1 - dist,  # Convert distance to similarity
                    "metadata": meta
                }
                for doc, dist, meta in zip(
                    results['documents'][0],
                    results['distances'][0],
                    results['metadatas'][0]
                )
            ]
        
        return {
            "status": "success",
            "facts": retrieved_facts,
            "count": len(retrieved_facts),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate_answer(request: GenerateRequest):
    """Generate answer using RAG or direct LLM"""
    start_time = time.time()
    
    try:
        if not embedder:
            raise HTTPException(status_code=503, detail="RAG service not initialized")
        
        retrieved_facts = []
        context = ""
        
        if request.use_rag:
            # Retrieve relevant context
            query_embedding = embedder.encode(request.query)
            results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=5
            )
            
            if results['documents'] and results['documents'][0]:
                context = "\n".join(results['documents'][0])
                
                # Format retrieved facts
                retrieved_facts = [
                    {
                        "content": doc,
                        "score": 1 - dist,
                        "metadata": meta
                    }
                    for doc, dist, meta in zip(
                        results['documents'][0],
                        results['distances'][0],
                        results['metadatas'][0]
                    )
                ]
        
        # Generate answer with LLM
        if groq_client:
            if request.use_rag and context:
                prompt = f"""You are a cryptocurrency expert assistant. Answer the question using ONLY the provided context. Be concise and accurate.

Context:
{context}

Question: {request.query}

Answer:"""
            else:
                prompt = f"""You are a cryptocurrency expert assistant. Answer the following question concisely and accurately.

Question: {request.query}

Answer:"""
            
            # Call Groq LLM
            model_name = os.getenv("GROQ_MODEL", "llama3-70b-8192")
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
        else:
            # Fallback if no Groq API key
            if request.use_rag and context:
                answer = f"Based on the knowledge base: {context[:300]}..."
            else:
                answer = "Groq API key not configured. Please add GROQ_API_KEY to your .env file."
        
        generation_time = time.time() - start_time
        
        return {
            "status": "success",
            "answer": answer,
            "facts_used": len(retrieved_facts),
            "generation_time": generation_time,
            "retrieved_facts": retrieved_facts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Answer generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get knowledge base statistics"""
    try:
        if not collection:
            return {"total_facts": 0, "unique_coins": 0}
        
        count = collection.count()
        
        # Get unique coins
        unique_coins = 0
        if count > 0:
            all_data = collection.get()
            unique_coins = len(set(
                meta.get('coin', 'unknown') 
                for meta in all_data['metadatas']
            ))
        
        return {
            "status": "success",
            "total_facts": count,
            "unique_coins": unique_coins,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/facts/clear")
async def clear_knowledge_base():
    """Clear all facts from knowledge base"""
    global collection
    
    try:
        if not chroma_client:
            raise HTTPException(status_code=503, detail="RAG service not initialized")
        
        # Delete and recreate collection
        chroma_client.delete_collection("crypto_facts")
        collection = chroma_client.get_or_create_collection(
            name="crypto_facts",
            metadata={"description": "Cryptocurrency facts and market data"}
        )
        
        logger.info("✅ Knowledge base cleared")
        
        return {
            "status": "success",
            "message": "Knowledge base cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to clear knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting RAG Service on port 8011...")
    uvicorn.run(app, host="0.0.0.0", port=8011)
