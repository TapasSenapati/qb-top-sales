"""
DuckDB client for forecasting analytics.

This module provides connection management and schema initialization
for the DuckDB analytical database used by the forecasting service.
"""

import os
import logging
import duckdb
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Configuration from environment
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/data/forecasting.duckdb")


class DuckDBClient:
    """
    Manages DuckDB connections and schema initialization.
    
    DuckDB supports single-writer, multiple-reader access.
    - Aggregation service (Java): writes
    - Forecasting service (Python): reads + writes forecasts
    """
    
    _instance: Optional["DuckDBClient"] = None
    
    def __init__(self, db_path: str = DUCKDB_PATH):
        self.db_path = db_path
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        logger.info(f"DuckDB client initialized with path: {db_path}")
    
    @classmethod
    def get_instance(cls) -> "DuckDBClient":
        """Get singleton instance of DuckDBClient."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _ensure_directory(self) -> None:
        """Ensure the directory for the database file exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created directory for DuckDB: {db_dir}")
    
    def connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """
        Get a connection to DuckDB.
        
        Args:
            read_only: If True, open in read-only mode (allows concurrent reads)
        
        Returns:
            DuckDB connection
        """
        self._ensure_directory()
        return duckdb.connect(self.db_path, read_only=read_only)
    
    @contextmanager
    def get_connection(self, read_only: bool = False):
        """
        Context manager for DuckDB connections.
        
        Usage:
            with client.get_connection() as conn:
                conn.execute("SELECT * FROM table")
        """
        conn = self.connect(read_only=read_only)
        try:
            yield conn
        finally:
            conn.close()
    
    def init_schema(self) -> None:
        """
        Initialize the DuckDB schema.
        Creates tables directly for reliability.
        """
        logger.info("Initializing DuckDB schema...")
        
        with self.get_connection() as conn:
            # Create category_sales_agg table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS category_sales_agg (
                    id BIGINT,
                    merchant_id BIGINT NOT NULL,
                    category_id BIGINT NOT NULL,
                    bucket_type VARCHAR NOT NULL,
                    bucket_start TIMESTAMPTZ NOT NULL,
                    bucket_end TIMESTAMPTZ NOT NULL,
                    total_sales_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
                    total_units_sold BIGINT NOT NULL DEFAULT 0,
                    order_count BIGINT NOT NULL DEFAULT 0,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (id)
                )
            """)
            
            # Create processed_events table (tracks processed orders for idempotency)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_events (
                    order_id BIGINT PRIMARY KEY,
                    processed_at TIMESTAMPTZ NOT NULL
                )
            """)
            
            # Create category_sales_forecast table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS category_sales_forecast (
                    id BIGINT,
                    merchant_id BIGINT NOT NULL,
                    category_id BIGINT NOT NULL,
                    model_name VARCHAR NOT NULL,
                    generated_at TIMESTAMPTZ NOT NULL,
                    forecast_horizon INTEGER NOT NULL,
                    forecasted_values VARCHAR NOT NULL,
                    mae DOUBLE,
                    PRIMARY KEY (id)
                )
            """)
            
            # Create sequences for auto-increment
            try:
                conn.execute("CREATE SEQUENCE IF NOT EXISTS category_sales_agg_id_seq START 1")
            except Exception:
                pass  # Sequence may already exist
            
            try:
                conn.execute("CREATE SEQUENCE IF NOT EXISTS category_sales_forecast_id_seq START 1")
            except Exception:
                pass  # Sequence may already exist
            
        logger.info("DuckDB schema initialized successfully")
    
    def health_check(self) -> dict:
        """
        Check DuckDB health and return status info.
        """
        try:
            with self.get_connection(read_only=True) as conn:
                # Check if tables exist
                tables = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()
                
                table_names = [t[0] for t in tables]
                
                # Get row counts
                counts = {}
                for table in ['category_sales_agg', 'processed_events', 'category_sales_forecast']:
                    if table in table_names:
                        result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                        counts[table] = result[0] if result else 0
                
                return {
                    "status": "UP",
                    "database": self.db_path,
                    "tables": table_names,
                    "row_counts": counts
                }
        except Exception as e:
            logger.error(f"DuckDB health check failed: {e}")
            return {
                "status": "DOWN",
                "database": self.db_path,
                "error": str(e)
            }


# Convenience function for getting the singleton client
def get_duckdb_client() -> DuckDBClient:
    """Get the singleton DuckDB client instance."""
    return DuckDBClient.get_instance()
