"""
Crypto Time-Series Data Manager for MongoDB
Handles time-series crypto data with proper versioning and historical storage
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
import httpx
import os
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSource(Enum):
    COINGECKO = "CoinGecko"
    COINMARKETCAP = "CoinMarketCap"
    NEWS_API = "NewsAPI"

@dataclass
class CryptoDataPoint:
    """Single crypto data point structure"""
    _id: Optional[str]
    coin: 