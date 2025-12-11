"""Retrieval component for the RAG pipeline."""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

try:
    from knowledge.embed_store import CryptoVectorStore
except ImportError:
    # Fallback to simple vector store if sentence-transformers is not available
    from knowledge.embed_store_simple import SimpleCryptoVectorStore as CryptoVectorStore

from utils.logger import logger


@dataclass
class RetrievalResult:
    """Result from fact retrieval."""
    query: str
    facts: List[Dict[str, Any]]
    total_found: int
    retrieval_time: float


@dataclass
class QueryAnalysis:
    """Analysis of user query for dynamic retrieval."""
    crypto_symbols: List[str]
    crypto_names: List[str]
    query_type: str  # price, performance, comparison, general
    time_context: str  # today, 24h, recent, etc.
    intent_keywords: List[str]
    is_comparison: bool
    confidence: float


class CryptoRetriever:
    """Handles dynamic fact retrieval for any crypto queries."""

    def __init__(self, vector_store: CryptoVectorStore = None):
        self.vector_store = vector_store or CryptoVectorStore()
        
        # Comprehensive crypto mapping (expandable)
        self.crypto_mapping = {
            # Major cryptocurrencies
            'bitcoin': 'BTC', 'btc': 'BTC',
            'ethereum': 'ETH', 'eth': 'ETH', 'ether': 'ETH',
            'cardano': 'ADA', 'ada': 'ADA',
            'solana': 'SOL', 'sol': 'SOL',
            'polkadot': 'DOT', 'dot': 'DOT',
            'chainlink': 'LINK', 'link': 'LINK',
            'polygon': 'MATIC', 'matic': 'MATIC',
            'avalanche': 'AVAX', 'avax': 'AVAX',
            'binance': 'BNB', 'bnb': 'BNB',
            'ripple': 'XRP', 'xrp': 'XRP',
            'dogecoin': 'DOGE', 'doge': 'DOGE',
            'shiba': 'SHIB', 'shib': 'SHIB',
            'litecoin': 'LTC', 'ltc': 'LTC',
            'cosmos': 'ATOM', 'atom': 'ATOM',
            'near': 'NEAR', 'algorand': 'ALGO', 'algo': 'ALGO',
            'fantom': 'FTM', 'ftm': 'FTM',
            'terra': 'LUNA', 'luna': 'LUNA',
            'uniswap': 'UNI', 'uni': 'UNI',
            'aave': 'AAVE', 'compound': 'COMP',
            'maker': 'MKR', 'mkr': 'MKR',
            'sushi': 'SUSHI', 'pancake': 'CAKE',
            'tron': 'TRX', 'trx': 'TRX',
            'stellar': 'XLM', 'xlm': 'XLM',
            'monero': 'XMR', 'xmr': 'XMR',
            'eos': 'EOS', 'iota': 'MIOTA',
            'vechain': 'VET', 'vet': 'VET',
            'theta': 'THETA', 'filecoin': 'FIL',
            'decentraland': 'MANA', 'mana': 'MANA',
            'sandbox': 'SAND', 'sand': 'SAND',
            'axie': 'AXS', 'axs': 'AXS'
        }
        
        # Query type patterns for dynamic analysis
        self.query_patterns = {
            'price': [
                r'\b(price|cost|value|worth|trading|priced)\b',
                r'\$|\busd\b|\bdollar\b',
                r'\bhow much\b|\bwhat.*cost\b'
            ],
            'performance': [
                r'\b(perform|change|gain|loss|up|down|increase|decrease)\b',
                r'\b(today|24h|hour|day|week|month|recently)\b',
                r'\b(better|worse|best|worst)\b'
            ],
            'comparison': [
                r'\b(vs|versus|compare|between|against)\b',
                r'\b(better|higher|lower|more|less)\b',
                r'\b(which|what.*best|top)\b'
            ],
            'market_data': [
                r'\b(market cap|capitalization|volume|rank|ranking)\b',
                r'\b(supply|circulation|total)\b'
            ],
            'general': [
                r'\b(tell me|about|information|details)\b',
                r'\b(what is|explain|describe)\b'
            ]
        }
        
        logger.info("Dynamic crypto retriever initialized")

    def analyze_query(self, query: str) -> QueryAnalysis:
        """Dynamically analyze any cryptocurrency query."""
        query_lower = query.lower()
        
        # Extract cryptocurrency mentions
        crypto_symbols = []
        crypto_names = []
        
        for name, symbol in self.crypto_mapping.items():
            if name in query_lower:
                crypto_symbols.append(symbol)
                crypto_names.append(name)
        
        # Remove duplicates while preserving order
        crypto_symbols = list(dict.fromkeys(crypto_symbols))
        crypto_names = list(dict.fromkeys(crypto_names))
        
        # Determine query type
        query_type = 'general'
        intent_keywords = []
        max_matches = 0
        
        for qtype, patterns in self.query_patterns.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    matches += 1
                    intent_keywords.extend(re.findall(pattern, query_lower))
            
            if matches > max_matches:
                max_matches = matches
                query_type = qtype
        
        # Detect time context
        time_context = 'current'
        time_patterns = {
            'today': r'\btoday\b',
            '24h': r'\b(24h|24 hour|day|daily)\b',
            'recent': r'\b(recent|recently|latest|now)\b',
            'week': r'\b(week|weekly)\b',
            'month': r'\b(month|monthly)\b'
        }
        
        for time_key, pattern in time_patterns.items():
            if re.search(pattern, query_lower):
                time_context = time_key
                break
        
        # Detect comparison queries
        is_comparison = bool(re.search(r'\b(vs|versus|compare|between|which.*better|top \d+)\b', query_lower))
        
        # Calculate confidence based on crypto mentions and intent clarity
        confidence = 0.5  # Base confidence
        if crypto_symbols:
            confidence += 0.3  # Boost for specific crypto mentions
        if max_matches > 0:
            confidence += 0.2  # Boost for clear intent
        
        confidence = min(confidence, 1.0)
        
        return QueryAnalysis(
            crypto_symbols=crypto_symbols,
            crypto_names=crypto_names,
            query_type=query_type,
            time_context=time_context,
            intent_keywords=intent_keywords,
            is_comparison=is_comparison,
            confidence=confidence
        )

    def retrieve_facts(self, query: str, max_facts: int = 8, 
                      crypto_filter: Optional[str] = None,
                      relevance_threshold: float = 0.1) -> RetrievalResult:
        """Dynamically retrieve facts based on query analysis."""
        import time
        start_time = time.time()
        
        # Analyze the query for dynamic retrieval
        analysis = self.analyze_query(query)
        
        logger.info(f"Query analysis: {analysis.query_type}, cryptos: {analysis.crypto_symbols}, confidence: {analysis.confidence:.2f}")
        
        # Dynamic search strategy
        all_results = []
        
        # Strategy 1: Search for specific cryptocurrencies mentioned
        if analysis.crypto_symbols:
            for crypto_symbol in analysis.crypto_symbols:
                crypto_results = self.vector_store.search_facts(
                    query=query,
                    n_results=max_facts,
                    crypto_filter=crypto_symbol
                )
                all_results.extend(crypto_results)
        
        # Strategy 2: Use provided crypto_filter if specified
        if crypto_filter and crypto_filter not in analysis.crypto_symbols:
            filter_results = self.vector_store.search_facts(
                query=query,
                n_results=max_facts,
                crypto_filter=crypto_filter
            )
            all_results.extend(filter_results)
        
        # Strategy 3: Broad semantic search
        general_results = self.vector_store.search_facts(
            query=query,
            n_results=max_facts * 2
        )
        all_results.extend(general_results)
        
        # Strategy 4: Search by query type keywords
        if analysis.intent_keywords:
            for keyword in analysis.intent_keywords[:2]:  # Top 2 keywords
                keyword_results = self.vector_store.search_facts(
                    query=f"{keyword} cryptocurrency",
                    n_results=max_facts
                )
                all_results.extend(keyword_results)
        
        # Remove duplicates based on content
        seen_content = set()
        unique_results = []
        for result in all_results:
            content_hash = hash(result['content'][:100])  # Hash first 100 chars
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        # Dynamic relevance scoring
        scored_results = []
        for result in unique_results:
            score = self._calculate_dynamic_relevance(result, analysis, query)
            if score > relevance_threshold:
                result['relevance_score'] = score
                result['similarity'] = score  # For backward compatibility
                scored_results.append(result)
        
        # If no results meet threshold, take top results anyway
        if not scored_results and unique_results:
            logger.warning(f"No facts met threshold {relevance_threshold}, using top results")
            for result in unique_results[:max_facts]:
                result['relevance_score'] = 0.5
                result['similarity'] = 0.5
                scored_results.append(result)
        
        # Sort by relevance score
        scored_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Take top results
        final_results = scored_results[:max_facts]
        
        retrieval_time = time.time() - start_time
        
        logger.info(f"Retrieved {len(final_results)} relevant facts for query: '{query}'")
        
        return RetrievalResult(
            query=query,
            facts=final_results,
            total_found=len(unique_results),
            retrieval_time=retrieval_time
        )

    def _calculate_dynamic_relevance(self, result: Dict, analysis: QueryAnalysis, query: str) -> float:
        """Calculate dynamic relevance score based on query analysis."""
        score = 0.0
        content = result['content'].lower()
        metadata = result.get('metadata', {})
        
        # Base similarity score
        if 'distance' in result and result['distance'] is not None:
            score += max(0, 1 - result['distance']) * 0.4
        else:
            score += 0.3  # Default base score
        
        # Boost for mentioned cryptocurrencies
        crypto_symbol = metadata.get('crypto_symbol', '').upper()
        if crypto_symbol in analysis.crypto_symbols:
            score += 0.3
        
        # Boost for query type matching
        if analysis.query_type == 'price' and any(word in content for word in ['price', 'trading', 'usd', '$']):
            score += 0.2
        elif analysis.query_type == 'performance' and any(word in content for word in ['change', 'increase', 'decrease', '%']):
            score += 0.2
        elif analysis.query_type == 'market_data' and any(word in content for word in ['market cap', 'volume', 'rank']):
            score += 0.2
        elif analysis.query_type == 'comparison' and len(analysis.crypto_symbols) > 1:
            score += 0.15
        
        # Boost for time relevance
        if analysis.time_context in ['today', '24h', 'recent'] and any(word in content for word in ['hour', '24h', 'day']):
            score += 0.1
        
        # Boost for exact query word matches
        query_words = set(query.lower().split())
        content_words = set(content.split())
        word_overlap = len(query_words.intersection(content_words)) / max(len(query_words), 1)
        score += word_overlap * 0.15
        
        return min(score, 1.0)

    def get_context_string(self, retrieval_result: RetrievalResult) -> str:
        """Convert retrieval results to context string for LLM."""
        if not retrieval_result.facts:
            return "I don't have specific information about that cryptocurrency query in my current knowledge base. Let me provide a general response based on my training."
        
        context_parts = []
        context_parts.append(f"Based on the latest cryptocurrency data, here are the relevant facts for your query:")
        
        for i, fact in enumerate(retrieval_result.facts, 1):
            content = fact['content']
            metadata = fact['metadata']
            timestamp = metadata.get('timestamp', 'unknown')
            relevance = fact.get('relevance_score', fact.get('similarity', 0))
            
            context_parts.append(f"{i}. {content}")
            context_parts.append(f"   (Crypto: {metadata.get('crypto_symbol', 'N/A')}, Time: {timestamp[:19]}, Relevance: {relevance:.2f})")
        
        return "\n".join(context_parts)

    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine intent and extract crypto symbols (legacy method)."""
        analysis = self.analyze_query(query)
        
        return {
            'cryptos': analysis.crypto_symbols,
            'intents': [analysis.query_type],
            'is_comparison': analysis.is_comparison,
            'is_general': len(analysis.crypto_symbols) == 0,
            'confidence': analysis.confidence,
            'time_context': analysis.time_context
        }
