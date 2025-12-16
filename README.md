# Crypto Domain Knowledge Update System

A production-ready microservices system for cryptocurrency knowledge management using RAG (Retrieval-Augmented Generation), self-healing capabilities, and Groq LLM integration.

## 🏗️ Architecture Overview

The system consists of 12 microservices working together to provide real-time crypto knowledge updates:

### Core Services
1. **Ingestion Service** (Port 8001) - Ingests data from multiple crypto sources
2. **Fact Extraction Service** (Port 8002) - Extracts structured facts using Groq LLM
3. **Embedding Service** (Port 8003) - Generates embeddings for vector storage
4. **Storage Service** (Port 8004) - MongoDB-based fact storage
5. **Vector Retrieval Service** (Port 8005) - ChromaDB-based similarity search
6. **LLM Generator Service** (Port 8006) - Groq-powered answer generation with hallucination detection
7. **Self-Healing Orchestrator** (Port 8007) - Monitors and heals system components
8. **Cache Service** (Port 8008) - Redis-based caching layer
9. **API Gateway** (Port 8080) - Authentication and request routing
10. **UI Service** (Port 8501) - Streamlit-based user interface
11. **Batch Processor** (Port 8009) - Scheduled data processing
12. **Notification Service** (Port 8010) - System alerts and notifications

### Infrastructure Components
- **MongoDB** - Primary data storage
- **ChromaDB** - Vector database for embeddings
- **Redis** - Caching and message queuing
- **Groq API** - LLM inference and fact extraction

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Groq API key (required)
- Optional: API keys for data sources (CoinMarketCap, News API)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd crypto-knowledge-system
cp .env.example .env
```

### 2. Configure Groq API
Edit `.env` file and add your Groq API key:
```bash
GROQ_API_KEY=your_groq_api_key_here
```

**Getting a Groq API Key:**
1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key to your `.env` file

### 3. Optional: Configure Data Sources
Add API keys for additional data sources:
```bash
COINMARKETCAP_API_KEY=your_coinmarketcap_api_key
NEWS_API_KEY=your_news_api_key
```

### 4. Start the System
```bash
docker-compose up -d
```

### 5. Verify Services
Check all services are running:
```bash
docker-compose ps
```

Access the UI at: http://localhost:8501

## 📊 Service Details

### Groq LLM Integration

The system uses Groq for two main purposes:

1. **Fact Extraction** (Fact Extraction Service)
   - Processes raw news articles and social media content
   - Extracts structured facts with confidence scores
   - Model: `mixtral-8x7b-32768`

2. **Answer Generation** (LLM Generator Service)
   - Generates responses based on retrieved facts
   - Includes hallucination detection
   - Temperature: 0.1 for factual responses

### Hallucination Detection

The system includes sophisticated hallucination detection:
- Pattern-based detection for suspicious claims
- Fact consistency checking against source data
- Price accuracy validation
- Confidence scoring based on source reliability

### Self-Healing Capabilities

The orchestrator monitors all services and can:
- Restart failed services
- Scale services under load
- Clear cache when data becomes stale
- Send notifications for critical issues

## 🔧 Configuration

### Groq Model Configuration
```python
# In services/*/app/config.py
groq_model: str = "mixtral-8x7b-32768"  # Default model
groq_temperature: float = 0.1           # Low temperature for factual responses
groq_max_tokens: int = 2000            # Maximum response length
```

### Available Groq Models
- `mixtral-8x7b-32768` (Recommended) - Best balance of speed and quality
- `llama2-70b-4096` - High quality, slower
- `gemma-7b-it` - Faster, good for simple tasks

### Performance Tuning
```bash
# In .env file
WORKER_PROCESSES=4      # Number of worker processes per service
MAX_CONNECTIONS=1000    # Maximum concurrent connections
CACHE_TTL=300          # Cache time-to-live in seconds
```

## 📡 API Usage

### Query the System
```bash
curl -X POST "http://localhost:8080/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the current price of Bitcoin?",
    "symbols": ["BTC"],
    "limit": 10
  }'
```

### Trigger Data Ingestion
```bash
curl -X POST "http://localhost:8080/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTC", "ETH", "ADA"],
    "data_types": ["price", "news", "technical"]
  }'
```

### Health Check
```bash
curl http://localhost:8080/health
```

## 🔍 Monitoring

### Service Health
Each service exposes health endpoints:
```bash
curl http://localhost:8001/health  # Ingestion Service
curl http://localhost:8002/health  # Fact Extraction Service
# ... etc for all services
```

### System Status
```bash
curl http://localhost:8007/status  # Self-healing orchestrator status
```

### Logs
View logs for specific services:
```bash
docker-compose logs -f ingestion-service
docker-compose logs -f llm-generator-service
```

## 🛠️ Development

### Adding New Data Sources
1. Extend `CryptoDataSource` enum in `shared/models.py`
2. Add ingestion logic in `services/ingestion-service/app/ingestion.py`
3. Update fact extraction patterns in `services/fact-extraction-service/app/extractor.py`

### Custom Fact Types
1. Extend `FactType` enum in `shared/models.py`
2. Update extraction logic for new fact types
3. Modify embedding and retrieval logic if needed

### Scaling Services
Scale individual services:
```bash
docker-compose up -d --scale ingestion-service=3
docker-compose up -d --scale llm-generator-service=2
```

## 🔒 Security

### API Authentication
The API Gateway supports JWT-based authentication:
```bash
# Set JWT secret in .env
JWT_SECRET_KEY=your_secure_secret_key

# Use API key for service-to-service communication
API_KEY=your_api_key_for_authentication
```

### Rate Limiting
Built-in rate limiting prevents API abuse:
- 100 requests per minute per IP (configurable)
- Groq API rate limits respected

## 📈 Performance Optimization

### Caching Strategy
- Redis caching for frequently accessed data
- Vector similarity results cached for 5 minutes
- API responses cached based on query patterns

### Database Optimization
- MongoDB indexes on symbol, timestamp, fact_type
- ChromaDB collections partitioned by symbol
- Connection pooling for all database connections

## 🚨 Troubleshooting

### Common Issues

1. **Groq API Key Issues**
   ```bash
   # Check if key is set
   docker-compose exec llm-generator-service env | grep GROQ
   
   # Test API connectivity
   curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models
   ```

2. **Service Connection Issues**
   ```bash
   # Check service connectivity
   docker-compose exec api-gateway curl http://llm-generator-service:8006/health
   ```

3. **Database Connection Issues**
   ```bash
   # Check MongoDB
   docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
   
   # Check Redis
   docker-compose exec redis redis-cli ping
   
   # Check ChromaDB
   curl http://localhost:8000/api/v1/heartbeat
   ```

### Performance Issues
- Monitor service logs for bottlenecks
- Check Redis memory usage
- Monitor Groq API rate limits
- Scale services horizontally as needed

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Open an issue on GitHub
4. Contact the development team

---

**Note**: This system requires a Groq API key to function. The free tier provides sufficient quota for development and testing. For production use, consider upgrading to a paid plan for higher rate limits and guaranteed availability.