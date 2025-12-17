from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict
from enum import Enum
from contextlib import asynccontextmanager
import os

from .service import ForecastingService, ForecastResult, CategoryForecastResult
from .db import fetch_category_time_series
from .consul_registration import register_service, deregister_service
from .evaluate_models import evaluate_models
from dataclasses import asdict


class CategoryForecastResponse(BaseModel):
    category_id: int = Field(..., example=101)
    category_name: str = Field(..., example="Beverages")
    forecast_value: float = Field(..., example=1234.56)
    model: str = Field(..., example="rolling")
    lookback: int = Field(..., example=4)
    confidence: str = Field(..., example="MEDIUM")

class ForecastResponse(BaseModel):
    forecasts: List[CategoryForecastResponse]
    messages: List[str]


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


@app.get(
    "/forecast/top-categories",
    response_model=ForecastResponse,
    tags=["forecast"],
    summary="Forecast top categories",
    description="Forecast next-period sales per category and return the top categories.",
)
def forecast_top_categories(
    merchant_id: int = Query(..., description="Merchant identifier", examples={"default": {"value": 1}}),
    bucket_type: str = Query(..., regex="^(DAY|WEEK|MONTH)$", description="Aggregation bucket type", examples={"day": {"value": "DAY"}}),
    model: ForecastModelName = Query(ForecastModelName.rolling, description="Forecasting model", examples={"rolling": {"value": "rolling"}, "wma": {"value": "wma"}, "ses": {"value": "ses"}, "snaive": {"value": "snaive"}}),
    lookback: int = Query(4, ge=1, le=12, description="Rolling window lookback", examples={"default": {"value": 4}}),
    limit: int = Query(5, ge=1, le=20, description="Max number of categories to return", examples={"default": {"value": 5}}),
):
    category_series, category_names = fetch_category_time_series(
        merchant_id=merchant_id,
        bucket_type=bucket_type
    )

    try:
        result = forecasting_service.forecast_categories(
            category_series=category_series,
            category_names=category_names,
            bucket_type=bucket_type,
            model=model.value,
            lookback=lookback,
            limit=limit
        )
        return ForecastResponse(forecasts=[asdict(f) for f in result.forecasts], messages=result.messages)
    except Exception as e:
        raise


@app.get(
    "/forecast/compare-models",
    response_model=ForecastResponse,
    tags=["forecast"],
    summary="Compare all models for top categories",
    description="For a given category, return a forecast from each model.",
)
def compare_models(
    merchant_id: int = Query(..., description="Merchant identifier", examples={"default": {"value": 1}}),
    bucket_type: str = Query(..., regex="^(DAY|WEEK|MONTH)$", description="Aggregation bucket type", examples={"day": {"value": "DAY"}}),
    lookback: int = Query(4, ge=1, le=12, description="Rolling window lookback", examples={"default": {"value": 4}}),
    limit: int = Query(5, ge=1, le=20, description="Max number of categories to return", examples={"default": {"value": 5}}),
    models: List[str] = Query(list(ForecastModelName)),
):
    category_series, category_names = fetch_category_time_series(
        merchant_id=merchant_id,
        bucket_type=bucket_type
    )

    all_forecasts = []
    all_messages = []
    for model_name in models:
        try:
            result = forecasting_service.forecast_categories(
                category_series=category_series,
                category_names=category_names,
                bucket_type=bucket_type,
                model=model_name,
                lookback=lookback,
                limit=limit
            )
            all_forecasts.extend(result.forecasts)
            all_messages.extend(result.messages)
        except Exception:
            # In a real app, you might want to log this
            continue

    return ForecastResponse(forecasts=[asdict(f) for f in all_forecasts], messages=list(set(all_messages)))


@app.get(
    "/evaluate-models",
    response_model=Dict[str, Dict],
    tags=["evaluation"],
    summary="Evaluate all models",
    description="Run walk-forward validation and return performance metrics.",
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
