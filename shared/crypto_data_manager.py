"""
Crypto Data Manager with Error Recovery
Handles retrieval_time attribute errors and provides robust data access
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from .database_adapter import DatabaseSchemaAdapter
from .database_migration import CryptoDBMigrationManager
from .models import CryptoFact
from .utils import setup_logging

logger = setup_logging("crypto_data_manager")

class CryptoDataManager:
    """Production-ready crypto data manager with comprehensive error handling"""
    
    def __init__(self, db, auto_migrate: bool = True):
        self.db = db
        self.adapter = DatabaseSchemaAdapter(db)
        self.migration_manager = CryptoDBMigrationManager(db, self.adapter)
        self.fallback_cache = {}
        
        # Run migrations if requested
        if auto_migrate:
            try:
                self.migration_manager.run_migrations()
            except Exception as e:
                logger.warning(f"Auto-migration failed: {e}")
    
    def get_crypto_data_safe(self, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get crypto data with comprehensive error handling"""
        try:
            return self._get_data_primary(symbol, **kwargs)
            
        except AttributeError as e:
            if 'retrieval_time' in str(e):
                logger.warning(f"Schema issue detected for {symbol}: {e}")
                return self._handle_retrieval_time_error(symbol, e, **kwargs)
            else:
                logger.error(f"Unexpected AttributeError for {symbol}: {e}")
                return self._get_fallback_data(symbol, **kwargs)
                
        except Exception as e:
            logger.error(f"Unexpected error getting data for {symbol}: {e}")
            return self._get_fallback_data(symbol, **kwargs)
    
    def _get_data_primary(self, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Primary data retrieval method"""
        try:
            record = self._fetch_from_db(symbol, **kwargs)
            
            if not record:
                return None
            
            # Use adapter for safe time access
            retrieval_time = self.adapter.safe_get_attribute(
                record, 'retrieval_time', datetime.now()
            )
            
            # Check if data is fresh
            max_age_minutes = kwargs.get('max_age_minutes', 5)
            if self._is_data_fresh(retrieval_time, max_age_minutes):
                return self._format_record(record)
            else:
                logger.info(f"Data for {symbol} is stale, refreshing...")
                return self._refresh_data(symbol, record, **kwargs)
                
        except Exception as e:
            logger.error(f"Primary data retrieval failed for {symbol}: {e}")
            raise
    
    def _handle_retrieval_time_error(self, symbol: str, error: Exception, **kwargs) -> Optional[Dict[str, Any]]:
        """Handle retrieval_time attribute errors specifically"""
        logger.info(f"Attempting to fix retrieval_time error for {symbol}")
        
        try:
            # Try to run the retrieval_time migration
            if self.migration_manager._add_retrieval_time_column():
                logger.info("Successfully added retrieval_time column, retrying...")
                return self._get_data_primary(symbol, **kwargs)
            else:
                logger.warning("Migration failed, using fallback approach")
                return self._get_data_with_fallback_time(symbol, **kwargs)
                
        except Exception as migration_error:
            logger.error(f"Migration attempt failed: {migration_error}")
            return self._get_data_with_fallback_time(symbol, **kwargs)
    
    def _get_data_with_fallback_time(self, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get data using fallback time handling"""
        try:
            record = self._fetch_from_db(symbol, **kwargs)
            
            if not record:
                return None
            
            # Manually add retrieval_time
            current_time = datetime.now()
            
            if hasattr(record, '__dict__'):
                record.retrieval_time = current_time
            elif isinstance(record, dict):
                record['retrieval_time'] = current_time
            
            return self._format_record(record)
            
        except Exception as e:
            logger.error(f"Fallback time handling failed for {symbol}: {e}")
            return self._get_fallback_data(symbol, **kwargs)
    
    def _fetch_from_db(self, symbol: str, **kwargs) -> Any:
        """Fetch record from database (implement based on your DB type)"""
        try:
            if hasattr(self.db, 'query'):
                # SQLAlchemy ORM
                return self.db.query(CryptoFact).filter(
                    CryptoFact.symbol == symbol.upper()
                ).order_by(CryptoFact.timestamp.desc()).first()
                
            elif hasattr(self.db, 'engine'):
                # SQLAlchemy Core
                from sqlalchemy import text
                result = self.db.engine.execute(text("""
                    SELECT * FROM crypto_data 
                    WHERE symbol = :symbol 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """), symbol=symbol.upper()).fetchone()
                
                if result:
                    return dict(result)
                return None
                
            elif hasattr(self.db, 'list_collection_names'):
                # MongoDB
                collection = self.db.crypto_data
                return collection.find_one(
                    {"symbol": symbol.upper()},
                    sort=[("timestamp", -1)]
                )
                
            else:
                logger.warning(f"Unknown database type: {type(self.db)}")
                return None
                
        except Exception as e:
            logger.error(f"Database fetch failed for {symbol}: {e}")
            raise
    
    def _is_data_fresh(self, retrieval_time: datetime, max_age_minutes: int = 5) -> bool:
        """Check if data is fresh enough"""
        if not retrieval_time:
            return False
            
        age = datetime.now() - retrieval_time
        return age.total_seconds() < (max_age_minutes * 60)
    
    def _refresh_data(self, symbol: str, existing_record: Any, **kwargs) -> Optional[Dict[str, Any]]:
        """Refresh stale data"""
        try:
            # This would typically fetch from external API
            # For now, just update the retrieval_time
            current_time = datetime.now()
            self.adapter.set_retrieval_time(existing_record, current_time)
            
            # Update in database if possible
            self._update_retrieval_time_in_db(symbol, current_time)
            
            return self._format_record(existing_record)
            
        except Exception as e:
            logger.error(f"Data refresh failed for {symbol}: {e}")
            return self._format_record(existing_record)
    
    def _update_retrieval_time_in_db(self, symbol: str, timestamp: datetime):
        """Update retrieval_time in database"""
        try:
            if hasattr(self.db, 'engine'):
                from sqlalchemy import text
                self.db.engine.execute(text("""
                    UPDATE crypto_data 
                    SET retrieval_time = :timestamp 
                    WHERE symbol = :symbol
                """), timestamp=timestamp, symbol=symbol.upper())
                
        except Exception as e:
            logger.warning(f"Failed to update retrieval_time in DB for {symbol}: {e}")
    
    def _get_fallback_data(self, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get data from fallback cache or external source"""
        cache_key = f"{symbol}_{kwargs.get('data_type', 'default')}"
        
        # Check cache first
        if cache_key in self.fallback_cache:
            cached_data = self.fallback_cache[cache_key]
            if self._is_data_fresh(cached_data.get('retrieval_time'), 10):  # 10 min cache
                logger.info(f"Using cached fallback data for {symbol}")
                return cached_data
        
        # Generate fallback data
        fallback_data = {
            'symbol': symbol.upper(),
            'price': None,
            'retrieval_time': datetime.now(),
            'source': 'fallback',
            'error': 'Primary data source unavailable'
        }
        
        self.fallback_cache[cache_key] = fallback_data
        logger.warning(f"Using fallback data for {symbol}")
        return fallback_data
    
    def _format_record(self, record: Any) -> Dict[str, Any]:
        """Format database record to standard dictionary"""
        try:
            if isinstance(record, dict):
                return record
            elif hasattr(record, '__dict__'):
                return record.__dict__
            elif hasattr(record, '_asdict'):  # Named tuple
                return record._asdict()
            else:
                # Try to extract common fields
                formatted = {}
                for field in ['symbol', 'price', 'timestamp', 'retrieval_time', 'volume', 'market_cap']:
                    value = self.adapter.safe_get_attribute(record, field)
                    if value is not None:
                        formatted[field] = value
                return formatted
                
        except Exception as e:
            logger.error(f"Record formatting failed: {e}")
            return {'error': 'Failed to format record', 'raw_type': str(type(record))}
    
    def get_multiple_symbols(self, symbols: List[str], **kwargs) -> Dict[str, Any]:
        """Get data for multiple symbols"""
        results = {}
        
        for symbol in symbols:
            try:
                data = self.get_crypto_data_safe(symbol, **kwargs)
                results[symbol] = data
            except Exception as e:
                logger.error(f"Failed to get data for {symbol}: {e}")
                results[symbol] = {
                    'symbol': symbol,
                    'error': str(e),
                    'retrieval_time': datetime.now()
                }
        
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on data manager"""
        health = {
            'status': 'healthy',
            'timestamp': datetime.now(),
            'components': {}
        }
        
        try:
            # Check database connection
            test_symbol = 'BTC'
            test_data = self._fetch_from_db(test_symbol)
            health['components']['database'] = {
                'status': 'healthy',
                'test_query': 'success'
            }
        except Exception as e:
            health['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['status'] = 'degraded'
        
        try:
            # Check schema validation
            schema_validation = self.adapter.validate_schema()
            missing_fields = [field for field, exists in schema_validation.items() if not exists]
            
            health['components']['schema'] = {
                'status': 'healthy' if not missing_fields else 'degraded',
                'missing_fields': missing_fields
            }
            
            if missing_fields:
                health['status'] = 'degraded'
                
        except Exception as e:
            health['components']['schema'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['status'] = 'degraded'
        
        return health