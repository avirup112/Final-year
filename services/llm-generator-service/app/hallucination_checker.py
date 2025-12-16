import re
from typing import List, Dict, Any
from shared.models import CryptoFact
from shared.utils import setup_logging
from .config import settings

logger = setup_logging(settings.service_name)

class HallucinationChecker:
    """Detects potential hallucinations in LLM responses"""
    
    def __init__(self):
        # Common hallucination patterns
        self.suspicious_patterns = [
            r'\$[\d,]+\.?\d*\s*(billion|million|trillion)',  # Specific large numbers
            r'(will|going to|expected to|predicted to)',     # Future predictions
            r'(according to|sources say|reports indicate)',  # Vague attributions
            r'(breaking|just announced|recently revealed)',  # Urgency without context
        ]
        
        # Confidence thresholds
        self.price_variance_threshold = 0.1  # 10% variance allowed
        self.date_freshness_threshold = 86400  # 24 hours in seconds
    
    async def check_hallucination(self, generated_text: str, source_facts: List[CryptoFact]) -> bool:
        """Check if generated text contains potential hallucinations"""
        try:
            # Pattern-based checks
            if self._check_suspicious_patterns(generated_text):
                logger.warning("Suspicious patterns detected in generated text")
                return True
            
            # Fact consistency checks
            if self._check_fact_consistency(generated_text, source_facts):
                logger.warning("Fact inconsistency detected")
                return True
            
            # Price accuracy checks
            if self._check_price_accuracy(generated_text, source_facts):
                logger.warning("Price inaccuracy detected")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in hallucination check: {str(e)}")
            return True  # Conservative approach - flag as potential hallucination
    
    def _check_suspicious_patterns(self, text: str) -> bool:
        """Check for suspicious patterns that might indicate hallucination"""
        text_lower = text.lower()
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _check_fact_consistency(self, text: str, facts: List[CryptoFact]) -> bool:
        """Check if generated text is consistent with source facts"""
        if not facts:
            return False
        
        text_lower = text.lower()
        
        # Extract symbols mentioned in the text
        mentioned_symbols = set()
        for fact in facts:
            if fact.symbol.lower() in text_lower:
                mentioned_symbols.add(fact.symbol)
        
        # Check if text mentions symbols not in source facts
        fact_symbols = set(fact.symbol for fact in facts)
        
        # Extract potential crypto symbols from text (simplified)
        potential_symbols = re.findall(r'\b[A-Z]{2,5}\b', text)
        crypto_symbols = [s for s in potential_symbols if len(s) <= 5 and s not in ['USD', 'API', 'LLM']]
        
        for symbol in crypto_symbols:
            if symbol not in fact_symbols and symbol not in mentioned_symbols:
                logger.warning(f"Text mentions symbol {symbol} not in source facts")
                return True
        
        return False
    
    def _check_price_accuracy(self, text: str, facts: List[CryptoFact]) -> bool:
        """Check if price information in text matches source facts"""
        # Extract price mentions from text
        price_pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
        price_matches = re.findall(price_pattern, text)
        
        if not price_matches:
            return False
        
        # Get price facts from source
        price_facts = [f for f in facts if f.fact_type.value == 'price']
        
        if not price_facts:
            # Text mentions prices but no price facts available
            return len(price_matches) > 0
        
        # Check if mentioned prices are within reasonable range of source prices
        for price_str in price_matches:
            mentioned_price = float(price_str.replace(',', ''))
            
            # Find closest price fact
            closest_variance = float('inf')
            for fact in price_facts:
                if 'raw_price' in fact.metadata:
                    source_price = float(fact.metadata['raw_price'])
                    variance = abs(mentioned_price - source_price) / source_price
                    closest_variance = min(closest_variance, variance)
            
            # If mentioned price is too different from any source price
            if closest_variance > self.price_variance_threshold:
                logger.warning(f"Price {mentioned_price} differs significantly from source prices")
                return True
        
        return False
    
    def _extract_numerical_claims(self, text: str) -> List[Dict[str, Any]]:
        """Extract numerical claims from text for verification"""
        claims = []
        
        # Price claims
        price_pattern = r'(\w+).*?\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
        for match in re.finditer(price_pattern, text, re.IGNORECASE):
            claims.append({
                'type': 'price',
                'symbol': match.group(1).upper(),
                'value': float(match.group(2).replace(',', '')),
                'text': match.group(0)
            })
        
        # Percentage claims
        percent_pattern = r'(\w+).*?(\d+(?:\.\d+)?)\s*%'
        for match in re.finditer(percent_pattern, text, re.IGNORECASE):
            claims.append({
                'type': 'percentage',
                'symbol': match.group(1).upper(),
                'value': float(match.group(2)),
                'text': match.group(0)
            })
        
        return claims