"""Streamlit dashboard for the crypto knowledge system."""

import os
import streamlit as st

# Suppress ChromaDB telemetry warnings
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Page configuration MUST be first
st.set_page_config(
    page_title="Crypto Knowledge AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time

# Import our modules
import sys
import os
from pathlib import Path

# Ensure proper path setup
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from data_ingestion.fetch_prices import CoinGeckoFetcher
from knowledge.fact_extractor import CryptoFactExtractor
from utils.config import Config
from utils.logger import logger

# Try to import LangChain generator, fallback to original if not available
USING_LANGCHAIN = False
CryptoVectorStore = None
CryptoAnswerGenerator = None

try:
    from knowledge.embed_store import CryptoVectorStore
    from rag_pipeline.langchain_generator import LangChainCryptoGenerator as CryptoAnswerGenerator
    USING_LANGCHAIN = True
except ImportError:
    try:
        from knowledge.embed_store_simple import SimpleCryptoVectorStore as CryptoVectorStore
        # Create a dummy generator for now
        class DummyGenerator:
            def generate_answer(self, query, use_rag=True):
                return type('obj', (object,), {
                    'answer': 'LangChain generator not available. Please install langchain-groq.',
                    'retrieval_result': type('obj', (object,), {'facts': []})(),
                    'generation_time': 0.0
                })()
            def compare_answers(self, query):
                return {
                    'rag_answer': {'answer': 'Not available', 'context_facts': 0, 'generation_time': 0},
                    'no_rag_answer': {'answer': 'Not available', 'generation_time': 0},
                    'performance': {'rag_total_time': 0, 'no_rag_total_time': 0, 'facts_retrieved': 0}
                }
        CryptoAnswerGenerator = DummyGenerator
        USING_LANGCHAIN = False
    except ImportError:
        st.error("❌ Could not import required modules. Please run: pip install -r requirements.txt")
        st.stop()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .ai-message {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_crypto_data():
    """Load fresh cryptocurrency data."""
    fetcher = CoinGeckoFetcher()
    return fetcher.fetch_top_cryptocurrencies()


@st.cache_resource
def initialize_components():
    """Initialize system components."""
    vector_store = CryptoVectorStore()
    generator = CryptoAnswerGenerator()
    return vector_store, generator


def update_knowledge_base():
    """Update the knowledge base with fresh data."""
    with st.spinner("Fetching latest crypto data..."):
        # Fetch data
        fetcher = CoinGeckoFetcher()
        crypto_data = fetcher.fetch_top_cryptocurrencies()
        
        if not crypto_data:
            st.error("Failed to fetch cryptocurrency data")
            return False
        
        # Extract facts
        extractor = CryptoFactExtractor()
        facts = extractor.extract_facts(crypto_data)
        
        # Store in vector database
        vector_store, _ = initialize_components()
        vector_store.add_facts(facts)
        
        st.success(f"✅ Updated knowledge base with {len(facts)} new facts from {len(crypto_data)} cryptocurrencies")
        return True


def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<h1 class="main-header">🚀 AI-Powered Crypto Knowledge System</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🛠️ System Controls")
        
        # Show system status
        if USING_LANGCHAIN:
            st.success("🔗 Using LangChain + Groq")
        else:
            st.info("🔧 Using Simple Mode")
        
        # Update knowledge base
        if st.button("🔄 Update Knowledge Base", type="primary"):
            update_knowledge_base()
            st.rerun()
        
        # System stats
        st.header("📊 System Stats")
        try:
            vector_store, _ = initialize_components()
            stats = vector_store.get_collection_stats()
            
            st.metric("Total Facts", stats.get("total_facts", 0))
            st.metric("Cryptocurrencies", stats.get("unique_cryptos", 0))
            
            if stats.get("crypto_symbols"):
                st.write("**Tracked Cryptos:**")
                st.write(", ".join(stats["crypto_symbols"][:10]))
                
        except Exception as e:
            st.error(f"Error loading stats: {e}")
        
        # Configuration
        st.header("⚙️ Settings")
        max_results = st.slider("Max Search Results", 1, 10, 5)
        use_rag = st.checkbox("Use RAG (Recommended)", value=True)
    
    # Chat input (must be outside tabs)
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Chat input at the top level
    if prompt := st.chat_input("💬 Ask about cryptocurrency prices, trends, or market data..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Generate AI response
        try:
            _, generator = initialize_components()
            result = generator.generate_answer(prompt, use_rag=use_rag)
            
            # Store message with metadata
            st.session_state.messages.append({
                "role": "assistant",
                "content": result.answer,
                "metadata": {
                    "facts_used": len(result.retrieval_result.facts),
                    "generation_time": f"{result.generation_time:.2f}s",
                    "retrieval_time": f"{result.retrieval_result.retrieval_time:.2f}s",
                    "context": result.context_used
                }
            })
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        # Rerun to show new messages
        st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["💬 AI Chat", "📈 Live Data", "🔍 Knowledge Explorer", "📊 Evaluation"])
    
    with tab1:
        st.header("💬 Chat History")
        
        # Display chat history
        if st.session_state.messages:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if message["role"] == "assistant" and "metadata" in message:
                        with st.expander("📋 View Context & Details"):
                            st.json(message["metadata"])
        else:
            st.info("👋 Start a conversation by typing in the chat box below!")
            st.markdown("**Try asking:**")
            st.markdown("- What is Bitcoin's current price?")
            st.markdown("- Which cryptocurrency has the highest market cap?")
            st.markdown("- How has Ethereum performed today?")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    
    with tab2:
        st.header("📈 Live Cryptocurrency Data")
        
        # Load and display data
        crypto_data = load_crypto_data()
        
        if crypto_data:
            # Convert to DataFrame
            df_data = []
            for crypto in crypto_data:
                df_data.append({
                    "Name": crypto.name,
                    "Symbol": crypto.symbol,
                    "Price (USD)": crypto.current_price,
                    "24h Change (%)": crypto.price_change_percentage_24h,
                    "Market Cap": crypto.market_cap,
                    "Volume (24h)": crypto.volume_24h,
                    "Rank": crypto.market_cap_rank
                })
            
            df = pd.DataFrame(df_data)
            
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Market Cap", f"${df['Market Cap'].sum()/1e9:.1f}B")
            
            with col2:
                avg_change = df['24h Change (%)'].mean()
                st.metric("Avg 24h Change", f"{avg_change:+.2f}%")
            
            with col3:
                st.metric("Total Volume", f"${df['Volume (24h)'].sum()/1e9:.1f}B")
            
            with col4:
                st.metric("Cryptocurrencies", len(df))
            
            # Price chart
            st.subheader("💰 Current Prices")
            fig_prices = px.bar(
                df.head(10), 
                x="Symbol", 
                y="Price (USD)",
                title="Top 10 Cryptocurrency Prices",
                color="24h Change (%)",
                color_continuous_scale="RdYlGn"
            )
            st.plotly_chart(fig_prices, use_container_width=True)
            
            # Change chart
            st.subheader("📊 24h Price Changes")
            fig_changes = px.bar(
                df.head(10),
                x="Symbol",
                y="24h Change (%)",
                title="24h Price Changes (%)",
                color="24h Change (%)",
                color_continuous_scale="RdYlGn"
            )
            st.plotly_chart(fig_changes, use_container_width=True)
            
            # Data table
            st.subheader("📋 Detailed Data")
            st.dataframe(
                df,
                column_config={
                    "Price (USD)": st.column_config.NumberColumn(format="$%.2f"),
                    "24h Change (%)": st.column_config.NumberColumn(format="%.2f%%"),
                    "Market Cap": st.column_config.NumberColumn(format="$%.0f"),
                    "Volume (24h)": st.column_config.NumberColumn(format="$%.0f")
                },
                use_container_width=True
            )
        else:
            st.error("Failed to load cryptocurrency data")
    
    with tab3:
        st.header("🔍 Knowledge Base Explorer")
        
        # Search interface
        search_query = st.text_input("🔍 Search the knowledge base:", placeholder="e.g., Bitcoin price, Ethereum market cap")
        
        if search_query:
            try:
                vector_store, _ = initialize_components()
                results = vector_store.search_facts(search_query, n_results=max_results)
                
                if results:
                    st.success(f"Found {len(results)} relevant facts")
                    
                    for i, result in enumerate(results, 1):
                        with st.expander(f"📄 Fact {i} (Similarity: {result.get('similarity', 0):.3f})"):
                            st.write(result['content'])
                            st.json(result['metadata'])
                else:
                    st.info("No relevant facts found. Try updating the knowledge base or using different keywords.")
                    
            except Exception as e:
                st.error(f"Search error: {e}")
        
        # Knowledge base statistics
        st.subheader("📊 Knowledge Base Statistics")
        try:
            vector_store, _ = initialize_components()
            stats = vector_store.get_collection_stats()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Facts", stats.get("total_facts", 0))
                st.metric("Unique Cryptocurrencies", stats.get("unique_cryptos", 0))
            
            with col2:
                if stats.get("fact_types"):
                    st.write("**Fact Types:**")
                    for fact_type in stats["fact_types"]:
                        st.write(f"• {fact_type}")
                
                if stats.get("crypto_symbols"):
                    st.write("**Tracked Cryptocurrencies:**")
                    st.write(", ".join(stats["crypto_symbols"]))
                    
        except Exception as e:
            st.error(f"Error loading statistics: {e}")
    
    with tab4:
        st.header("📊 RAG vs Non-RAG Evaluation")
        
        # Evaluation interface
        eval_query = st.text_input("🧪 Test Query:", placeholder="Enter a question to compare RAG vs non-RAG answers")
        
        if st.button("🔬 Run Comparison") and eval_query:
            with st.spinner("Generating both answers..."):
                try:
                    _, generator = initialize_components()
                    comparison = generator.compare_answers(eval_query)
                    
                    # Display results side by side
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🤖 RAG-Enhanced Answer")
                        st.write(comparison["rag_answer"]["answer"])
                        
                        st.metric("Facts Used", comparison["rag_answer"]["context_facts"])
                        st.metric("Generation Time", f"{comparison['rag_answer']['generation_time']:.2f}s")
                        st.metric("Total Time", f"{comparison['performance']['rag_total_time']:.2f}s")
                    
                    with col2:
                        st.subheader("🧠 Standard LLM Answer")
                        st.write(comparison["no_rag_answer"]["answer"])
                        
                        st.metric("Facts Used", "0 (No RAG)")
                        st.metric("Generation Time", f"{comparison['no_rag_answer']['generation_time']:.2f}s")
                        st.metric("Total Time", f"{comparison['performance']['no_rag_total_time']:.2f}s")
                    
                    # Performance comparison
                    st.subheader("⚡ Performance Comparison")
                    perf_data = {
                        "Method": ["RAG-Enhanced", "Standard LLM"],
                        "Total Time (s)": [
                            comparison['performance']['rag_total_time'],
                            comparison['performance']['no_rag_total_time']
                        ],
                        "Facts Used": [
                            comparison['performance']['facts_retrieved'],
                            0
                        ]
                    }
                    
                    perf_df = pd.DataFrame(perf_data)
                    
                    fig_perf = px.bar(
                        perf_df,
                        x="Method",
                        y="Total Time (s)",
                        title="Response Time Comparison",
                        color="Facts Used",
                        text="Total Time (s)"
                    )
                    st.plotly_chart(fig_perf, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Evaluation error: {e}")
        
        # Sample evaluation queries
        st.subheader("💡 Sample Evaluation Queries")
        sample_queries = [
            "What is Bitcoin's current price?",
            "Which cryptocurrency has the highest market cap?",
            "How much has Ethereum changed in the last 24 hours?",
            "Compare the trading volumes of the top 3 cryptocurrencies"
        ]
        
        for query in sample_queries:
            if st.button(f"Test: {query}", key=f"sample_{hash(query)}"):
                st.rerun()


if __name__ == "__main__":
    # Check configuration
    if not Config.validate():
        st.error("⚠️ Configuration incomplete. Please set GROQ_API_KEY in your .env file.")
        st.stop()
    
    main()