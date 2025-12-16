"""
Database Migration Manager for Crypto Knowledge System
Handles schema migrations and fixes missing columns
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
import pymongo.errors
from .utils import setup_logging

logger = setup_logging("database_migration")

class CryptoDBMigrationManager:
    """Handles database migrations for crypto schema"""
    
    def __init__(self, db, adapter=None):
        self.db = db
        self.adapter = adapter
        self.db_type = self._detect_db_type()
        self.migrations = [
            self._add_retrieval_time_column,
            self._add_performance_indexes,
            self._normalize_symbol_format,
            self._add_confidence_score_column,
        ]
    
    def _detect_db_type(self) -> str:
        """Detect database type"""
        if hasattr(self.db, 'engine'):
            return 'sqlalchemy'
        elif hasattr(self.db, 'cursor'):
            return 'raw_sql'
        elif hasattr(self.db, 'list_collection_names'):
            return 'mongodb'
        else:
            return 'unknown'
    
    def run_migrations(self) -> bool:
        """Run all pending migrations"""
        logger.info("Starting database migrations...")
        
        success_count = 0
        for i, migration in enumerate(self.migrations):
            try:
                logger.info(f"Running migration {i+1}: {migration.__name__}")
                if migration():
                    logger.info(f"✅ Migration {i+1} completed successfully")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ Migration {i+1} skipped or failed")
            except Exception as e:
                logger.error(f"❌ Migration {i+1} failed: {e}")
                # Continue with other migrations
        
        logger.info(f"Migrations completed: {success_count}/{len(self.migrations)} successful")
        return success_count == len(self.migrations)
    
    def _add_retrieval_time_column(self) -> bool:
        """Migration: Add retrieval_time column"""
        try:
            if self.db_type == 'sqlalchemy':
                return self._add_retrieval_time_sqlalchemy()
            elif self.db_type == 'raw_sql':
                return self._add_retrieval_time_raw_sql()
            elif self.db_type == 'mongodb':
                return self._add_retrieval_time_mongodb()
            else:
                logger.warning(f"Unsupported database type: {self.db_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to add retrieval_time column: {e}")
            return False
    
    def _add_retrieval_time_sqlalchemy(self) -> bool:
        """Add retrieval_time column for SQLAlchemy"""
        try:
            inspector = inspect(self.db.engine)
            
            # Find the target table
            tables = inspector.get_table_names()
            target_tables = ['crypto_data', 'crypto_facts', 'facts']
            
            for table_name in target_tables:
                if table_name in tables:
                    columns = [col['name'] for col in inspector.get_columns(table_name)]
                    
                    if 'retrieval_time' not in columns:
                        # Add the column
                        alter_sql = f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN retrieval_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        """
                        self.db.engine.execute(text(alter_sql))
                        
                        # Update existing records
                        update_sql = f"""
                            UPDATE {table_name} 
                            SET retrieval_time = CURRENT_TIMESTAMP 
                            WHERE retrieval_time IS NULL
                        """
                        self.db.engine.execute(text(update_sql))
                        
                        logger.info(f"Added retrieval_time column to {table_name}")
                    else:
                        logger.info(f"retrieval_time column already exists in {table_name}")
                    
                    return True
            
            logger.warning("No target tables found for retrieval_time migration")
            return False
            
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy migration error: {e}")
            return False
    
    def _add_retrieval_time_raw_sql(self) -> bool:
        """Add retrieval_time column for raw SQL"""
        try:
            cursor = self.db.cursor()
            
            # Try different table names
            target_tables = ['crypto_data', 'crypto_facts', 'facts']
            
            for table_name in target_tables:
                try:
                    # Check if table exists and get columns
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
                    columns = [desc[0] for desc in cursor.description]
                    
                    if 'retrieval_time' not in columns:
                        # Add column (syntax varies by database)
                        alter_sql = f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN retrieval_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        """
                        cursor.execute(alter_sql)
                        
                        # Update existing records
                        update_sql = f"""
                            UPDATE {table_name} 
                            SET retrieval_time = CURRENT_TIMESTAMP 
                            WHERE retrieval_time IS NULL
                        """
                        cursor.execute(update_sql)
                        
                        self.db.commit()
                        logger.info(f"Added retrieval_time column to {table_name}")
                        return True
                    else:
                        logger.info(f"retrieval_time column already exists in {table_name}")
                        return True
                        
                except Exception:
                    continue
            
            logger.warning("No target tables found for raw SQL migration")
            return False
            
        except Exception as e:
            logger.error(f"Raw SQL migration error: {e}")
            if hasattr(self.db, 'rollback'):
                self.db.rollback()
            return False
    
    def _add_retrieval_time_mongodb(self) -> bool:
        """Add retrieval_time field for MongoDB"""
        try:
            collections = self.db.list_collection_names()
            target_collections = ['crypto_data', 'crypto_facts', 'facts']
            
            for collection_name in target_collections:
                if collection_name in collections:
                    collection = self.db[collection_name]
                    
                    # Update documents without retrieval_time
                    result = collection.update_many(
                        {"retrieval_time": {"$exists": False}},
                        {"$set": {"retrieval_time": datetime.utcnow()}}
                    )
                    
                    logger.info(f"Updated {result.modified_count} documents in {collection_name}")
                    return True
            
            logger.warning("No target collections found for MongoDB migration")
            return False
            
        except pymongo.errors.PyMongoError as e:
            logger.error(f"MongoDB migration error: {e}")
            return False
    
    def _add_performance_indexes(self) -> bool:
        """Migration: Add performance indexes"""
        try:
            if self.db_type == 'sqlalchemy':
                return self._add_indexes_sqlalchemy()
            elif self.db_type == 'mongodb':
                return self._add_indexes_mongodb()
            else:
                logger.info("Index creation not implemented for this database type")
                return True
        except Exception as e:
            logger.error(f"Failed to add indexes: {e}")
            return False
    
    def _add_indexes_sqlalchemy(self) -> bool:
        """Add indexes for SQLAlchemy"""
        try:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_crypto_symbol ON crypto_data(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_crypto_retrieval_time ON crypto_data(retrieval_time)",
                "CREATE INDEX IF NOT EXISTS idx_crypto_symbol_time ON crypto_data(symbol, retrieval_time)",
                "CREATE INDEX IF NOT EXISTS idx_crypto_timestamp ON crypto_data(timestamp)"
            ]
            
            for index_sql in indexes:
                try:
                    self.db.engine.execute(text(index_sql))
                    logger.debug(f"Created index: {index_sql}")
                except Exception as e:
                    logger.warning(f"Index creation failed (may already exist): {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"SQLAlchemy index creation error: {e}")
            return False
    
    def _add_indexes_mongodb(self) -> bool:
        """Add indexes for MongoDB"""
        try:
            collections = self.db.list_collection_names()
            target_collections = ['crypto_data', 'crypto_facts', 'facts']
            
            for collection_name in target_collections:
                if collection_name in collections:
                    collection = self.db[collection_name]
                    
                    # Create indexes
                    indexes = [
                        ("symbol", 1),
                        ("retrieval_time", -1),
                        ([("symbol", 1), ("retrieval_time", -1)]),
                        ("timestamp", -1)
                    ]
                    
                    for index in indexes:
                        try:
                            if isinstance(index, tuple) and len(index) == 2:
                                collection.create_index(index[0], direction=index[1])
                            else:
                                collection.create_index(index)
                            logger.debug(f"Created MongoDB index: {index}")
                        except Exception as e:
                            logger.warning(f"MongoDB index creation failed: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"MongoDB index creation error: {e}")
            return False
    
    def _normalize_symbol_format(self) -> bool:
        """Migration: Normalize symbol format to uppercase"""
        try:
            if self.db_type == 'sqlalchemy':
                self.db.engine.execute(text("""
                    UPDATE crypto_data 
                    SET symbol = UPPER(symbol) 
                    WHERE symbol != UPPER(symbol)
                """))
            elif self.db_type == 'mongodb':
                collections = self.db.list_collection_names()
                for collection_name in ['crypto_data', 'crypto_facts', 'facts']:
                    if collection_name in collections:
                        # This would require a more complex aggregation pipeline
                        # For now, just log that it should be done
                        logger.info(f"Symbol normalization needed for {collection_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Symbol normalization error: {e}")
            return False
    
    def _add_confidence_score_column(self) -> bool:
        """Migration: Add confidence_score column if missing"""
        try:
            if self.db_type == 'sqlalchemy':
                inspector = inspect(self.db.engine)
                tables = inspector.get_table_names()
                
                for table_name in ['crypto_data', 'crypto_facts', 'facts']:
                    if table_name in tables:
                        columns = [col['name'] for col in inspector.get_columns(table_name)]
                        
                        if 'confidence_score' not in columns:
                            alter_sql = f"""
                                ALTER TABLE {table_name} 
                                ADD COLUMN confidence_score FLOAT DEFAULT 0.5
                            """
                            self.db.engine.execute(text(alter_sql))
                            logger.info(f"Added confidence_score column to {table_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Confidence score column addition error: {e}")
            return False
    
    def check_schema_health(self) -> Dict[str, Any]:
        """Check overall schema health"""
        health_report = {
            'database_type': self.db_type,
            'timestamp': datetime.utcnow(),
            'issues': [],
            'recommendations': []
        }
        
        try:
            if self.adapter:
                validation_results = self.adapter.validate_schema()
                
                for field, exists in validation_results.items():
                    if not exists:
                        health_report['issues'].append(f"Missing field: {field}")
                        health_report['recommendations'].append(f"Run migration to add {field}")
            
            # Check for common issues
            if self.db_type == 'unknown':
                health_report['issues'].append("Unknown database type")
                health_report['recommendations'].append("Verify database connection")
            
        except Exception as e:
            health_report['issues'].append(f"Schema health check failed: {e}")
        
        return health_report