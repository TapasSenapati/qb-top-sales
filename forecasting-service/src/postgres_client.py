"""
Postgres client for forecasting analytics.
Singleton client for PostgreSQL database access.
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Configuration from environment (defaults match docker-compose.yml)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "qb_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "qb_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "qb_db")

class PostgresClient:
    """
    Manages connections to the PostgreSQL database.
    """
    
    _instance = None
    
    def __init__(self):
        self.dsn = f"host={POSTGRES_HOST} port={POSTGRES_PORT} user={POSTGRES_USER} password={POSTGRES_PASSWORD} dbname={POSTGRES_DB}"
        logger.info(f"Postgres client initialized for host: {POSTGRES_HOST}")
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_connection(self):
        return psycopg2.connect(self.dsn)

    @contextmanager
    def cursor(self, commit=False):
        """
        Context manager for DB cursors.
        """
        conn = self.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            yield cur
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def health_check(self) -> dict:
        try:
            with self.cursor() as cur:
                cur.execute("SELECT 1")
                return {"status": "UP", "database": "Postgres"}
        except Exception as e:
            logger.error(f"Postgres health check failed: {e}")
            return {"status": "DOWN", "error": str(e)}

def get_postgres_client() -> PostgresClient:
    return PostgresClient.get_instance()
