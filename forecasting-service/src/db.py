import os
import psycopg2
from typing import Dict, List
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
) -> Dict[int, List[TimeSeriesPoint]]:

    sql = """
        SELECT
            category_id,
            bucket_start,
            total_sales_amount
        FROM forecasting.category_sales_agg
        WHERE merchant_id = %s
          AND bucket_type = %s
        ORDER BY category_id, bucket_start
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

        for category_id, bucket_start, value in rows:
            series.setdefault(category_id, []).append(
                TimeSeriesPoint(
                    bucket_start=bucket_start,
                    value=float(value)
                )
            )

        return series

    finally:
        conn.close()
