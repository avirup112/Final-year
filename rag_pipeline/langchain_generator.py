"""LangChain-based answer generation for crypto queries."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from rag_pipeline.retriever import CryptoRetriever, RetrievalResult
from utils.config import Config
from utils.logger import logger


@dataclass
class GenerationResult:
    """Result from answer generation."""
    query: str
    answer: str
    context_used: str
    retrieval_result: RetrievalResult
    generation_time: float
    model_used: str


class LangChainCryptoGenerator:
    """LangChain-based crypto answer generator with RAG."""
    
    def __init__(self, retriever: CryptoRetriever = None):
        if retriever is None:
            from rag_pipeline.retriever import CryptoRetriever
            self.retriever = CryptoRetriever()
        else:
            self.retriever = retriever
        self.model_name = Config.LLM_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
        
        # Initialize LangChain Groq LLM
        self._initialize_llm()
        
        # Setup prompts
        self._setup_prompts()
        
        logger.info(f"LangChain generator initialized with model: {self.model_name}")
    
    def _initialize_llm(self):
        """Initialize the LangChain Groq LLM."""
        try:
            self.llm = ChatGroq(
                groq_api_key=Config.GROQ_API_KEY,
                model_name=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            logger.info("LangChain Groq LLM initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangChain Groq LLM: {e}")
            raise
    
    def _setup_prompts(self):
        """Setup LangChain prompt templates."""
        
        # RAG prompt template
        self.rag_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a knowledgeable cryptocurrency analyst. Use the provided context to answer questions about cryptocurrencies accurately and concisely.

Guidelines:
- Answer ANY cryptocurrency question using the provided context
- If context is limited, clearly state what information you have vs. don't have
- Include specific numbers, percentages, and timeframes when available
- For price questions: provide current price and recent changes
- For performance questions: focus on percentage changes and trends
- For comparison questions: use available data to make fair comparisons
- For general questions: provide comprehensive overview using available facts
- Always mention the timeframe of your data
- If asked about a crypto not in context, acknowledge the limitation but provide what you can"""),
        ("human", """Context:
{context}

Question: {query}

Please provide a comprehensive answer using the context above. If the context doesn't fully address the question, explain what information you have and what might be missing.""")
    ])
        
        # Non-RAG prompt template
        self.no_rag_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a cryptocurrency analyst. Answer questions about cryptocurrencies based on your general knowledge. 

Important: You should clearly state that your information might not be current and recommend checking live data sources for the most up-to-date information."""),
            ("human", "Question: {query}")
        ])
        
        # Create chains
        self.rag_chain = self.rag_prompt | self.llm | StrOutputParser()
        self.no_rag_chain = self.no_rag_prompt | self.llm | StrOutputParser()
    
    def generate_answer(self, query: str, use_rag: bool = True) -> GenerationResult:
        """Generate answer to crypto query with or without RAG."""
        start_time = time.time()
        
        if use_rag:
            # Retrieve relevant facts
            retrieval_result = self.retriever.retrieve_facts(query)
            context = self.retriever.get_context_string(retrieval_result)
            
            # Generate RAG-enhanced answer
            answer = self._generate_with_context(query, context)
        else:
            # Generate answer without context
            retrieval_result = RetrievalResult(query, [], 0, 0.0)
            context = "No context provided."
            answer = self._generate_without_context(query)
        
        generation_time = time.time() - start_time
        
        return GenerationResult(
            query=query,
            answer=answer,
            context_used=context,
            retrieval_result=retrieval_result,
            generation_time=generation_time,
            model_used=self.model_name
        )
    
    def _generate_with_context(self, query: str, context: str) -> str:
        """Generate answer using retrieved context with LangChain."""
        try:
            response = self.rag_chain.invoke({
                "context": context,
                "query": query
            })
            return response
            
        except Exception as e:
            logger.error(f"Error generating answer with context: {e}")
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"
    
    def _generate_without_context(self, query: str) -> str:
        """Generate answer without retrieved context using LangChain."""
        try:
            response = self.no_rag_chain.invoke({"query": query})
            return response
            
        except Exception as e:
            logger.error(f"Error generating answer without context: {e}")
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"
    
    def compare_answers(self, query: str) -> Dict[str, Any]:
        """Compare answers with and without RAG."""
        logger.info(f"Comparing RAG vs non-RAG answers for: {query}")
        
        # Generate both versions
        rag_result = self.generate_answer(query, use_rag=True)
        no_rag_result = self.generate_answer(query, use_rag=False)
        
        return {
            "query": query,
            "rag_answer": {
                "answer": rag_result.answer,
                "context_facts": len(rag_result.retrieval_result.facts),
                "generation_time": rag_result.generation_time,
                "retrieval_time": rag_result.retrieval_result.retrieval_time
            },
            "no_rag_answer": {
                "answer": no_rag_result.answer,
                "generation_time": no_rag_result.generation_time
            },
            "performance": {
                "rag_total_time": rag_result.generation_time + rag_result.retrieval_result.retrieval_time,
                "no_rag_total_time": no_rag_result.generation_time,
                "facts_retrieved": len(rag_result.retrieval_result.facts)
            }
        }
    
    def batch_generate(self, queries: List[str], use_rag: bool = True) -> List[GenerationResult]:
        """Generate answers for multiple queries efficiently."""
        results = []
        
        for query in queries:
            try:
                result = self.generate_answer(query, use_rag=use_rag)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                continue
        
        return results
    
    def test_connection(self) -> bool:
        """Test LangChain Groq connection."""
        try:
            test_message = HumanMessage(content="Say 'LangChain connection successful' in exactly those words.")
            test_response = self.llm.invoke([test_message])
            
            response_text = test_response.content.strip()
            return "LangChain connection successful" in response_text
            
        except Exception as e:
            logger.error(f"LangChain connection test failed: {e}")
            return False


def main():
    """Test the LangChain answer generation functionality."""
    if not Config.GROQ_API_KEY:
        print("❌ Groq API key not configured. Please set GROQ_API_KEY in .env file")
        return
    
    print("🤖 Testing LangChain Answer Generation")
    print("=" * 50)
    
    try:
        # Initialize generator
        generator = LangChainCryptoGenerator()
        
        # Test connection
        print("🔄 Testing LangChain connection...")
        if generator.test_connection():
            print("✅ LangChain connection successful!")
        else:
            print("❌ LangChain connection failed")
            return
        
        # Test queries
        test_queries = [
            "What is the current price of Bitcoin?",
            "Which cryptocurrency has performed best in the last 24 hours?",
            "Compare Ethereum and Bitcoin market caps"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n❓ Query {i}: {query}")
            print("-" * 40)
            
            # Generate RAG answer
            result = generator.generate_answer(query, use_rag=True)
            
            print(f"🎯 Answer: {result.answer}")
            print(f"📊 Facts used: {len(result.retrieval_result.facts)}")
            print(f"⏱️  Time: {result.generation_time:.2f}s")
        
        # Test comparison
        print(f"\n🔬 Testing RAG vs Non-RAG comparison...")
        comparison = generator.compare_answers("What is Bitcoin's current price?")
        
        print(f"RAG Time: {comparison['performance']['rag_total_time']:.2f}s")
        print(f"Non-RAG Time: {comparison['performance']['no_rag_total_time']:.2f}s")
        print(f"Facts Retrieved: {comparison['performance']['facts_retrieved']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()