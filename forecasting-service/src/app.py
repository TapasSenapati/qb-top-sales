from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import List
from contextlib import asynccontextmanager

from .service import ForecastingService
from .db import fetch_category_time_series
from .consul_registration import register_service, deregister_service


class CategoryForecastResponse(BaseModel):
    category_id: int = Field(..., example=101)
    forecast_value: float = Field(..., example=1234.56)
    model: str = Field(..., example="rolling")
    lookback: int = Field(..., example=4)
    confidence: str = Field(..., example="MEDIUM")


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_service()
    yield
    deregister_service()


app = FastAPI(
    title="Forecasting Service API",
    description="Endpoints to forecast next-period sales across categories.",
    version="1.0.0",
    lifespan=lifespan,
)

forecasting_service = ForecastingService()


@app.get("/health", tags=["health"], summary="Service health")
def health():
    return {"status": "UP"}


@app.get(
    "/forecast/top-categories",
    response_model=List[CategoryForecastResponse],
    tags=["forecast"],
    summary="Forecast top categories",
    description="Forecast next-period sales per category and return the top categories.",
)
def forecast_top_categories(
    merchant_id: int = Query(..., description="Merchant identifier", examples={"default": {"value": 1}}),
    bucket_type: str = Query(..., regex="^(DAY|WEEK|MONTH)$", description="Aggregation bucket type", examples={"day": {"value": "DAY"}}),
    model: str = Query("rolling", regex="^(rolling|prophet)$", description="Forecasting model", examples={"rolling": {"value": "rolling"}, "prophet": {"value": "prophet"}}),
    lookback: int = Query(4, ge=1, le=12, description="Rolling window lookback", examples={"default": {"value": 4}}),
    limit: int = Query(5, ge=1, le=20, description="Max number of categories to return", examples={"default": {"value": 5}}),
):
    """
    Example response:
    [
      {
        "category_id": 101,
        "forecast_value": 1234.56,
        "model": "rolling",
        "lookback": 4,
        "confidence": "MEDIUM"
      },
      {
        "category_id": 102,
        "forecast_value": 987.65,
        "model": "rolling",
        "lookback": 4,
        "confidence": "MEDIUM"
      }
    ]
    """
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
