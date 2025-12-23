"""
Database module for forecasting service.

Data sources:
- DuckDB: Analytics data (category_sales_agg, processed_events, category_sales_forecast)
- PostgreSQL: Catalog data (ingestion.categories for category names)
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Tuple
from datetime import datetime

from .service import TimeSeriesPoint
from .duckdb_client import get_duckdb_client

logger = logging.getLogger(__name__)

# PostgreSQL config - used only for catalog lookups
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "qb_db")
DB_USER = os.getenv("DB_USER", "qb_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "qb_password")


def _get_postgres_connection():
    """Get a PostgreSQL connection for catalog lookups."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def _get_category_names_from_postgres(category_ids: List[int]) -> Dict[int, str]:
    """
    Fetch category names from PostgreSQL (catalog data).
    """
    if not category_ids:
        return {}
    
    placeholders = ','.join(['%s'] * len(category_ids))
    sql = f"SELECT id, name FROM ingestion.categories WHERE id IN ({placeholders})"
    
    conn = _get_postgres_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(category_ids))
        rows = cur.fetchall()
        return {row[0]: row[1] for row in rows}
    finally:
        conn.close()


def fetch_category_time_series(
    merchant_id: int,
    bucket_type: str
) -> Tuple[Dict[int, List[TimeSeriesPoint]], Dict[int, str]]:
    """
    Fetch time series data for all categories of a merchant.
    
    - Aggregation data: from DuckDB
    - Category names: from PostgreSQL
    """
    client = get_duckdb_client()
    
    # Query DuckDB for aggregation data
    sql = """
        SELECT
            category_id,
            bucket_start,
            total_sales_amount
        FROM category_sales_agg
        WHERE merchant_id = ?
          AND bucket_type = ?
        ORDER BY category_id, bucket_start
    """
    
    with client.get_connection(read_only=True) as conn:
        rows = conn.execute(sql, [merchant_id, bucket_type]).fetchall()
    
    if not rows:
        return {}, {}
    
    # Build time series
    series: Dict[int, List[TimeSeriesPoint]] = {}
    category_ids = set()
    
    for category_id, bucket_start, value in rows:
        category_ids.add(category_id)
        series.setdefault(category_id, []).append(
            TimeSeriesPoint(
                bucket_start=bucket_start,
                value=float(value)
            )
        )
    
    # Fetch category names from PostgreSQL
    category_names = _get_category_names_from_postgres(list(category_ids))
    
    return series, category_names


def get_distinct_merchants() -> List[int]:
    """
    Returns a list of all unique merchant_ids from the sales aggregation table.
    Data source: DuckDB
    """
    client = get_duckdb_client()
    
    with client.get_connection(read_only=True) as conn:
        rows = conn.execute("SELECT DISTINCT merchant_id FROM category_sales_agg").fetchall()
    
    return [row[0] for row in rows]


def save_forecast_results(
    merchant_id: int,
    all_models_results: Dict,
    category_names: Dict[int, str],
    generated_at: datetime,
    forecast_horizon: int
):
    """
    Saves a complete set of forecast results for a merchant.
    Deletes old forecasts first, then inserts new ones.
    Data source: DuckDB
    """
    client = get_duckdb_client()
    
    with client.get_connection() as conn:
        # Delete all previous forecasts for this merchant
        conn.execute("DELETE FROM category_sales_forecast WHERE merchant_id = ?", [merchant_id])
        
        # Insert new forecasts
        for category_id, results in all_models_results.items():
            for model_name, forecast in results['models'].items():
                if forecast.forecast is not None:
                    # Convert forecast points to JSON string
                    forecast_values = json.dumps([
                        {'bucket_start': p.bucket_start.isoformat(), 'value': p.value}
                        for p in forecast.forecast
                    ])
                    
                    conn.execute("""
                        INSERT INTO category_sales_forecast (
                            id, merchant_id, category_id, model_name, generated_at,
                            forecast_horizon, forecasted_values, mae
                        ) VALUES (
                            nextval('category_sales_forecast_id_seq'), ?, ?, ?, ?, ?, ?, ?
                        )
                    """, [
                        merchant_id,
                        category_id,
                        model_name,
                        generated_at,
                        forecast_horizon,
                        forecast_values,
                        forecast.mae
                    ])
        
        logger.info(f"Saved forecasts for merchant {merchant_id} to DuckDB")


def fetch_latest_forecasts(merchant_id: int, limit: int) -> List[Dict]:
    """
    Fetches the most recently generated forecast for a given merchant.
    
    - Forecast data: from DuckDB
    - Category names: from PostgreSQL
    """
    client = get_duckdb_client()
    
    # Query DuckDB for forecast data
    sql = """
        WITH latest_forecast AS (
            SELECT MAX(generated_at) AS max_generated_at
            FROM category_sales_forecast
            WHERE merchant_id = ?
        )
        SELECT
            f.category_id,
            f.model_name,
            f.generated_at,
            f.forecasted_values,
            f.mae
        FROM category_sales_forecast f, latest_forecast lf
        WHERE f.merchant_id = ?
          AND f.generated_at = lf.max_generated_at
        ORDER BY f.category_id, f.model_name
    """
    
    with client.get_connection(read_only=True) as conn:
        rows = conn.execute(sql, [merchant_id, merchant_id]).fetchall()
    
    if not rows:
        return []
    
    # Get category IDs for name lookup
    category_ids = list(set(row[0] for row in rows))
    category_names = _get_category_names_from_postgres(category_ids)
    
    # Build result list
    results = []
    for row in rows:
        category_id, model_name, generated_at, forecasted_values_str, mae = row
        
        # Parse JSON forecasted values
        try:
            forecasted_values = json.loads(forecasted_values_str) if forecasted_values_str else []
        except json.JSONDecodeError:
            forecasted_values = []
        
        results.append({
            'category_id': category_id,
            'category_name': category_names.get(category_id, str(category_id)),
            'model_name': model_name,
            'generated_at': generated_at,
            'forecasted_values': forecasted_values,
            'mae': mae
        })
    
    return results
