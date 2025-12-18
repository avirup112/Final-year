import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page Config
st.set_page_config(
    page_title="CryptoAI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    /* Dark Theme Optimization */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Metrics Cards */
    div[data-testid="metric-container"] {
        background-color: #1a1e26;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2d333b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Chat Bubbles */
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
        align-items: flex-start;
    }
    .chat-message.user {
        background-color: #2b313e;
    }
    .chat-message.ai {
        background-color: #1a1e26;
        border: 1px solid #2d333b;
    }
    
    /* Headers */
    h1, h2, h3 {
        background: linear-gradient(90deg, #fff, #ff960b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #ff960b;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 10px 24px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #ffaa33;
        box-shadow: 0 4px 12px rgba(255, 150, 11, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Constants
API_URL = "http://localhost:8000"

def check_backend_health():
    try:
        requests.get(f"{API_URL}/health", timeout=2)
        return True
    except:
        return False

# Sidebar
with st.sidebar:
    st.image("https://cryptologos.cc/logos/bitcoin-btc-logo.png", width=50)
    st.title("CryptoAI")
    
    backend_status = "🟢 Online" if check_backend_health() else "🔴 Offline"
    st.caption(f"Backend Status: {backend_status}")
    
    selected_page = st.radio(
        "Navigation",
        ["💬 AI Chat", "📊 Live Dashboard", "📚 Knowledge Base"]
    )
    
    st.divider()
    st.info("Powered by RAG & Groq LLM")

# --------------------------
# AI CHAT PAGE
# --------------------------
if selected_page == "💬 AI Chat":
    st.header("💬 AI Investment Assistant")
    st.caption("Ask about market trends, coin prices, or technical analysis.")
    
    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm your CryptoAI assistant. How can I help you today?"}
        ]
    
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "metadata" in msg:
                st.caption(f"📚 {msg['metadata']['facts']} facts | ⏱️ {msg['metadata']['time']}s")

    # Chat Input
    if prompt := st.chat_input("What is the current price of Bitcoin?"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Generate Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_URL}/generate_answer",
                        json={"query": prompt, "use_rag": True},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("answer", "No answer generated.")
                        facts_used = data.get("facts_used", 0)
                        gen_time = data.get("generation_time", 0.0)
                        
                        st.markdown(answer)
                        
                        # Show metadata
                        if facts_used > 0:
                            st.caption(f"📚 Used {facts_used} retrieved facts | ⏱️ {gen_time:.2f}s")
                            with st.expander("View Retrieved Facts"):
                                for fact in data.get("retrieved_facts", []):
                                    st.info(f"{fact.get('content', '')}")
                        
                        # Save to history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "metadata": {"facts": facts_used, "time": f"{gen_time:.2f}"}
                        })
                    else:
                        st.error("Failed to get response from AI service.")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")

# --------------------------
# LIVE DASHBOARD PAGE
# --------------------------
elif selected_page == "📊 Live Dashboard":
    st.header("📊 Live Market Data")
    
    if st.button("🔄 Refresh Data"):
        st.rerun()

    try:
        response = requests.get(f"{API_URL}/crypto_data")
        if response.status_code == 200:
            data = response.json()
            if not data:
                st.warning("No data available. Please update knowledge base.")
            else:
                df = pd.DataFrame(data)
                
                # Top Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Coins", len(df))
                with col2:
                    top_coin = df.loc[df['current_price'].idxmax()]
                    st.metric("Top Price", f"${top_coin['current_price']:,.2f}", top_coin['name'])
                with col3:
                    top_gainer = df.loc[df['price_change_percentage_24h'].idxmax()]
                    st.metric("Top Gainer (24h)", f"{top_gainer['price_change_percentage_24h']:.2f}%", top_gainer['name'])
                with col4:
                    top_loser = df.loc[df['price_change_percentage_24h'].idxmin()]
                    st.metric("Top Loser (24h)", f"{top_loser['price_change_percentage_24h']:.2f}%", top_loser['name'])
                
                st.markdown("### 📈 Market Overview")
                
                # Charts
                tab1, tab2 = st.tabs(["Price Distribution", "24h Performance"])
                
                with tab1:
                    fig_price = px.bar(
                        df.nlargest(10, 'current_price'), 
                        x='name', 
                        y='current_price',
                        title="Top 10 Cryptos by Price (USD)",
                        color='current_price',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig_price, use_container_width=True)
                    
                with tab2:
                    fig_change = px.bar(
                        df.nlargest(10, 'abs_change'), # Assuming we calculate abs change for sorting
                        x='name',
                        y='price_change_percentage_24h',
                        title="Top Movers (24h %)",
                        color='price_change_percentage_24h',
                        color_continuous_scale='RdYlGn'
                    )
                    # Add absolute change for sorting only
                    df['abs_change'] = df['price_change_percentage_24h'].abs()
                    fig_change = px.bar(
                        df.nlargest(15, 'abs_change'),
                        x='name',
                        y='price_change_percentage_24h',
                        color='price_change_percentage_24h',
                        title="Top 15 Volatile Assets (24h)",
                        color_continuous_scale=['red', 'yellow', 'green']
                    )
                    st.plotly_chart(fig_change, use_container_width=True)

                st.markdown("### 📋 Detailed Market Data")
                st.dataframe(
                    df[['rank', 'name', 'symbol', 'current_price', 'price_change_percentage_24h', 'market_cap', 'total_volume']],
                    column_config={
                        "current_price": st.column_config.NumberColumn("Price ($)", format="$%.2f"),
                        "price_change_percentage_24h": st.column_config.NumberColumn("24h Change", format="%.2f%%"),
                        "market_cap": st.column_config.NumberColumn("Market Cap", format="$%d"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
        else:
            st.error("Failed to fetch crypto data.")
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")

# --------------------------
# KNOWLEDGE BASE PAGE
# --------------------------
elif selected_page == "📚 Knowledge Base":
    st.header("📚 RAG Knowledge Base")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info("""
        **System Architecture**
        - **LLM**: Groq (Llama3/Mixtral)
        - **Vector DB**: ChromaDB
        - **Embeddings**: Sentence-Transformers
        """)
        
        if st.button("🔄 Update Knowledge Base", type="primary"):
            with st.spinner("Fetching latest crypto data..."):
                try:
                    response = requests.post(f"{API_URL}/update_knowledge", timeout=60)
                    if response.status_code == 200:
                        st.success("Successfully updated knowledge base with latest prices!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Update failed.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        try:
            response = requests.get(f"{API_URL}/system_stats")
            if response.status_code == 200:
                stats = response.json()
                
                st.markdown("### 📊 System Statistics")
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Total Facts Stored", stats.get('total_facts', 0))
                sc2.metric("Unique Assets", stats.get('unique_coins', 0))
                sc3.metric("Status", "Healthy")
                
                # Visualizing distribution if possible (mock data for now or detailed stats)
                st.progress(100, text="Vector Database Status: Optimized")
            else:
                st.warning("Could not fetch system stats.")
        except:
            st.warning("Backend offline.")

