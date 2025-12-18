import asyncio
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from shared.models import CryptoFact, QueryRequest, QueryResponse
from shared.utils import setup_logging, make_http_request
from .config import settings
from .hallucination_checker import HallucinationChecker

logger = setup_logging(settings.service_name)

class GroqLLMGenerator:
    """Groq-powered LLM generator with hallucination detection"""
    
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key else None
        self.hallucination_checker = HallucinationChecker()
    
    async def generate_answer(self, query: str, relevant_facts: List[CryptoFact]) -> QueryResponse:
        """Generate answer using Groq LLM with retrieved facts"""
        if not self.groq_client:
            raise Exception("Groq API key not configured")
        
        try:
            # Prepare context from facts
            context = self._prepare_context(relevant_facts)
            
            # Generate answer
            answer = await self._generate_with_groq(query, context)
            
            # Check for hallucinations
            hallucination_detected = False
            if settings.fact_verification_enabled:
                hallucination_detected = await self.hallucination_checker.check_hallucination(
                    answer, relevant_facts
                )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(relevant_facts, hallucination_detected)
            
            # Extract sources
            sources = list(set([f"{fact.source.value}" for fact in relevant_facts]))
            
            return QueryResponse(
                query=query,
                facts=relevant_facts,
                generated_answer=answer,
                confidence_score=confidence_score,
                hallucination_detected=hallucination_detected,
                sources=sources
            )
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            raise
    
    def _prepare_context(self, facts: List[CryptoFact]) -> str:
        """Prepare context string from relevant facts"""
        if not facts:
            return "No relevant information found."
        
        context_parts = []
        for fact in facts:
            context_parts.append(
                f"[{fact.source.value}] {fact.content} (Confidence: {fact.confidence_score:.2f})"
            )
        
        return "\n".join(context_parts)
    
    async def _generate_with_groq(self, query: str, context: str) -> str:
        """Generate answer using Groq API"""
        prompt = f"""
        You are a cryptocurrency expert assistant. Answer the user's question based ONLY on the provided context.
        
        Context (verified facts):
        {context}
        
        User Question: {query}
        
        Instructions:
        1. Answer based ONLY on the provided context
        2. If the context doesn't contain enough information, say so clearly
        3. Include specific data points and sources when available
        4. Be precise and factual
        5. Do not make up or infer information not in the context
        6. If asked about prices, include the timestamp context if available
        
        Answer:
        """
        
        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.groq_temperature,
                max_tokens=settings.groq_max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            raise Exception(f"Failed to generate answer: {str(e)}")
    
    def _calculate_confidence(self, facts: List[CryptoFact], hallucination_detected: bool) -> float:
        """Calculate overall confidence score for the response"""
        if not facts:
            return 0.0
        
        if hallucination_detected:
            return 0.2  # Low confidence if hallucination detected
        
        # Average confidence of source facts
        avg_fact_confidence = sum(fact.confidence_score for fact in facts) / len(facts)
        
        # Adjust based on number of supporting facts
        fact_count_bonus = min(len(facts) * 0.1, 0.3)
        
        # Adjust based on fact freshness (simplified)
        freshness_bonus = 0.1  # Could be more sophisticated
        
        total_confidence = avg_fact_confidence + fact_count_bonus + freshness_bonus
        return min(max(total_confidence, 0.0), 1.0)
    
    async def get_vector_facts(self, query: str, symbols: Optional[List[str]] = None, limit: int = 10) -> List[CryptoFact]:
        """Retrieve relevant facts from vector service"""
        try:
            request_data = {
                "query": query,
                "limit": limit
            }
            
            if symbols:
                request_data["symbols"] = symbols
            
            response = await make_http_request(
                f"{settings.vector_service_url}/search",
                method="POST",
                data=request_data
            )
            
            # Convert response to CryptoFact objects
            facts = []
            for fact_data in response.get("facts", []):
                try:
                    facts.append(CryptoFact(**fact_data))
                except Exception as e:
                    logger.warning(f"Failed to parse fact: {str(e)}")
            
            return facts
            
        except Exception as e:
            logger.error(f"Failed to retrieve vector facts: {str(e)}")
            return []
    
    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """Process a complete query request"""
        try:
            # Get relevant facts from vector database
            relevant_facts = await self.get_vector_facts(
                request.query,
                request.symbols,
                request.limit
            )
            
            # Filter by similarity threshold if specified
            if request.similarity_threshold > 0:
                # This would require similarity scores from vector service
                # For now, we'll use all returned facts
                pass
            
            # Generate answer
            response = await self.generate_answer(request.query, relevant_facts)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            # Return error response
            return QueryResponse(
                query=request.query,
                facts=[],
                generated_answer=f"I apologize, but I encountered an error while processing your query: {str(e)}",
                confidence_score=0.0,
                hallucination_detected=False,
                sources=[]
            )