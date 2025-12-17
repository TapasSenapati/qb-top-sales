from typing import List, Dict, Optional, Protocol, Tuple
from dataclasses import dataclass
from datetime import datetime
from fastapi import HTTPException
import pandas as pd
import logging

# Configure logger
logger = logging.getLogger(__name__)


# ----------------------------
# Strategy contracts
# ----------------------------

class ForecastModel(Protocol):
    name: str

    def forecast(
        self,
        series: List["TimeSeriesPoint"],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Tuple[Optional[float], Optional[str]]:
        ...

# ----------------------------
# Domain models
# ----------------------------

@dataclass
class TimeSeriesPoint:
    bucket_start: datetime
    value: float

@dataclass
class CategoryForecastResult:
    category_id: int
    category_name: str
    forecast_value: float
    model: str
    lookback: int
    confidence: str

@dataclass
class ForecastResult:
    forecasts: List[CategoryForecastResult]
    messages: List[str]

# ----------------------------
# Forecasting service
# ----------------------------

def compute_confidence(lookback: int) -> str:
    if lookback <= 1:
        return "LOW"
    if lookback <= 3:
        return "MEDIUM"
    return "HIGH"

class ForecastingService:
    """
    Stateless forecasting service.
    - Uses pre-aggregated time series
    - Strategy-based model selection (rolling,wma ,etc ...)
    """
    def __init__(self, default_lookback: int = 4):
        self.default_lookback = default_lookback
        # Registry of forecasting models
        self._models: Dict[str, ForecastModel] = {
            "rolling": RollingAverageModel(),
            "wma": WeightedMovingAverageModel(),
            "ses": ExponentialSmoothingModel(),
            "snaive": SeasonalNaiveModel(),
        }
    # ---------- PUBLIC API ----------

    def forecast_categories(
        self,
        category_series: Dict[int, List[TimeSeriesPoint]],
        category_names: Dict[int, str],
        bucket_type: str,
        model: str = "rolling",
        lookback: Optional[int] = None,
        limit: int = 5
    ) -> ForecastResult:
        """
        Forecast next-period sales per category.
        """
        if not category_series:
            return ForecastResult(forecasts=[], messages=["No historical sales data found for the selected Merchant ID and Time Bucket."])

        lookback = lookback or self.default_lookback
        results: List[CategoryForecastResult] = []
        messages: List[str] = []

        model_impl = self._models.get(model)
        if not model_impl:
            available = ", ".join(self._models.keys())
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Forecasting model '{model}' is not available. "
                    f"Available models: {available}"
                )
            )

        for category_id, series in category_series.items():
            category_name = category_names.get(category_id, str(category_id))
            
            if not series:
                messages.append(f"Skipping category '{category_name}': No sales data available.")
                continue

            try:
                forecast_value, message = model_impl.forecast(
                    series=series,
                    lookback=lookback,
                    bucket_type=bucket_type,
                    category_id=category_id,
                    category_name=category_name,
                )
                if message:
                    messages.append(message)

            except Exception as e:
                logger.error(f"Prediction failed for category {category_id}: {e}")
                messages.append(f"An unexpected error occurred for category '{category_name}'.")
                continue

            if forecast_value is None:
                continue

            confidence = compute_confidence(lookback)
            results.append(
                CategoryForecastResult(
                    category_id=category_id,
                    category_name=category_name,
                    forecast_value=forecast_value,
                    model=model_impl.name,
                    lookback=lookback,
                    confidence=confidence
                )
            )
        
        if not results and not messages:
             messages.append(f"Not enough historical data to generate a forecast with the selected model ('{model}') and lookback period ({lookback}). Try a smaller lookback value or a different model.")

        # Sort by forecasted value descending
        results.sort(key=lambda r: r.forecast_value, reverse=True)
        return ForecastResult(forecasts=results[:limit], messages=messages)

# ---------- MODEL IMPLEMENTATIONS ----------

class RollingAverageModel:
    name = "rolling"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Tuple[Optional[float], Optional[str]]:
        if lookback <= 0 or len(series) < lookback:
            message = (f"Skipping category '{category_name}': "
                       f"Not enough data for 'rolling' model (needs {lookback}, has {len(series)}).")
            return None, message

        values = [p.value for p in series[-lookback:]]
        return sum(values) / lookback, None

class WeightedMovingAverageModel:
    name = "wma"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Tuple[Optional[float], Optional[str]]:
        if lookback <= 0 or len(series) < lookback:
            message = (f"Skipping category '{category_name}': "
                       f"Not enough data for 'wma' model (needs {lookback}, has {len(series)}).")
            return None, message

        values = [p.value for p in series[-lookback:]]
        weights = range(1, lookback + 1)
        
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        return weighted_sum / sum(weights), None

class ExponentialSmoothingModel:
    name = "ses"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Tuple[Optional[float], Optional[str]]:
        if len(series) < 2:
            message = (f"Skipping category '{category_name}': "
                       f"Not enough data for 'ses' model (needs at least 2 points, has {len(series)}).")
            return None, message
        
        try:
            from statsmodels.tsa.api import SimpleExpSmoothing
            
            values = [p.value for p in series]
            model = SimpleExpSmoothing(values, initialization_method="estimated").fit()
            return model.forecast(1)[0], None
        
        except ImportError:
            raise HTTPException(status_code=501, detail="Statsmodels library not installed. Cannot use 'ses' model.")
        except Exception as e:
            logger.error(f"Exponential smoothing failed for category {category_id}: {e}")
            return None, f"Error during 'ses' forecast for category '{category_name}'."

class SeasonalNaiveModel:
    name = "snaive"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Tuple[Optional[float], Optional[str]]:
        seasonal_period = self._get_seasonal_period(bucket_type)
        if seasonal_period is None:
            return None, f"Seasonal naive model ('snaive') is not applicable for bucket type '{bucket_type}'."

        if len(series) < seasonal_period:
            message = (f"Skipping category '{category_name}': Not enough data for 'snaive' "
                       f"(needs {seasonal_period} points for seasonality, has {len(series)}).")
            return None, message

        return series[-seasonal_period].value, None

    def _get_seasonal_period(self, bucket_type: str) -> Optional[int]:
        if bucket_type == "DAY":
            return 7
        if bucket_type == "WEEK":
            return 52
        if bucket_type == "MONTH":
            return 12
        return None