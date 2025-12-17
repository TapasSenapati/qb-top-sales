import os
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from typing import Dict, List, Tuple
from datetime import datetime

from .service import TimeSeriesPoint


DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "qb_db")
DB_USER = os.getenv("DB_USER", "qb_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "qb_password")


def fetch_category_time_series(
    merchant_id: int,
    bucket_type: str
) -> Tuple[Dict[int, List[TimeSeriesPoint]], Dict[int, str]]:

    sql = """
        SELECT
            csa.category_id,
            c.name AS category_name,
            csa.bucket_start,
            csa.total_sales_amount
        FROM forecasting.category_sales_agg csa
        JOIN ingestion.categories c ON c.id = csa.category_id
        WHERE csa.merchant_id = %s
          AND csa.bucket_type = %s
        ORDER BY csa.category_id, csa.bucket_start
    """

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    try:
        cur = conn.cursor()
        cur.execute(sql, (merchant_id, bucket_type))

        rows = cur.fetchall()

        series: Dict[int, List[TimeSeriesPoint]] = {}
        category_names: Dict[int, str] = {}

        for category_id, category_name, bucket_start, value in rows:
            category_names.setdefault(category_id, category_name)
            series.setdefault(category_id, []).append(
                TimeSeriesPoint(
                    bucket_start=bucket_start,
                    value=float(value)
                )
            )

        return series, category_names

    finally:
        conn.close()


def get_distinct_merchants() -> List[int]:
    """
    Returns a list of all unique merchant_ids from the sales aggregation table.
    """
    sql = "SELECT DISTINCT merchant_id FROM forecasting.category_sales_agg;"
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        cur = conn.cursor()
        cur.execute(sql)
        merchants = cur.fetchall()
        return merchants
    finally:
        conn.close()


def save_forecast_results(
    merchant_id: int,
    all_models_results: Dict,
    category_names: Dict[int, str],
    generated_at: datetime,
    forecast_horizon: int
):
    """
    Saves a complete set of forecast results for a merchant, deleting old ones first.
    This is done in a single transaction.
    """
    delete_sql = "DELETE FROM forecasting.category_sales_forecast WHERE merchant_id = %s;"
    insert_sql = """
        INSERT INTO forecasting.category_sales_forecast (
            merchant_id, category_id, model_name, generated_at, 
            forecast_horizon, forecasted_values, mae
        ) VALUES (%s, %s, %s, %s, %s, %s, %s);
    """

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        with conn.cursor() as cur:
            # Delete all previous forecasts for this merchant to make way for the new ones
            cur.execute(delete_sql, (merchant_id,))

            # Iterate over each category's results
            for category_id, results in all_models_results.items():
                # Iterate over each model's forecast for the category
                for model_name, forecast in results['models'].items():
                    if forecast.forecast is not None:
                        # Convert forecast points to a JSON-serializable list of dicts
                        forecast_values = [
                            {'bucket_start': p.bucket_start.isoformat(), 'value': p.value}
                            for p in forecast.forecast
                        ]
                        
                        cur.execute(insert_sql, (
                            merchant_id,
                            category_id,
                            model_name,
                            generated_at,
                            forecast_horizon,
                            Json(forecast_values),
                            forecast.mae
                        ))
            conn.commit()
    finally:
        conn.close()


def fetch_latest_forecasts(merchant_id: int, limit: int) -> List[Dict]:
    """
    Fetches the most recently generated forecast for a given merchant.
    """
    sql = """
        WITH latest_forecast AS (
            SELECT
                merchant_id,
                MAX(generated_at) AS max_generated_at
            FROM forecasting.category_sales_forecast
            WHERE merchant_id = %s
            GROUP BY merchant_id
        )
        SELECT
            f.category_id,
            c.name as category_name,
            f.model_name,
            f.generated_at,
            f.forecasted_values,
            f.mae
        FROM forecasting.category_sales_forecast f
        JOIN latest_forecast lf ON f.merchant_id = lf.merchant_id AND f.generated_at = lf.max_generated_at
        JOIN ingestion.categories c ON c.id = f.category_id
        WHERE f.merchant_id = %s
        ORDER BY f.category_id, f.model_name;
    """

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, (merchant_id, merchant_id))
        results = cur.fetchall()
        return results
    finally:
        conn.close()
