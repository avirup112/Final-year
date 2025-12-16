"""
Database Schema Adapter for Crypto Knowledge System
Handles schema variations and missing attributes like 'retrieval_time'
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from sqlalchemy import inspect, text, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError
import pymongo
from .utils import setup_logging

logger = setup_logging("database_adapter")

class DatabaseSchemaAdapter:
    """Adapts different database schemas to a common interface"""
    
    def __init__(self, db):
        self.db = db
        self.db_type = self._detect_db_type()
        self.schema_map = self._detect_schema()
        logger.info(f"Initialized adapter for {self.db_type} database")
    
    def _detect_db_type(self) -> str:
        """Detect the type of database connection"""
        if hasattr(self.db, 'engine'):
            return 'sqlalchemy'
        elif hasattr(self.db, 'cursor'):
            return 'raw_sql'
        elif hasattr(self.db, 'list_collection_names'):
            return 'mongodb'
        elif hasattr(self.db, 'get_collection'):
            return 'chromadb'
        else:
            return 'unknown'
    
    def _detect_schema(self) -> Dict[str, str]:
        """Auto-detect and map database schema variations"""
        schema_variations = {
            'retrieval_time': [
                'retrieval_time', 'retrieved_at', 'fetch_time', 
                'last_updated', 'timestamp', 'created_at', 'updated_at'
            ],
            'price': ['price', 'current_price', 'value', 'amount', 'close_price'],
            'symbol': ['symbol', 'ticker', 'coin', 'currency_code', 'asset'],
            'volume': ['volume', 'trading_volume', 'vol', 'volume_24h'],
            'market_cap': ['market_cap', 'marketcap', 'market_capitalization', 'mcap']
        }
        
        detected_map = {}
        available_columns = self._get_available_columns()
        
        for standard_field, variations in schema_variations.items():
            for variation in variations:
                if variation in available_columns:
                    detected_map[standard_field] = variation
                    logger.debug(f"Mapped {standard_field} -> {variation}")
                    break
            else:
                detected_map[standard_field] = None
                logger.warning(f"No mapping found for {standard_field}")
                
        return detected_map
    
    def _get_available_columns(self) -> List[str]:
        """Get available columns from different DB types"""
        try:
            if self.db_type == 'sqlalchemy':
                inspector = inspect(self.db.engine)
                tables = inspector.get_table_names()
                
                # Check common table names
                table_candidates = ['crypto_data', 'crypto_facts', 'facts', 'prices']
                target_table = None
                
                for candidate in table_candidates:
                    if candidate in tables:
                        target_table = candidate
                        break
                
                if target_table:
                    columns = inspector.get_columns(target_table)
                    return [col['name'] for col in columns]
                else:
                    logger.warning(f"No recognized tables found in: {tables}")
                    return []
                    
            elif self.db_type == 'raw_sql':
                cursor = self.db.cursor()
                # Try different table names
                for table in ['crypto_data', 'crypto_facts', 'facts']:
                    try:
                        cursor.execute(f"SELECT * FROM {table} LIMIT 0")
                        return [desc[0] for desc in cursor.description]
                    except:
                        continue
                return []
                
            elif self.db_type == 'mongodb':
                # Check common collection names
                collections = self.db.list_collection_names()
                collection_candidates = ['crypto_data', 'crypto_facts', 'facts']
                
                for candidate in collection_candidates:
                    if candidate in collections:
                        sample = self.db[candidate].find_one()
                        return list(sample.keys()) if sample else []
                return []
                
        except Exception as e:
            logger.error(f"Column detection error: {e}")
            return []
    
    def get_retrieval_time(self, record: Union[Dict, Any]) -> Optional[datetime]:
        """Safely get retrieval time regardless of schema"""
        time_field = self.schema_map.get('retrieval_time')
        
        if time_field:
            if hasattr(record, time_field):
                value = getattr(record, time_field)
            elif isinstance(record, dict):
                value = record.get(time_field)
            else:
                value = None
                
            # Convert to datetime if needed
            if value:
                if isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        return datetime.now()
                elif isinstance(value, datetime):
                    return value
                        
        # Fallback: return current time
        logger.debug("No retrieval_time found, using current time")
        return datetime.now()
    
    def set_retrieval_time(self, record: Union[Dict, Any], timestamp: Optional[datetime] = None) -> bool:
        """Safely set retrieval time"""
        if timestamp is None:
            timestamp = datetime.now()
            
        time_field = self.schema_map.get('retrieval_time') or 'retrieval_time'
        
        try:
            if hasattr(record, time_field):
                setattr(record, time_field, timestamp)
                return True
            elif isinstance(record, dict):
                record[time_field] = timestamp
                return True
            else:
                # Try to add attribute dynamically
                if hasattr(record, '__dict__'):
                    setattr(record, time_field, timestamp)
                    return True
        except Exception as e:
            logger.error(f"Failed to set retrieval_time: {e}")
            
        return False
    
    def is_data_fresh(self, record: Union[Dict, Any], max_age_minutes: int = 5) -> bool:
        """Check if data is fresh enough"""
        retrieval_time = self.get_retrieval_time(record)
        
        if not retrieval_time:
            return False
            
        age = datetime.now() - retrieval_time
        return age.total_seconds() < (max_age_minutes * 60)
    
    def get_field_value(self, record: Union[Dict, Any], standard_field: str) -> Any:
        """Get field value using schema mapping"""
        mapped_field = self.schema_map.get(standard_field)
        
        if not mapped_field:
            return None
            
        if hasattr(record, mapped_field):
            return getattr(record, mapped_field)
        elif isinstance(record, dict):
            return record.get(mapped_field)
            
        return None
    
    def validate_schema(self) -> Dict[str, bool]:
        """Validate current schema against requirements"""
        required_fields = ['retrieval_time', 'symbol', 'price']
        validation_results = {}
        
        for field in required_fields:
            validation_results[field] = self.schema_map.get(field) is not None
            
        return validation_results
    
    def safe_get_attribute(self, obj: Any, attr_name: str, default: Any = None) -> Any:
        """Safely get attribute with fallback handling for missing retrieval_time"""
        try:
            # First try direct attribute access
            if hasattr(obj, attr_name):
                return getattr(obj, attr_name)
            
            # Try mapped field name
            mapped_field = self.schema_map.get(attr_name)
            if mapped_field and hasattr(obj, mapped_field):
                return getattr(obj, mapped_field)
            
            # Try dictionary access
            if isinstance(obj, dict):
                if attr_name in obj:
                    return obj[attr_name]
                elif mapped_field and mapped_field in obj:
                    return obj[mapped_field]
            
            # Special handling for retrieval_time
            if attr_name == 'retrieval_time':
                logger.warning(f"retrieval_time not found, using current time")
                current_time = datetime.now()
                # Try to set it for future use
                self.set_retrieval_time(obj, current_time)
                return current_time
            
            return default
            
        except AttributeError as e:
            if 'retrieval_time' in str(e):
                logger.warning(f"AttributeError for retrieval_time: {e}")
                current_time = datetime.now()
                self.set_retrieval_time(obj, current_time)
                return current_time
            else:
                logger.error(f"Unexpected AttributeError: {e}")
                return default
        except Exception as e:
            logger.error(f"Error in safe_get_attribute: {e}")
            return default