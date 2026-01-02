import time
import os
import logging
import json
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.sdk.resources import Resource

from src.service import ForecastingService
from src.postgres_client import get_postgres_client

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenTelemetry with environment variable
ZIPKIN_ENDPOINT = os.getenv("ZIPKIN_ENDPOINT", "http://zipkin:9411/api/v2/spans")
resource = Resource.create({"service.name": "forecasting-worker"})
trace.set_tracer_provider(TracerProvider(resource=resource))
zipkin_exporter = ZipkinExporter(endpoint=ZIPKIN_ENDPOINT)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(zipkin_exporter))
tracer = trace.get_tracer(__name__)

# Initialize Service & DB
service = ForecastingService()
pg_client = get_postgres_client()

def run_forecast_job():
    """
    Periodic job to generate forecasts for all categories across all merchants.
    """
    with tracer.start_as_current_span("task forecast-generation"):
        logger.info("Starting scheduled forecast generation job...")
        
        try:
            # 1. Get all merchants that have aggregated sales data
            from src.db import get_distinct_merchants
            merchant_ids = get_distinct_merchants()
            
            if not merchant_ids:
                logger.info("No merchants with data found. Skipping forecast generation.")
                return
            
            logger.info(f"Generating forecasts for {len(merchant_ids)} merchants: {merchant_ids}")
            
            # Use a single batch timestamp for all forecasts in this run
            # This ensures compare-models can retrieve all forecasts from the same batch
            batch_timestamp = datetime.now()
            
            total_count = 0
            for merchant_id in merchant_ids:
                # 2. Run models for this merchant
                # We look back 28 days (4 weeks) to get a good trend
                results = service.run_all_models(merchant_id=merchant_id, category_series=None, lookback=28, limit=100)
                
                # 3. Store results in Postgres
                with pg_client.cursor(commit=True) as cur:
                    count = 0
                    for category_id, category_data in results.items():
                        models = category_data["models"]
                        
                        for model_name, forecast_data in models.items():
                            if forecast_data.forecast:
                                # We only store the first point for now (1-day forecast)
                                next_point = forecast_data.forecast[0]
                                value = next_point.value
                                horizon = 1
                                
                                # Simple serialization of the value
                                forecast_json = json.dumps([{"date": str(next_point.bucket_start), "value": value}])
                                
                                cur.execute("""
                                    INSERT INTO forecasting.category_sales_forecast 
                                    (merchant_id, category_id, model_name, generated_at, forecast_horizon, forecasted_values, mae)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    merchant_id,
                                    category_id,
                                    model_name,
                                    batch_timestamp,  # Use consistent batch timestamp
                                    horizon,
                                    forecast_json,
                                    forecast_data.mae
                                ))
                                count += 1
                    
                    total_count += count
                    logger.info(f"Generated {count} forecasts for merchant {merchant_id}")
            
            logger.info(f"Forecast job completed. Generated {total_count} total forecast records.")

        except Exception as e:
            logger.error(f"Forecast job failed: {e}")
            # Span will automatically record exception

if __name__ == "__main__":
    # Wait for DB to be ready (reduced from 10s since depends_on waits for healthy)
    time.sleep(5) 
    
    scheduler = BlockingScheduler()
    
    # Run immediately on startup, then every 60 seconds
    # The next_run_time=datetime.now() ensures immediate first execution
    scheduler.add_job(
        run_forecast_job, 
        'interval', 
        seconds=60,
        next_run_time=datetime.now(),  # Run immediately!
        misfire_grace_time=30,  # Allow job to run up to 30s late
        coalesce=True  # If multiple runs were missed, only run once
    )
    
    logger.info("Forecasting Worker started. Running immediately, then every 60 seconds.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
