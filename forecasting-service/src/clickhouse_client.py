"""
ClickHouse client for forecasting analytics.
Singleton client for ClickHouse database access (analytics queries and writes).
"""

import os
import logging
import clickhouse_connect
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Configuration from environment (defaults match docker-compose.yml)
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "default")


class ClickHouseClient:
    """
    Manages connections to the ClickHouse database for analytics.
    """
    
    _instance = None
    
    def __init__(self):
        self._client = None
        logger.info(f"ClickHouse client initialized for host: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _get_client(self):
        """Lazy initialization of ClickHouse client."""
        if self._client is None:
            self._client = clickhouse_connect.get_client(
                host=CLICKHOUSE_HOST,
                port=CLICKHOUSE_PORT,
                database=CLICKHOUSE_DATABASE,
                settings={"connect_timeout": 10}
            )
        return self._client
    
    def query(self, sql: str, parameters: dict = None):
        """
        Execute a query and return results as a list of dicts.
        """
        client = self._get_client()
        result = client.query(sql, parameters=parameters)
        
        # Convert to list of dicts for compatibility with existing code
        columns = result.column_names
        rows = []
        for row in result.result_rows:
            rows.append(dict(zip(columns, row)))
        return rows
    
    def insert(self, table: str, data: list, column_names: list):
        """
        Insert data into a table.
        """
        client = self._get_client()
        client.insert(table, data, column_names=column_names)
    
    def command(self, sql: str, parameters: dict = None):
        """
        Execute a command (INSERT, UPDATE, etc.) that doesn't return results.
        """
        client = self._get_client()
        return client.command(sql, parameters=parameters)
    
    def health_check(self) -> dict:
        """Check ClickHouse connectivity."""
        try:
            client = self._get_client()
            result = client.query("SELECT version()")
            version = result.result_rows[0][0] if result.result_rows else "unknown"
            return {"status": "UP", "database": "ClickHouse", "version": version}
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return {"status": "DOWN", "error": str(e)}


def get_clickhouse_client() -> ClickHouseClient:
    """Get the singleton ClickHouse client instance."""
    return ClickHouseClient.get_instance()
