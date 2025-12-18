# RAG Service

Retrieval Augmented Generation microservice for the Crypto Knowledge System.

## Features

- **Vector Storage**: ChromaDB for semantic search
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **LLM**: Groq API (Mixtral-8x7b-32768)
- **REST API**: FastAPI with automatic docs

## Port

**8011**

## Endpoints

### Health Check
```
GET /health
```

### Add Facts
```
POST /facts/add
Body: {
  "facts": [
    {
      "id": "bitcoin_price_123",
      "content": "Bitcoin is priced at $98,000",
      "metadata": {"coin": "bitcoin", "type": "price"}
    }
  ]
}
```

### Retrieve Facts
```
POST /retrieve
Body: {
  "query": "What is the price of Bitcoin?",
  "top_k": 5
}
```

### Generate Answer
```
POST /generate
Body: {
  "query": "What is the price of Bitcoin?",
  "use_rag": true
}
```

### Get Stats
```
GET /stats
```

### Clear Knowledge Base
```
DELETE /facts/clear
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variable:
```bash
# .env file
GROQ_API_KEY=your_groq_api_key_here
```

3. Run service:
```bash
python main.py
```

## API Documentation

Visit `http://localhost:8011/docs` for interactive API documentation.

## Architecture

```
User Query
    ↓
RAG Service (Port 8011)
    ↓
1. Embed query (Sentence Transformers)
2. Search ChromaDB (semantic similarity)
3. Retrieve top-k facts
4. Generate answer (Groq LLM + context)
    ↓
Return: answer + retrieved facts + metadata
```
