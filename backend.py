from flask import Flask, jsonify, request
from data_ingestion.fetch_prices import CoinGeckoFetcher
from flask_cors import CORS
import requests
import time
import os

app = Flask(__name__)
CORS(app)

from rag_pipeline.langchain_generator import LangChainCryptoGenerator
generator = LangChainCryptoGenerator()
fetcher = CoinGeckoFetcher()

@app.route("/crypto_data", methods=["GET"])
def get_prices():
    """Fetches live data from CoinGecko securely via the backend"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": "bitcoin,ethereum,dogecoin",
            "order": "market_cap_desc"
        }
        response = requests.get(url, params=params)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # -------------------------------------------
@app.route("/generate_answer", methods=["POST"])
def generate_answer():
    """Handles both Chat and Evaluation queries with RAG toggle."""
    try:
        data = request.json
        query = data.get("query")
        use_rag = data.get("use_rag", True) # Toggle for evaluation comparison
        
        start_time = time.time()
        # Process through the LangChain RAG pipeline
        result = generator.generate_answer(query, use_rag=use_rag)
        total_time = time.time() - start_time

        return jsonify({
            "answer": result.answer,
            "facts_used": len(result.retrieval_result.facts) if result.retrieval_result else 0,
            "generation_time": total_time,
            "status": "success"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/crypto_data", methods=["GET"])
def get_crypto_live():
    """Fetches real-time prices for index and live-data pages."""
    try:
        data = fetcher.fetch_top_cryptocurrencies(limit=10)
        return jsonify([c.__dict__ for c in data])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/system_stats", methods=["GET"])
def get_system_stats():
    """Returns how many facts are currently stored in the system."""
    try:
        # In a real scenario, you would call vector_store.count() here
        return jsonify({
            "total_facts": 1250,  # Replace with actual DB count
            "unique_coins": 10,   # Replace with actual DB count
            "status": "healthy"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
import requests
from flask import Flask, jsonify

@app.route('/api/coingecko/global')
def get_coingecko_global():
    url = "https://api.coingecko.com/api/v3/global"
    response = requests.get(url)
    return jsonify(response.json())

import subprocess # To run external scripts if needed
from flask import Flask, jsonify

@app.route('/update_knowledge', methods=['POST'])
def trigger_update():
    try:
        # OPTION A: If your scraping logic is a function in another file
        # from scraper import run_main_scraper
        # run_main_scraper()
        
        # OPTION B: If your scraper is a standalone script (e.g., scraper.py)
        # subprocess.run(["python", "scraper.py"], check=True)
        
        print("Knowledge base update triggered successfully.")
        return jsonify({"status": "success", "message": "Database updated!"})
    except Exception as e:
        print(f"Update failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
import subprocess # To run external scripts if needed
from flask import Flask, jsonify

@app.route('/update_knowledge', methods=['POST'])
def trigger_update():
    try:
        # OPTION A: If your scraping logic is a function in another file
        # from scraper import run_main_scraper
        # run_main_scraper()
        
        # OPTION B: If your scraper is a standalone script (e.g., scraper.py)
        # subprocess.run(["python", "scraper.py"], check=True)
        
        print("Knowledge base update triggered successfully.")
        return jsonify({"status": "success", "message": "Database updated!"})
    except Exception as e:
        print(f"Update failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
    
if __name__ == "__main__":
    app.run(port=8000, debug=True)