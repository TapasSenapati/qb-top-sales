from typing import List, Dict, Optional, Protocol
from dataclasses import dataclass
from datetime import datetime
from fastapi import HTTPException
import pandas as pd
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Prophet is imported lazily inside forecasting to avoid import cost when not used.
MIN_POINTS_FOR_PROPHET = 3
# Feature flags
ENABLE_PROPHET = True

class ProphetNotAvailableError(Exception):
    pass

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
    ) -> Optional[float]:
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
    - Strategy-based model selection (rolling, prophet, ...)
    """
    def __init__(self, default_lookback: int = 4):
        self.default_lookback = default_lookback
        # Registry of forecasting models
        self._models: Dict[str, ForecastModel] = {
            "rolling": RollingAverageModel(),
            "wma": WeightedMovingAverageModel(),
            "ses": ExponentialSmoothingModel(),
        }
        if ENABLE_PROPHET:
            self._models["prophet"] = ProphetModel()
    # ---------- PUBLIC API ----------

    def forecast_categories(
        self,
        category_series: Dict[int, List[TimeSeriesPoint]],
        category_names: Dict[int, str],
        bucket_type: str,
        model: str = "rolling",
        lookback: Optional[int] = None,
        limit: int = 5
    ) -> List[CategoryForecastResult]:
        """
        Forecast next-period sales per category.
        """
        lookback = lookback or self.default_lookback
        results: List[CategoryForecastResult] = []

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
            
            # Skip if not enough data in general
            if not series:
                print(f"[forecasting] Skipping category {category_id}: empty series")
                continue

            try:
                forecast_value = model_impl.forecast(
                    series=series,
                    lookback=lookback,
                    bucket_type=bucket_type,
                    category_id=category_id,
                    category_name=category_name,
                )
            except ProphetNotAvailableError as e:
                # Re-raise to be handled by controller (400 Bad Request)
                raise e
            except Exception as e:
                logger.error(f"Prediction failed for category {category_id}: {e}")
                continue

            if forecast_value is None:
                # Model decided to skip (e.g., insufficient history)
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

        # Sort by forecasted value descending
        results.sort(key=lambda r: r.forecast_value, reverse=True)
        return results[:limit]

# ---------- MODEL IMPLEMENTATIONS ----------

@staticmethod
def _freq_for_bucket(bucket_type: str) -> str:
    if bucket_type == "DAY":
        return "D"
    if bucket_type == "WEEK":
        return "W"
    if bucket_type == "MONTH":
        return "MS"
    return "D"

class RollingAverageModel:
    name = "rolling"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Optional[float]:
        if lookback <= 0 or len(series) < lookback:
            print(
                f"[forecasting:rolling] Skipping category {category_id}: "
                f"only {len(series)} points, need {lookback}"
            )
            return None

        values = [p.value for p in series[-lookback:]]
        return sum(values) / lookback

class WeightedMovingAverageModel:
    name = "wma"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Optional[float]:
        if lookback <= 0 or len(series) < lookback:
            print(
                f"[forecasting:wma] Skipping category {category_id}: "
                f"only {len(series)} points, need {lookback}"
            )
            return None

        values = [p.value for p in series[-lookback:]]
        weights = range(1, lookback + 1)
        
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        return weighted_sum / sum(weights)

class ExponentialSmoothingModel:
    name = "ses"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Optional[float]:
        if len(series) < 2:
            print(
                f"[forecasting:ses] Skipping category {category_id}: "
                f"only {len(series)} points, need at least 2 for SES"
            )
            return None
        
        try:
            from statsmodels.tsa.api import SimpleExpSmoothing
            
            values = [p.value for p in series]
            model = SimpleExpSmoothing(values, initialization_method="estimated").fit()
            return model.forecast(1)[0]
        
        except ImportError:
            raise HTTPException(status_code=501, detail="Statsmodels library not installed. Cannot use 'ses' model.")
        except Exception as e:
            logger.error(f"Exponential smoothing failed for category {category_id}: {e}")
            return None

class ProphetModel:
    name = "prophet"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Optional[float]:
        if len(series) < MIN_POINTS_FOR_PROPHET:
            print(
                f"[forecasting:prophet] Skipping category {category_id}: "
                f"only {len(series)} points, need at least {MIN_POINTS_FOR_PROPHET} for Prophet"
            )
            return None

        # Map bucket_type to Prophet frequency
        if bucket_type == "DAY":
            freq = "D"
        elif bucket_type == "WEEK":
            freq = "W"
        elif bucket_type == "MONTH":
            freq = "MS"
        else:
            freq = "D"

        try:
            from prophet import Prophet
            
            df = pd.DataFrame({
                "ds": [p.bucket_start for p in series],
                "y": [p.value for p in series],
            })

            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=False,
                daily_seasonality=False
            )
            
            model.fit(df)
            future = model.make_future_dataframe(periods=1, freq=freq)
            forecast = model.predict(future)
            
            return float(forecast.iloc[-1]["yhat"])

        except ImportError:
             raise ProphetNotAvailableError("Prophet library not installed.")
        except Exception as e:
            # Catch backend initialization errors (like stan_backend)
            raise ProphetNotAvailableError(f"Prophet initialization failed: {str(e)}") from e
