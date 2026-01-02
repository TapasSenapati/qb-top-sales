import logging
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict
from enum import Enum
from contextlib import asynccontextmanager
import os

from . import db
from .service import ForecastingService, CategoryForecastResult, compute_confidence # Import compute_confidence
from .consul_registration import register_service, deregister_service
from .evaluate_models import evaluate_models
from .postgres_client import get_postgres_client

logger = logging.getLogger(__name__)

class CategoryForecastResponse(BaseModel):
    category_id: int = Field(..., example=101)
    category_name: str = Field(..., example="Beverages")
    forecast_value: float = Field(..., example=1234.56)
    model: str = Field(..., example="rolling")
    lookback: int = Field(..., example=4)      # Re-added
    confidence: str = Field(..., example="MEDIUM") # Re-added


class ForecastResponse(BaseModel):
    forecasts: List[CategoryForecastResponse]
    messages: List[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify Postgres connectivity on startup
    try:
        pg_client = get_postgres_client()
        health = pg_client.health_check()
        if health["status"] == "UP":
            logger.info("PostgreSQL connection verified successfully")
        else:
            logger.warning(f"PostgreSQL health check returned: {health}")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
    
    register_service()
    yield
    deregister_service()


app = FastAPI(
    title="Forecasting Service API",
    description="Endpoints to forecast next-period sales across categories.",
    version="1.0.0",
    lifespan=lifespan,
)

# --- Instrumentation ---
from opentelemetry import trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

# 1. Setup Zipkin Exporter with environment variable
ZIPKIN_ENDPOINT = os.getenv("ZIPKIN_ENDPOINT", "http://zipkin:9411/api/v2/spans")
resource = Resource.create({"service.name": "forecasting-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
zipkin_exporter = ZipkinExporter(endpoint=ZIPKIN_ENDPOINT)
span_processor = BatchSpanProcessor(zipkin_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# 2. Instrument FastAPI for Tracing
FastAPIInstrumentor.instrument_app(app)

# 3. Instrument FastAPI for Prometheus Metrics (/metrics)
Instrumentator().instrument(app).expose(app)


# --- UI Static Files ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class ForecastModelName(str, Enum):
    rolling = "rolling"
    wma = "wma"
    ses = "ses"
    snaive = "snaive"


forecasting_service = ForecastingService()


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health", tags=["health"], summary="Service health")
def health():
    return {"status": "UP"}


@app.get("/health/postgres", tags=["health"], summary="PostgreSQL health")
def postgres_health():
    """Check PostgreSQL database connection status."""
    client = get_postgres_client()
    return client.health_check()


@app.get(
    "/forecast/top-categories",
    response_model=ForecastResponse,
    tags=["forecast"],
    summary="Real-time forecast generation",
    description="Generate forecasts on-the-fly for top N categories. Use this for real-time predictions with custom model/lookback. Slower than compare-models but uses live data.",
)
def forecast_top_categories(
    merchant_id: int = Query(..., description="Merchant identifier", examples={"default": {"value": 1}}),
    bucket_type: str = Query(..., regex="^(DAY|WEEK|MONTH)$", description="Aggregation bucket type", examples={"day": {"value": "DAY"}}),
    model: ForecastModelName = Query(ForecastModelName.rolling, description="Forecasting model", examples={"rolling": {"value": "rolling"}, "wma": {"value": "wma"}, "ses": {"value": "ses"}, "snaive": {"value": "snaive"}}),
    lookback: int = Query(4, ge=1, le=12, description="Rolling window lookback", examples={"default": {"value": 4}}),
    limit: int = Query(5, ge=1, le=20, description="Max number of categories to return", examples={"default": {"value": 5}}),
):
    # This endpoint still calculates on-demand, which could be a future improvement.
    logger.info(f"Received /forecast/top-categories request for merchant_id={merchant_id}, bucket_type={bucket_type}, model={model}, lookback={lookback}, limit={limit}")
    category_series, category_names = db.fetch_category_time_series(
        merchant_id=merchant_id,
        bucket_type=bucket_type
    )

    try:
        result = forecasting_service.forecast_categories(
            merchant_id=merchant_id,
            category_series=category_series,
            category_names=category_names,
            bucket_type=bucket_type,
            model=model.value,
            lookback=lookback,
            limit=limit
        )
        return ForecastResponse(forecasts=[
            CategoryForecastResponse(
                category_id=f.category_id,
                category_name=f.category_name,
                model=f.model,
                forecast_value=f.forecast_value,
                lookback=f.lookback,
                confidence=f.confidence
            ) for f in result.forecasts
        ], messages=result.messages)
    except Exception as e:
        logger.error(f"Error processing /forecast/top-categories request: {e}", exc_info=True)
        raise

@app.get(
    "/forecast/compare-models",
    response_model=ForecastResponse,
    tags=["forecast"],
    summary="Pre-computed forecast lookup (fast)",
    description="Fetch the latest pre-computed forecasts from the database. These are generated by the forecasting-worker every 60 seconds. Use this for dashboard displays and quick lookups.",
)
def compare_models(
    merchant_id: int = Query(..., description="Merchant identifier", examples={"default": {"value": 1}}),
    limit: int = Query(5, ge=1, le=20, description="Max number of categories to return", examples={"default": {"value": 5}}),
):
    logger.info(f"Received /forecast/compare-models request for merchant_id={merchant_id}, limit={limit}")
    latest_forecasts = db.fetch_latest_forecasts(merchant_id, limit)

    if not latest_forecasts:
        return ForecastResponse(forecasts=[], messages=["No pre-computed forecasts found for this merchant."])

    all_forecasts = []
    # Hardcode lookback for now as worker uses fixed value
    fixed_lookback = 4
    fixed_confidence = compute_confidence(fixed_lookback)

    for forecast_row in latest_forecasts:
        # The pre-computed forecast values are a list of dicts.
        # For this API, we'll just take the first predicted value.
        forecast_values = forecast_row['forecasted_values']
        first_forecast_value = forecast_values[0]['value'] if forecast_values else 0.0

        all_forecasts.append(
            CategoryForecastResponse(
                category_id=forecast_row['category_id'],
                category_name=forecast_row['category_name'],
                model=forecast_row['model_name'],
                forecast_value=first_forecast_value,
                lookback=fixed_lookback,    # Injected
                confidence=fixed_confidence # Injected
            )
        )
    
    generated_at = latest_forecasts[0]['generated_at'].isoformat() if latest_forecasts else 'N/A'
    messages = [f"Displaying latest forecasts generated at {generated_at} UTC."]

    return ForecastResponse(forecasts=all_forecasts, messages=messages)


@app.get(
    "/evaluate-models",
    response_model=Dict[str, Dict],
    tags=["evaluation"],
    summary="Model accuracy evaluation (slowest)",
    description="Run walk-forward validation to compare model accuracy. Returns MAE/RMSE metrics per model. Use this for model selection and accuracy analysis.",
)
def run_evaluation(
    merchant_id: int = Query(..., description="Merchant identifier", examples={"default": {"value": 1}}),
    bucket_type: str = Query(..., regex="^(DAY|WEEK|MONTH)$", description="Aggregation bucket type", examples={"day": {"value": "DAY"}}),
    test_points: int = Query(5, ge=1, le=20, description="Number of test points for validation"),
):
    try:
        return evaluate_models(
            merchant_id=merchant_id,
            bucket_type=bucket_type,
            test_points=test_points
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


