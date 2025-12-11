"""Simple launcher for the crypto knowledge system."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Suppress ChromaDB telemetry warnings
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

def main():
    """Simple system launcher."""
    print("🚀 AI-Powered Crypto Knowledge System")
    print("=" * 50)
    
    try:
        # Import and test core components
        from utils.config import Config
        from data_ingestion.fetch_prices import CoinGeckoFetcher
        from knowledge.fact_extractor import CryptoFactExtractor
        
        # Try advanced embeddings first, fallback to simple
        try:
            from knowledge.embed_store import CryptoVectorStore
            print("✅ Using advanced embeddings (sentence-transformers)")
        except Exception as e:
            print(f"⚠️  Advanced embeddings failed: {e}")
            print("🔄 Falling back to simple embeddings...")
            from knowledge.embed_store_simple import SimpleCryptoVectorStore as CryptoVectorStore
            print("✅ Using simple embeddings (ChromaDB default)")
        
        from rag_pipeline.langchain_generator import LangChainCryptoGenerator
        
        print("✅ All modules imported successfully")
        
        # Check API key
        if not Config.GROQ_API_KEY:
            print("❌ GROQ_API_KEY not found in .env file")
            print("Please add your API key from https://console.groq.com")
            return
        
        print("✅ Configuration valid")
        
        # Fetch some crypto data
        print("📡 Fetching crypto data...")
        fetcher = CoinGeckoFetcher()
        crypto_data = fetcher.fetch_top_cryptocurrencies(limit=3)
        
        if crypto_data:
            print(f"✅ Fetched {len(crypto_data)} cryptocurrencies")
            
            # Extract facts
            extractor = CryptoFactExtractor()
            facts = extractor.extract_facts(crypto_data)
            
            # Store in vector DB
            vector_store = CryptoVectorStore()
            vector_store.add_facts(facts)
            
            # Test AI generator
            generator = LangChainCryptoGenerator()
            result = generator.generate_answer("What is Bitcoin's current price?")
            
            print("✅ System working! Sample response:")
            print(f"   {result.answer[:100]}...")
            
        print("\n🎉 System ready!")
        print("Launch dashboard: streamlit run ui/app.py")
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()