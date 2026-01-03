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
from src.clickhouse_client import get_clickhouse_client
from src.db import get_distinct_merchants

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
ch_client = get_clickhouse_client()

def run_forecast_job():
    """
    Periodic job to generate forecasts for all categories across all merchants.
    """
    with tracer.start_as_current_span("task forecast-generation"):
        logger.info("Starting scheduled forecast generation job...")
        
        try:
            # 1. Get all merchants that have aggregated sales data (from ClickHouse)
            merchant_ids = get_distinct_merchants()
            
            if not merchant_ids:
                logger.info("No merchants with data found. Skipping forecast generation.")
                return
            
            logger.info(f"Generating forecasts for {len(merchant_ids)} merchants: {merchant_ids}")
            
            # Use a single batch timestamp for all forecasts in this run
            batch_timestamp = datetime.now()
            
            total_count = 0
            for merchant_id in merchant_ids:
                # 2. Run models for this merchant
                results = service.run_all_models(merchant_id=merchant_id, category_series=None, lookback=28, limit=100)
                
                # 3. Store results in ClickHouse
                data = []
                columns = ['id', 'merchant_id', 'category_id', 'model_name', 
                           'generated_at', 'forecast_horizon', 'forecasted_values', 'mae']
                
                row_id = int(datetime.now().timestamp() * 1000000)
                
                for category_id, category_data in results.items():
                    models = category_data["models"]
                    
                    for model_name, forecast_data in models.items():
                        if forecast_data.forecast:
                            next_point = forecast_data.forecast[0]
                            value = next_point.value
                            horizon = 1
                            
                            forecast_json = json.dumps([{"date": str(next_point.bucket_start), "value": value}])
                            
                            data.append([
                                row_id,
                                merchant_id,
                                category_id,
                                model_name,
                                batch_timestamp,
                                horizon,
                                forecast_json,
                                forecast_data.mae
                            ])
                            row_id += 1
                
                if data:
                    ch_client.insert('category_sales_forecast', data, columns)
                
                total_count += len(data)
                logger.info(f"Generated {len(data)} forecasts for merchant {merchant_id}")
            
            logger.info(f"Forecast job completed. Generated {total_count} total forecast records.")

        except Exception as e:
            logger.error(f"Forecast job failed: {e}")
            # Span will automatically record exception

if __name__ == "__main__":
    # Wait for DB to be ready
    time.sleep(5) 
    
    scheduler = BlockingScheduler()
    
    # Run immediately on startup, then every 60 seconds
    scheduler.add_job(
        run_forecast_job, 
        'interval', 
        seconds=60,
        next_run_time=datetime.now(),
        misfire_grace_time=30,
        coalesce=True
    )
    
    logger.info("Forecasting Worker started. Running immediately, then every 60 seconds.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
