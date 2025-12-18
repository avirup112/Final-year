# Crypto Knowledge System - Frontend UI

## Overview
Modern web-based UI for the Crypto Knowledge System microservices architecture.

## Features
- **Dashboard**: Real-time system status and service health monitoring
- **AI Chat**: Interactive chat interface for querying the knowledge base
- **Service Monitoring**: Visual status of all microservices
- **Data Management**: Trigger data ingestion and view recent facts
- **Authentication**: JWT-based authentication with API Gateway

## Architecture
The UI integrates with the backend through the API Gateway (port 8080):
- All requests go through the API Gateway
- JWT authentication for secure access
- Real-time status updates every 30 seconds

## Files
- `index.html` - Main dashboard page
- `ai-chat.html` - AI chat interface
- `main.js` - Dashboard JavaScript logic
- `style.css` - Styling for all pages

## API Integration
The frontend communicates with these API Gateway endpoints:
- `POST /auth/token` - Authentication
- `GET /system/health` - System health status
- `GET /services/status` - All services status
- `POST /knowledge/query` - Query the knowledge base
- `POST /data/fetch` - Trigger data ingestion
- `GET /data/facts` - Get stored facts
- `GET /system/healing-events` - Recent healing events

## Configuration
Update `API_CONFIG` in `main.js`:
```javascript
const API_CONFIG = {
    API_GATEWAY: 'http://localhost:8080',
    API_KEY: 'crypto-knowledge-api-key'
};
```

## Running
The UI is served by the UI Service (FastAPI) on port 3000:
```bash
# Via Docker
docker-compose up ui-service

# Direct access
http://localhost:3000
```

## Development
For local development without Docker:
```bash
cd services/ui-service
pip install -r requirements.txt
python app/main.py
```

Then access at http://localhost:3000
