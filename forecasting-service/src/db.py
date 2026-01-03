"""
Database module for forecasting service.

Data sources:
- ClickHouse: Analytics data (category_sales_agg, category_sales_forecast)
- PostgreSQL: Catalog data (ingestion.categories for category names)
"""

import os
import json
import logging
from typing import Dict, List, Tuple
from datetime import datetime
from opentelemetry import trace

from .service import TimeSeriesPoint
from .postgres_client import get_postgres_client
from .clickhouse_client import get_clickhouse_client

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def _get_category_names_from_postgres(category_ids: List[int]) -> Dict[int, str]:
    """
    Fetch category names from PostgreSQL (catalog data).
    Category names stay in PostgreSQL as part of the OLTP catalog.
    """
    if not category_ids:
        return {}
    
    with tracer.start_as_current_span("db.get_category_names") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.operation", "SELECT")
        span.set_attribute("category_count", len(category_ids))
        
        client = get_postgres_client()
        placeholders = ','.join(['%s'] * len(category_ids))
        sql = f"SELECT id, name FROM ingestion.categories WHERE id IN ({placeholders})"
        
        with client.cursor() as cur:
            cur.execute(sql, tuple(category_ids))
            rows = cur.fetchall()
            return {row['id']: row['name'] for row in rows}


def fetch_category_time_series(
    merchant_id: int,
    bucket_type: str
) -> Tuple[Dict[int, List[TimeSeriesPoint]], Dict[int, str]]:
    """
    Fetch time series data for all categories of a merchant.
    
    Data source: ClickHouse (category_sales_agg)
    """
    with tracer.start_as_current_span("db.fetch_category_time_series") as span:
        span.set_attribute("db.system", "clickhouse")
        span.set_attribute("db.operation", "SELECT")
        span.set_attribute("merchant_id", merchant_id)
        span.set_attribute("bucket_type", bucket_type)
        
        ch_client = get_clickhouse_client()
        
        # Use FINAL to get deduplicated results from ReplacingMergeTree
        sql = """
            SELECT
                category_id,
                bucket_start,
                total_sales_amount
            FROM category_sales_agg FINAL
            WHERE merchant_id = %(merchant_id)s
              AND bucket_type = %(bucket_type)s
            ORDER BY category_id, bucket_start
        """
        
        rows = ch_client.query(sql, {"merchant_id": merchant_id, "bucket_type": bucket_type})
        span.set_attribute("row_count", len(rows))
    
    if not rows:
        return {}, {}
    
    # Build time series
    series: Dict[int, List[TimeSeriesPoint]] = {}
    category_ids = set()
    
    for row in rows:
        category_id = row['category_id']
        category_ids.add(category_id)
        series.setdefault(category_id, []).append(
            TimeSeriesPoint(
                bucket_start=row['bucket_start'],
                value=float(row['total_sales_amount'])
            )
        )
    
    # Fetch category names from PostgreSQL (catalog stays in OLTP)
    category_names = _get_category_names_from_postgres(list(category_ids))
    
    return series, category_names


def get_distinct_merchants() -> List[int]:
    """
    Returns a list of all unique merchant_ids from the sales aggregation table.
    Data source: ClickHouse
    """
    with tracer.start_as_current_span("db.get_distinct_merchants") as span:
        span.set_attribute("db.system", "clickhouse")
        span.set_attribute("db.operation", "SELECT")
        
        ch_client = get_clickhouse_client()
        
        rows = ch_client.query("SELECT DISTINCT merchant_id FROM category_sales_agg FINAL")
        span.set_attribute("merchant_count", len(rows))
    
    return [row['merchant_id'] for row in rows]


def save_forecast_results(
    merchant_id: int,
    all_models_results: Dict,
    category_names: Dict[int, str],
    generated_at: datetime,
    forecast_horizon: int
):
    """
    Saves a complete set of forecast results for a merchant.
    Data source: ClickHouse (category_sales_forecast)
    
    Note: ClickHouse doesn't support DELETE in the same way as PostgreSQL.
    We insert new rows and can clean up old ones via TTL or scheduled jobs.
    """
    with tracer.start_as_current_span("db.save_forecast_results") as span:
        span.set_attribute("db.system", "clickhouse")
        span.set_attribute("db.operation", "INSERT")
        span.set_attribute("merchant_id", merchant_id)
        
        ch_client = get_clickhouse_client()
        
        # Prepare batch data for insert
        data = []
        columns = ['id', 'merchant_id', 'category_id', 'model_name', 
                   'generated_at', 'forecast_horizon', 'forecasted_values', 'mae']
        
        row_id = int(datetime.now().timestamp() * 1000000)  # Simple ID generation
        
        for category_id, results in all_models_results.items():
            for model_name, forecast in results['models'].items():
                if forecast.forecast is not None:
                    # Convert forecast points to JSON string
                    forecast_values = json.dumps([
                        {'bucket_start': p.bucket_start.isoformat(), 'value': p.value}
                        for p in forecast.forecast
                    ])
                    
                    data.append([
                        row_id,
                        merchant_id,
                        category_id,
                        model_name,
                        generated_at,
                        forecast_horizon,
                        forecast_values,
                        forecast.mae
                    ])
                    row_id += 1
        
        if data:
            ch_client.insert('category_sales_forecast', data, columns)
        
        logger.info(f"Saved {len(data)} forecasts for merchant {merchant_id} to ClickHouse")


def fetch_latest_forecasts(merchant_id: int, limit: int) -> List[Dict]:
    """
    Fetches the most recently generated forecast for a given merchant.
    
    Data source: ClickHouse (category_sales_forecast)
    """
    ch_client = get_clickhouse_client()
    
    # ClickHouse query to get latest forecasts
    sql = """
        WITH latest_forecast AS (
            SELECT max(generated_at) AS max_generated_at
            FROM category_sales_forecast
            WHERE merchant_id = %(merchant_id)s
        )
        SELECT
            f.category_id,
            f.model_name,
            f.generated_at,
            f.forecasted_values,
            f.mae
        FROM category_sales_forecast f, latest_forecast lf
        WHERE f.merchant_id = %(merchant_id)s
          AND f.generated_at = lf.max_generated_at
        ORDER BY f.category_id, f.model_name
    """
    
    rows = ch_client.query(sql, {"merchant_id": merchant_id})
    
    if not rows:
        return []
    
    # Get category IDs for name lookup from PostgreSQL
    category_ids = list(set(row['category_id'] for row in rows))
    category_names = _get_category_names_from_postgres(category_ids)
    
    # Build result list
    results = []
    for row in rows:
        # Parse JSON forecasted values
        forecasted_values_str = row['forecasted_values']
        try:
            forecasted_values = json.loads(forecasted_values_str) if forecasted_values_str else []
        except json.JSONDecodeError:
            forecasted_values = []
        
        results.append({
            'category_id': row['category_id'],
            'category_name': category_names.get(row['category_id'], str(row['category_id'])),
            'model_name': row['model_name'],
            'generated_at': row['generated_at'],
            'forecasted_values': forecasted_values,
            'mae': row['mae']
        })
    
    return results
