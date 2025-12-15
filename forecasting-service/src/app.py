from fastapi import FastAPI, Query
from contextlib import asynccontextmanager

from .service import ForecastingService
from .db import fetch_category_time_series
from .consul_registration import register_service, deregister_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_service()
    yield
    deregister_service()


app = FastAPI(lifespan=lifespan)

forecasting_service = ForecastingService()


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/forecast/top-categories")
def forecast_top_categories(
    merchant_id: int,
    bucket_type: str = Query(..., regex="^(DAY|WEEK|MONTH)$"),
    model: str = Query("rolling", regex="^(rolling|prophet)$"),
    lookback: int = Query(4, ge=1, le=12), # add stricter lookback for production
    limit: int = Query(5, ge=1, le=20),
):
    category_series = fetch_category_time_series(
        merchant_id=merchant_id,
        bucket_type=bucket_type
    )

    return forecasting_service.forecast_categories(
        category_series=category_series,
        model=model,
        lookback=lookback,
        limit=limit
    )
