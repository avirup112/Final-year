import streamlit as st
import httpx
import json
from datetime import datetime
import asyncio
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

# Configuration - All service URLs
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8080")
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:8001")
FACT_EXTRACTION_URL = os.getenv("FACT_EXTRACTION_SERVICE_URL", "http://localhost:8002")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8003")
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://localhost:8004")
VECTOR_RETRIEVAL_URL = os.getenv("VECTOR_RETRIEVAL_SERVICE_URL", "http://localhost:8005")
LLM_GENERATOR_URL = os.getenv("LLM_GENERATOR_SERVICE_URL", "http://localhost:8006")
SELF_HEALING_URL = os.getenv("SELF_HEALING_SERVICE_URL", "http://localhost:8007")
CACHE_SERVICE_URL = os.getenv("CACHE_SERVICE_URL", "http://localhost:8008")
BATCH_PROCESSOR_URL = os.getenv("BATCH_PROCESSOR_URL", "http://localhost:8009")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8010")

# Page configuration
st.set_page_config(
    page_title="Crypto Knowledge System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-healthy {
        color: #28a745;
        font-weight: bold;
    }
    .status-unhealthy {
        color: #dc3545;
        font-weight: bold;
    }
    .sidebar-section {
        margin: 1rem 0;
        padding: 1rem;
        border-left: 3px solid #1f77b4;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

def make_request(url, method="GET", data=None):
    """Make HTTP request with error handling"""
    try:
        with httpx.Client(timeout=10.0) as client:
            if method == "GET":
                response = client.get(url)
            elif method == "POST":
                response = client.post(url, json=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def get_system_health():
    """Get overall system health"""
    return make_request(f"{SELF_HEALING_URL}/system/health")

def get_service_status(service_url):
    """Get individual service status"""
    return make_request(f"{service_url}/health")

def trigger_data_fetch():
    """Trigger manual data fetch"""
    data = {
        "symbols": ["bitcoin", "ethereum", "cardano", "polkadot", "chainlink"],
        "sources": ["coingecko", "coinmarketcap", "news"],
        "force": True
    }
    return make_request(f"{INGESTION_SERVICE_URL}/fetch-now", "POST", data)

def query_knowledge(question):
    """Query the knowledge system using LLM Generator"""
    data = {
        "query": question,
        "use_rag": True,
        "max_tokens": 500
    }
    return make_request(f"{LLM_GENERATOR_URL}/generate", "POST", data)

def search_vectors(question, n_results=5):
    """Search vector database directly"""
    data = {
        "query": question,
        "n_results": n_results,
        "collection_name": "crypto_facts"
    }
    return make_request(f"{VECTOR_RETRIEVAL_URL}/search", "POST", data)

def extract_facts(text):
    """Extract facts from text using fact extraction service"""
    data = {
        "text": text,
        "source": "user_input",
        "extract_entities": True
    }
    return make_request(f"{FACT_EXTRACTION_URL}/extract", "POST", data)

def generate_embeddings(texts):
    """Generate embeddings for texts"""
    data = {
        "texts": texts if isinstance(texts, list) else [texts],
        "normalize": True
    }
    return make_request(f"{EMBEDDING_SERVICE_URL}/embed", "POST", data)

def get_recent_facts():
    """Get recent facts from storage"""
    return make_request(f"{STORAGE_SERVICE_URL}/facts?limit=10")

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🚀 Crypto Knowledge System</h1>', unsafe_allow_html=True)
    st.markdown("**Production-Ready Microservices for Crypto Intelligence**")
    
    # Sidebar
    st.sidebar.markdown('<div class="sidebar-section"><h3>🎛️ Control Panel</h3></div>', unsafe_allow_html=True)
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigate to:",
        ["🏠 Dashboard", "🔍 Knowledge Query", "📊 System Health", "⚙️ Data Management", "📈 Analytics"]
    )
    
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "🔍 Knowledge Query":
        show_knowledge_query()
    elif page == "📊 System Health":
        show_system_health()
    elif page == "⚙️ Data Management":
        show_data_management()
    elif page == "📈 Analytics":
        show_analytics()

def show_dashboard():
    """Show main dashboard"""
    st.header("📊 System Dashboard")
    
    # System metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Get system health
    health_data = get_system_health()
    
    if "error" not in health_data:
        system_metrics = health_data.get("system_metrics", {})
        
        with col1:
            st.metric(
                "Total Services",
                system_metrics.get("total_services", "N/A"),
                delta=None
            )
        
        with col2:
            healthy_services = system_metrics.get("healthy_services", 0)
            total_services = system_metrics.get("total_services", 1)
            health_percentage = (healthy_services / total_services) * 100 if total_services > 0 else 0
            st.metric(
                "System Health",
                f"{health_percentage:.1f}%",
                delta=f"{healthy_services}/{total_services} healthy"
            )
        
        with col3:
            st.metric(
                "Health Score",
                f"{system_metrics.get('overall_health_score', 0):.2f}",
                delta=None
            )
        
        with col4:
            st.metric(
                "Last Updated",
                datetime.now().strftime("%H:%M:%S"),
                delta=None
            )
    
    # Recent activity
    st.subheader("📋 Recent Facts")
    facts_data = get_recent_facts()
    
    if "error" not in facts_data and "facts" in facts_data:
        facts = facts_data["facts"]
        if facts:
            for fact in facts[:5]:  # Show top 5
                with st.expander(f"📄 {fact.get('category', 'Unknown').title()} - {fact.get('source', 'Unknown')}"):
                    st.write(f"**Content:** {fact.get('content', 'No content')}")
                    st.write(f"**Confidence:** {fact.get('confidence_score', 0):.2f}")
                    st.write(f"**Timestamp:** {fact.get('timestamp', 'Unknown')}")
        else:
            st.info("No recent facts available. Try triggering a data fetch.")
    else:
        st.error("Unable to fetch recent facts")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Fetch New Data", type="primary"):
            with st.spinner("Fetching crypto data..."):
                result = trigger_data_fetch()
                if "error" not in result:
                    st.success("✅ Data fetch triggered successfully!")
                else:
                    st.error(f"❌ Error: {result['error']}")
    
    with col2:
        if st.button("🔍 Test Knowledge Query"):
            st.session_state.test_query = True
    
    with col3:
        if st.button("📊 Refresh Dashboard"):
            st.rerun()

def show_knowledge_query():
    """Show knowledge query interface"""
    st.header("🔍 Knowledge Query System")
    st.markdown("Ask questions about cryptocurrency and get intelligent responses from our RAG system.")
    
    # Query input
    question = st.text_input(
        "Enter your crypto question:",
        placeholder="e.g., What is Bitcoin's current market trend?",
        key="knowledge_query"
    )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        search_button = st.button("🔍 Search", type="primary")
    
    with col2:
        n_results = st.slider("Number of results", 1, 10, 5)
    
    if search_button and question:
        with st.spinner("Searching knowledge base..."):
            result = query_knowledge(question)
            
            if "error" not in result:
                st.subheader("📋 Search Results")
                
                # Show confidence score
                confidence = result.get("confidence_score", 0)
                st.metric("Confidence Score", f"{confidence:.2f}")
                
                # Show context
                context = result.get("context", [])
                sources = result.get("sources", [])
                
                if context:
                    for i, (ctx, source) in enumerate(zip(context, sources)):
                        with st.expander(f"Result {i+1} - Similarity: {source.get('similarity', 0):.3f}"):
                            st.write(ctx)
                            st.json(source.get("metadata", {}))
                else:
                    st.warning("No relevant results found for your query.")
            else:
                st.error(f"Query failed: {result['error']}")
    
    # Example queries
    st.subheader("💡 Example Queries")
    examples = [
        "What is Bitcoin?",
        "How does Ethereum smart contracts work?",
        "What are the latest crypto market trends?",
        "Explain DeFi protocols",
        "What is the difference between Bitcoin and Ethereum?"
    ]
    
    for example in examples:
        if st.button(f"📝 {example}", key=f"example_{example}"):
            st.session_state.knowledge_query = example
            st.rerun()

def show_system_health():
    """Show system health monitoring"""
    st.header("📊 System Health Monitoring")
    
    # Overall system health
    health_data = get_system_health()
    
    if "error" not in health_data:
        # System metrics
        st.subheader("🎯 Overall System Status")
        system_metrics = health_data.get("system_metrics", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            healthy = system_metrics.get("healthy_services", 0)
            total = system_metrics.get("total_services", 1)
            st.metric("Healthy Services", f"{healthy}/{total}")
        
        with col2:
            degraded = system_metrics.get("degraded_services", 0)
            st.metric("Degraded Services", degraded)
        
        with col3:
            unhealthy = system_metrics.get("unhealthy_services", 0)
            st.metric("Unhealthy Services", unhealthy)
        
        # Individual service health
        st.subheader("🔧 Individual Service Status")
        service_health = health_data.get("service_health", {})
        
        services = [
            ("Ingestion Service", INGESTION_SERVICE_URL),
            ("Storage Service", STORAGE_SERVICE_URL),
            ("Vector Retrieval", VECTOR_RETRIEVAL_URL),
            ("Self-Healing", SELF_HEALING_URL)
        ]
        
        for service_name, service_url in services:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**{service_name}**")
            
            with col2:
                status = get_service_status(service_url)
                if "error" not in status:
                    st.markdown('<span class="status-healthy">✅ Healthy</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-unhealthy">❌ Unhealthy</span>', unsafe_allow_html=True)
            
            with col3:
                if st.button(f"Test {service_name}", key=f"test_{service_name}"):
                    st.json(status)
        
        # Circuit breakers
        st.subheader("⚡ Circuit Breakers")
        circuit_breakers = health_data.get("circuit_breakers", {})
        
        if circuit_breakers:
            cb_df = pd.DataFrame([
                {
                    "Service": service,
                    "State": cb.get("state", "unknown"),
                    "Failure Count": cb.get("failure_count", 0),
                    "Last Failure": cb.get("last_failure", "Never")
                }
                for service, cb in circuit_breakers.items()
            ])
            st.dataframe(cb_df, use_container_width=True)
    else:
        st.error(f"Unable to fetch system health: {health_data['error']}")

def show_data_management():
    """Show data management interface"""
    st.header("⚙️ Data Management")
    
    # Data ingestion controls
    st.subheader("📥 Data Ingestion")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Manual Data Fetch**")
        symbols = st.multiselect(
            "Select cryptocurrencies:",
            ["bitcoin", "ethereum", "cardano", "polkadot", "chainlink", "solana", "avalanche-2"],
            default=["bitcoin", "ethereum"]
        )
        
        sources = st.multiselect(
            "Select data sources:",
            ["coingecko", "coinmarketcap", "news"],
            default=["coingecko"]
        )
        
        if st.button("🚀 Trigger Fetch"):
            data = {
                "symbols": symbols,
                "sources": sources,
                "force": True
            }
            result = trigger_data_fetch()
            if "error" not in result:
                st.success("✅ Data fetch triggered!")
                st.json(result)
            else:
                st.error(f"❌ Error: {result['error']}")
    
    with col2:
        st.write("**Ingestion Status**")
        status = make_request(f"{INGESTION_SERVICE_URL}/status")
        if "error" not in status:
            st.json(status)
        else:
            st.error("Unable to fetch ingestion status")
    
    # Storage management
    st.subheader("💾 Storage Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Recent Facts**")
        facts_data = get_recent_facts()
        if "error" not in facts_data:
            st.metric("Total Facts", facts_data.get("count", 0))
        
    with col2:
        st.write("**Storage Health**")
        storage_health = get_service_status(STORAGE_SERVICE_URL)
        if "error" not in storage_health:
            st.success("✅ Storage service healthy")
        else:
            st.error("❌ Storage service issues")

def show_analytics():
    """Show analytics and insights"""
    st.header("📈 System Analytics")
    
    # Placeholder for analytics
    st.info("📊 Analytics dashboard coming soon! This will include:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Data Insights:**
        - 📈 Data ingestion trends
        - 🔍 Query patterns analysis
        - 📊 Knowledge base growth
        - ⚡ Response time metrics
        """)
    
    with col2:
        st.markdown("""
        **System Metrics:**
        - 🏥 Service uptime statistics
        - 🔄 Self-healing events
        - 💾 Storage utilization
        - 🚀 Performance benchmarks
        """)
    
    # Sample chart
    st.subheader("📊 Sample Metrics")
    
    # Generate sample data
    dates = pd.date_range(start="2024-01-01", end="2024-01-07", freq="D")
    sample_data = pd.DataFrame({
        "Date": dates,
        "Queries": [45, 52, 38, 67, 73, 81, 59],
        "Data Points": [1200, 1350, 1180, 1420, 1580, 1650, 1480]
    })
    
    fig = px.line(sample_data, x="Date", y=["Queries", "Data Points"], 
                  title="System Activity (Sample Data)")
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()