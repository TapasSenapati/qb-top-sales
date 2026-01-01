import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from . import db
from . import service as forecast_service_module # Use forecast_service_module to avoid name clash with instance


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create a single instance of the service to use in the job
forecasting_service = forecast_service_module.ForecastingService()


def run_forecast_job():
    """
    This job runs periodically to pre-compute forecasts for all merchants.
    """
    logger.info("Scheduler triggered. Running forecast job.")
    try:
        # 1. Get all merchants that have sales data
        merchants = db.get_distinct_merchants()
        logger.info(f"Found {len(merchants)} merchants to process.")

        if not merchants:
            logger.info("No merchants found in aggregation table. Job will sleep.")
            return

        for merchant_id in merchants:
            logger.info(f"Processing forecasts for merchant_id: {merchant_id}")

            # 2. For each merchant, get the daily time series data
            bucket_type = 'DAY'
            series, category_names = db.fetch_category_time_series(merchant_id, bucket_type)

            if not series:
                logger.info(f"No sales data found for merchant_id: {merchant_id}. Skipping.")
                continue

            # 3. Run all forecasting models
            lookback = 4
            limit = 5
            all_models_results = forecasting_service.run_all_models(series, lookback, limit)

            # 4. Store the results in the new forecast table
            generated_at = datetime.now()
            db.save_forecast_results(
                merchant_id,
                all_models_results,
                category_names,
                generated_at,
                limit
            )
            logger.info(f"Successfully saved forecasts for merchant_id: {merchant_id}")

    except Exception as e:
        logger.error(f"Error during forecast job: {e}", exc_info=True)

    logger.info("Forecast pre-computation job finished.")


# Scheduler setup
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_forecast_job, 'interval', minutes=1, misfire_grace_time=60)





