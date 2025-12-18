# 🚀 Crypto Knowledge System

A unified crypto intelligence platform with AI-powered knowledge retrieval, real-time data ingestion, and interactive web interface.

## ✨ Features

- **🤖 AI-Powered Chat**: Ask questions about cryptocurrencies and get intelligent responses
- **📊 Real-time Dashboard**: Monitor system health and crypto market data
- **🔍 Knowledge Base**: Store and retrieve crypto facts and insights
- **🌐 Web Interface**: Modern, responsive UI with multiple pages
- **🔧 REST API**: Full API with comprehensive endpoints
- **📈 System Monitoring**: Health checks and performance metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)

### Installation & Setup

1. **Clone and navigate to the project**:
   ```bash
   cd crypto-currency
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv myenv
   myenv\Scripts\activate  # Windows
   # or
   source myenv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your API keys if needed
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the system**:
   - 🌐 **Main UI**: http://localhost:8080
   - 💬 **AI Chat**: http://localhost:8080/ai-chat
   - 🔧 **API Docs**: http://localhost:8080/docs
   - ❤️ **Health Check**: http://localhost:8080/health

## 🎯 Usage

### Web Interface

- **Dashboard**: Overview of system status and crypto data
- **AI Chat**: Interactive chat interface for crypto questions
- **Knowledge Base**: Browse stored crypto facts and insights
- **Live Data**: Real-time crypto market information
- **System Health**: Monitor service status and performance

### API Endpoints

#### Core Endpoints
- `GET /` - Main dashboard
- `GET /health` - System health check
- `GET /docs` - API documentation

#### Knowledge & Query
- `POST /api/query` - Query the knowledge system
- `POST /knowledge/query` - AI chat queries
- `GET /api/facts` - Get crypto facts

#### System Management
- `GET /system/health` - Detailed system health
- `GET /services/status` - Service status
- `GET /data/facts` - Data facts
- `POST /data/fetch` - Trigger data fetch

#### Authentication
- `POST /auth/token` - Get authentication token

### Example API Usage

```python
import requests

# Get system health
response = requests.get("http://localhost:8080/health")
print(response.json())

# Ask AI a question
auth_response = requests.post("http://localhost:8080/auth/token", 
                            json={"api_key": "crypto-knowledge-api-key"})
token = auth_response.json()["access_token"]

query_response = requests.post("http://localhost:8080/knowledge/query",
                             json={"question": "What is Bitcoin?"},
                             headers={"Authorization": f"Bearer {token}"})
print(query_response.json())
```

## 🏗️ Architecture

### Unified Application Structure
```
crypto-currency/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── .env                  # Environment configuration
├── ui/                   # Web interface files
│   ├── index.html        # Main dashboard
│   ├── ai-chat.html      # AI chat interface
│   ├── style.css         # Styling
│   └── main.js           # JavaScript functionality
├── shared/               # Shared utilities
│   ├── models.py         # Data models
│   ├── utils.py          # Utility functions
│   └── database_*.py     # Database adapters
└── services/             # Individual service modules
    ├── ingestion-service/
    ├── llm-generator-service/
    └── ...               # Other services
```

### Key Components

1. **FastAPI Application** (`app.py`):
   - Unified web server and API
   - Static file serving for UI
   - Authentication and CORS handling
   - Mock data endpoints for development

2. **Web Interface** (`ui/`):
   - Responsive HTML/CSS/JS frontend
   - Real-time dashboard updates
   - Interactive AI chat interface
   - Multiple page navigation

3. **Shared Modules** (`shared/`):
   - Common utilities and models
   - Database adapters
   - Reusable components

## 🔧 Configuration

### Environment Variables (.env)

```bash
# API Keys (optional for basic functionality)
GROQ_API_KEY=your_groq_api_key
COINMARKETCAP_API_KEY=your_cmc_api_key
COINGECKO_API_KEY=your_coingecko_api_key
NEWS_API_KEY=your_news_api_key

# System Configuration
LOG_LEVEL=INFO
UPDATE_INTERVAL_MINUTES=5
MAX_CRYPTO_COINS=10

# LLM Configuration
LLM_MODEL=llama-3.3-70b-versatile
MAX_TOKENS=1000
TEMPERATURE=0.1
```

## 🚀 Development

### Running in Development Mode

```bash
# With auto-reload
uvicorn app:app --host localhost --port 8080 --reload

# Or simply
python app.py
```

### Adding New Features

1. **API Endpoints**: Add new routes in `app.py`
2. **UI Pages**: Create new HTML files in `ui/`
3. **Shared Logic**: Add utilities in `shared/`
4. **Service Modules**: Extend individual services in `services/`

### Testing

```bash
# Test API endpoints
curl http://localhost:8080/health

# Test AI chat
curl -X POST http://localhost:8080/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Ethereum?"}'
```

## 📊 Features in Detail

### AI Chat System
- Natural language processing for crypto questions
- Context-aware responses
- Support for various crypto topics
- Real-time chat interface

### Dashboard & Monitoring
- System health visualization
- Service status monitoring
- Performance metrics
- Real-time updates

### Knowledge Management
- Crypto fact storage and retrieval
- Categorized information
- Confidence scoring
- Search capabilities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

- Check the API documentation at `/docs`
- Monitor system health at `/health`
- Review logs in the console output
- Open issues for bugs or feature requests

---

**🎉 Enjoy exploring the crypto knowledge system!**