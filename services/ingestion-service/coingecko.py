import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def fetch_market_data(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch live market data from CoinGecko"""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully fetched {len(data)} coins from CoinGecko")
                return data
            elif response.status_code == 429:
                logger.warning("⚠️ CoinGecko Rate Limit Hit")
                return []
            else:
                logger.error(f"❌ CoinGecko Error: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"❌ Connection Error: {e}")
        return []
