from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import os
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Generator Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
VECTOR_RETRIEVAL_URL = os.getenv("VECTOR_RETRIEVAL_SERVICE_URL", "http://vector-retrieval-service:8005")

class QueryRequest(BaseModel):
    question: str
    context: Optional[List[str]] = None
    max_tokens: int = 1000
    temperature: float = 0.3
    model: str = "mixtral-8x7b-32768"

class GeneratedResponse(BaseModel):
    answer: str
    confidence_score: float
    sources_used: List[Dict[str, Any]]
    hallucination_check: Dict[str, Any]
    metadata: Dict[str, Any]

class HallucinationCheck(BaseModel):
    is_hallucinated: bool
    confidence: float
    issues: List[str]
    corrected_answer: Optional[str] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        groq_available = bool(GROQ_API_KEY)
        
        return {
            "status": "healthy",
            "service": "llm-generator-service",
            "groq_configured": groq_available,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

async def call_groq_api(messages: List[Dict], model: str = "mixtral-8x7b-32768", max_tokens: int = 1000, temperature: float = 0.3) -> str:
    """Call Groq API for text generation"""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Groq API key not configured")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
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

async def get_relevant_context(question: str, n_results: int = 5) -> Dict[str, Any]:
    """Get relevant context from vector retrieval service"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{VECTOR_RETRIEVAL_URL}/rag-query",
                json={
                    "question": question,
                    "n_results": n_results,
                    "collection_name": "crypto_facts"
                }
            )
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"Failed to get context from vector service: {e}")
        return {"context": [], "sources": [], "confidence_score": 0.0}

def create_system_prompt() -> str:
    """Create system prompt for crypto knowledge assistant"""
    return """You are a knowledgeable cryptocurrency expert and financial analyst. Your role is to:

1. Provide accurate, up-to-date information about cryptocurrencies
2. Explain complex crypto concepts in simple terms
3. Analyze market trends and price movements
4. Offer insights based on factual data
5. Always cite your sources when possible

Guidelines:
- Be precise and factual
- Avoid speculation unless clearly marked as such
- Use the provided context to inform your answers
- If you're unsure about something, say so
- Focus on educational and informative responses
- Include relevant numbers, dates, and specific details when available

Remember: Only provide information that can be supported by the context provided or well-established crypto knowledge."""

def create_rag_prompt(question: str, context: List[str]) -> List[Dict[str, str]]:
    """Create RAG prompt with context"""
    context_text = "\n\n".join([f"Context {i+1}: {ctx}" for i, ctx in enumerate(context)])
    
    user_prompt = f"""Based on the following context about cryptocurrency, please answer the question.

Context Information:
{context_text}

Question: {question}

Please provide a comprehensive answer based on the context provided. If the context doesn't contain enough information to fully answer the question, please indicate what information is missing."""

    return [
        {"role": "system", "content": create_system_prompt()},
        {"role": "user", "content": user_prompt}
    ]

async def check_hallucination(answer: str, context: List[str], question: str) -> HallucinationCheck:
    """Check for hallucinations in the generated answer"""
    try:
        hallucination_prompt = f"""
Analyze the following answer for potential hallucinations or inaccuracies:

Question: {question}

Answer: {answer}

Available Context:
{chr(10).join(context)}

Please evaluate:
1. Are there any claims in the answer not supported by the context?
2. Are there any factual inaccuracies?
3. Are there any made-up statistics or dates?
4. Is the answer consistent with the provided context?

Respond in JSON format:
{{
    "is_hallucinated": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of specific issues found"],
    "corrected_answer": "corrected version if needed, or null"
}}
"""

        messages = [
            {"role": "system", "content": "You are a fact-checker specializing in cryptocurrency information. Be thorough and critical."},
            {"role": "user", "content": hallucination_prompt}
        ]
        
        hallucination_response = await call_groq_api(messages, temperature=0.1)
        
        try:
            hallucination_data = json.loads(hallucination_response)
            return HallucinationCheck(**hallucination_data)
        except json.JSONDecodeError:
            # Fallback analysis
            return HallucinationCheck(
                is_hallucinated=False,
                confidence=0.5,
                issues=["Could not parse hallucination check response"],
                corrected_answer=None
            )
            
    except Exception as e:
        logger.error(f"Hallucination check failed: {e}")
        return HallucinationCheck(
            is_hallucinated=False,
            confidence=0.0,
            issues=[f"Hallucination check error: {str(e)}"],
            corrected_answer=None
        )

def calculate_confidence_score(context_confidence: float, hallucination_check: HallucinationCheck) -> float:
    """Calculate overall confidence score"""
    base_confidence = context_confidence
    
    if hallucination_check.is_hallucinated:
        # Reduce confidence if hallucinations detected
        hallucination_penalty = 0.3 * hallucination_check.confidence
        base_confidence = max(0.1, base_confidence - hallucination_penalty)
    
    # Boost confidence if hallucination check passed with high confidence
    if not hallucination_check.is_hallucinated and hallucination_check.confidence > 0.8:
        base_confidence = min(1.0, base_confidence + 0.1)
    
    return round(base_confidence, 2)

@app.post("/generate", response_model=GeneratedResponse)
async def generate_answer(request: QueryRequest):
    """Generate answer using RAG + LLM with hallucination checking"""
    try:
        # Get context if not provided
        if not request.context:
            logger.info(f"Getting context for question: {request.question}")
            context_data = await get_relevant_context(request.question)
            context = context_data.get("context", [])
            sources = context_data.get("sources", [])
            context_confidence = context_data.get("confidence_score", 0.0)
        else:
            context = request.context
            sources = []
            context_confidence = 0.8  # Assume good confidence for provided context
        
        if not context:
            # No context available, provide general response
            messages = [
                {"role": "system", "content": create_system_prompt()},
                {"role": "user", "content": f"Question: {request.question}\n\nNote: No specific context available. Please provide a general answer based on your crypto knowledge, but clearly indicate this is general information."}
            ]
            context_confidence = 0.3
        else:
            # Create RAG prompt with context
            messages = create_rag_prompt(request.question, context)
        
        # Generate answer
        logger.info("Generating answer with Groq LLM")
        answer = await call_groq_api(
            messages, 
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Check for hallucinations
        logger.info("Performing hallucination check")
        hallucination_check = await check_hallucination(answer, context, request.question)
        
        # Calculate final confidence score
        final_confidence = calculate_confidence_score(context_confidence, hallucination_check)
        
        # Use corrected answer if available
        final_answer = hallucination_check.corrected_answer or answer
        
        response = GeneratedResponse(
            answer=final_answer,
            confidence_score=final_confidence,
            sources_used=sources,
            hallucination_check=hallucination_check.dict(),
            metadata={
                "model_used": request.model,
                "context_items": len(context),
                "generation_timestamp": datetime.utcnow().isoformat(),
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
        )
        
        logger.info(f"Generated answer with confidence {final_confidence}")
        return response
        
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simple-generate")
async def simple_generate(question: str, max_tokens: int = 500):
    """Simple text generation without RAG"""
    try:
        messages = [
            {"role": "system", "content": create_system_prompt()},
            {"role": "user", "content": question}
        ]
        
        answer = await call_groq_api(messages, max_tokens=max_tokens, temperature=0.3)
        
        return {
            "answer": answer,
            "timestamp": datetime.utcnow(),
            "model": "mixtral-8x7b-32768"
        }
        
    except Exception as e:
        logger.error(f"Simple generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_available_models():
    """List available Groq models"""
    return {
        "available_models": [
            "mixtral-8x7b-32768",
            "llama2-70b-4096",
            "gemma-7b-it"
        ],
        "default_model": "mixtral-8x7b-32768",
        "recommended_for_crypto": "mixtral-8x7b-32768"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)