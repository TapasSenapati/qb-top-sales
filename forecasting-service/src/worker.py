import time
import logging

from src.scheduler import scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting forecasting worker process...")
    scheduler.start()
    logger.info("Scheduler started. Worker will now sleep indefinitely.")
    
    try:
        while True:
            time.sleep(60)  # Keep the main thread alive
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler shut down. Exiting.")
