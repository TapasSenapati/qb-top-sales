from typing import List, Dict, Optional, Protocol, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from fastapi import HTTPException
import pandas as pd
import logging
from .postgres_client import get_postgres_client
from .clickhouse_client import get_clickhouse_client

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
class ModelForecast:
    forecast: Optional[List[TimeSeriesPoint]]
    mae: Optional[float]


@dataclass
class ForecastResult:
    forecasts: List[CategoryForecastResult]
    messages: List[str]


def compute_confidence(lookback: int) -> str:
    if lookback <= 1:
        return "LOW"
    if lookback <= 3:
        return "MEDIUM"
    return "HIGH"


# Minimum data points required for each model
MODEL_DATA_REQUIREMENTS = {
    "rolling": 4,
    "wma": 4,
    "ses": 4,
    "arima": 10,
    "snaive": 52,  # Needs 1 year of data for seasonal patterns
}



class ForecastingService:
    """
    Stateless forecasting service.
    - Uses pre-aggregated time series from ClickHouse
    - Strategy-based model selection
    """
    def __init__(self, default_lookback: int = 4):
        self.default_lookback = default_lookback
        self.ch_client = get_clickhouse_client()
        self.pg_client = get_postgres_client()  # For category names only
        # Registry of forecasting models
        self._models: Dict[str, ForecastModel] = {
            "rolling": RollingAverageModel(),
            "wma": WeightedMovingAverageModel(),
            "ses": ExponentialSmoothingModel(),
            "snaive": SeasonalNaiveModel(),
            "arima": ARIMAModel(),
        }
        # Ensemble model weights (higher = more influence)
        self._ensemble_weights = {
            "arima": 0.35,
            "ses": 0.30,
            "wma": 0.20,
            "rolling": 0.15,
        }

    def _has_enough_data(self, model_name: str, data_points: int, bucket_type: str) -> bool:
        """Check if there's enough data for a given model."""
        # SNAIVE period varies by bucket type
        if model_name == "snaive":
            period = 7 if bucket_type == "DAY" else 52 if bucket_type == "WEEK" else 12
            return data_points >= period
        required = MODEL_DATA_REQUIREMENTS.get(model_name, 4)
        return data_points >= required

    def _evaluate_model_for_category(
        self, model: ForecastModel, series: List[TimeSeriesPoint], bucket_type: str, category_id: int
    ) -> float:
        """Simple one-step-ahead error for model selection."""
        if len(series) < 5:
            return float('inf')
        
        # Use last point as test, rest as training
        train_series = series[:-1]
        actual = series[-1].value
        
        try:
            forecast_value, _ = model.forecast(
                series=train_series,
                lookback=4,
                bucket_type=bucket_type,
                category_id=category_id,
                category_name=str(category_id),
            )
            if forecast_value is None:
                return float('inf')
            # Calculate absolute percentage error
            if actual == 0:
                return float('inf') if forecast_value != 0 else 0
            return abs((actual - forecast_value) / actual) * 100
        except:
            return float('inf')

    def _select_best_model_for_category(
        self, series: List[TimeSeriesPoint], category_id: int, bucket_type: str
    ) -> Tuple[str, float]:
        """Evaluate all eligible models for this category and return the best one."""
        data_points = len(series)
        
        # Filter eligible models based on data sufficiency
        eligible_models = {
            k: v for k, v in self._models.items()
            if self._has_enough_data(k, data_points, bucket_type)
        }
        
        if not eligible_models:
            return "rolling", float('inf')  # Fallback
        
        # Find model with lowest error
        best_model = "rolling"
        best_error = float('inf')
        
        for name, model in eligible_models.items():
            error = self._evaluate_model_for_category(model, series, bucket_type, category_id)
            if error < best_error:
                best_error = error
                best_model = name
        
        return best_model, best_error

    def _ensemble_forecast(
        self, series: List[TimeSeriesPoint], lookback: int, bucket_type: str, 
        category_id: int, category_name: str
    ) -> Tuple[Optional[float], str]:
        """Weighted average of multiple models."""
        forecasts = {}
        total_weight = 0
        data_points = len(series)
        
        for name, model in self._models.items():
            if name == "snaive":  # Skip SNAIVE in ensemble (too restrictive)
                continue
            if not self._has_enough_data(name, data_points, bucket_type):
                continue
            try:
                value, _ = model.forecast(series, lookback, bucket_type, category_id, category_name)
                if value is not None:
                    weight = self._ensemble_weights.get(name, 0.1)
                    forecasts[name] = (value, weight)
                    total_weight += weight
            except:
                pass
        
        if not forecasts:
            return None, "No models succeeded for ensemble"
        
        # Calculate weighted average
        ensemble_value = sum(v * w for v, w in forecasts.values()) / total_weight
        models_used = ", ".join(forecasts.keys())
        
        return round(ensemble_value, 2), f"Ensemble of {len(forecasts)} models: {models_used}"

    def _fetch_series(self, merchant_id: int, bucket_type: str, limit_per_category: int = 20) -> Dict[int, List[TimeSeriesPoint]]:
        """
        Fetches time-series data from ClickHouse (category_sales_agg).
        Filters by merchant_id to only return categories belonging to that merchant.
        """
        query = """
            SELECT merchant_id, category_id, bucket_start, total_sales_amount
            FROM category_sales_agg FINAL
            WHERE merchant_id = %(merchant_id)s AND bucket_type = %(bucket_type)s
            ORDER BY category_id, bucket_start ASC
        """
        
        category_series: Dict[int, List[TimeSeriesPoint]] = {}
        
        try:
            rows = self.ch_client.query(query, {"merchant_id": merchant_id, "bucket_type": bucket_type})
            
            for row in rows:
                cat_id = row['category_id']
                point = TimeSeriesPoint(
                    bucket_start=row['bucket_start'],
                    value=float(row['total_sales_amount'])
                )
                if cat_id not in category_series:
                    category_series[cat_id] = []
                category_series[cat_id].append(point)
                    
        except Exception as e:
            logger.error(f"Failed to fetch series from ClickHouse: {e}")
            raise
            
        return category_series

    def run_all_models(
        self,
        merchant_id: int,
        category_series: Dict[int, List[TimeSeriesPoint]], # Can pass in if already fetched, or None
        lookback: int,
        limit: int,
    ) -> Dict[int, Dict[str, Dict[str, ModelForecast]]]:
        """
        Run all available models using data from Postgres.
        """
        all_results = {}
        bucket_type = "DAY" 
        
        # If series not provided, fetch them (Worker flow usually fetches them)
        if category_series is None:
             category_series = self._fetch_series(merchant_id, bucket_type)

        for category_id, series in category_series.items():
            category_results = {"models": {}}
            for model_name, model_impl in self._models.items():
                try:
                    forecast_value, message = model_impl.forecast(
                        series=series,
                        lookback=lookback,
                        bucket_type=bucket_type,
                        category_id=category_id,
                        category_name=str(category_id), 
                    )
                    
                    forecast_points = None
                    if forecast_value is not None:
                        last_bucket_start = series[-1].bucket_start
                        next_bucket_start = last_bucket_start + pd.Timedelta(days=1)
                        forecast_points = [TimeSeriesPoint(bucket_start=next_bucket_start, value=forecast_value)]

                    category_results["models"][model_name] = ModelForecast(
                        forecast=forecast_points,
                        mae=None 
                    )

                except Exception as e:
                    logger.error(f"Model '{model_name}' failed for category {category_id}: {e}")
                    category_results["models"][model_name] = ModelForecast(forecast=None, mae=None)
            
            all_results[category_id] = category_results
        
        return all_results

    # ---------- PUBLIC API ----------

    def forecast_categories(
        self,
        merchant_id: int,
        category_series: Any, # Ignored in Postgres version, we fetch internally
        category_names: Dict[int, str],
        bucket_type: str,
        model: str = "rolling",
        lookback: Optional[int] = None,
        limit: int = 5
    ) -> ForecastResult:
        """
        Forecast next-period sales per category for a specific merchant.
        """
        lookback = lookback or self.default_lookback
        
        # Fetch fresh data from Postgres filtered by merchant
        series_map = self._fetch_series(merchant_id, bucket_type)
        
        results: List[CategoryForecastResult] = []
        messages: List[str] = []

        # Validate model for non-special cases
        if model not in ("auto", "ensemble") and model not in self._models:
            raise HTTPException(status_code=400, detail=f"Model '{model}' not found.")

        for category_id, series in series_map.items():
            category_name = category_names.get(category_id, str(category_id))
            
            if not series:
                continue

            try:
                # Handle special model modes
                if model == "auto":
                    # Per-category best model selection
                    best_model_name, _ = self._select_best_model_for_category(series, category_id, bucket_type)
                    model_impl = self._models[best_model_name]
                    forecast_value, message = model_impl.forecast(
                        series=series,
                        lookback=lookback,
                        bucket_type=bucket_type,
                        category_id=category_id,
                        category_name=category_name,
                    )
                    used_model_name = best_model_name
                elif model == "ensemble":
                    # Weighted ensemble of multiple models
                    forecast_value, message = self._ensemble_forecast(
                        series=series,
                        lookback=lookback,
                        bucket_type=bucket_type,
                        category_id=category_id,
                        category_name=category_name,
                    )
                    used_model_name = "ensemble"
                else:
                    # Standard single model
                    model_impl = self._models[model]
                    forecast_value, message = model_impl.forecast(
                        series=series,
                        lookback=lookback,
                        bucket_type=bucket_type,
                        category_id=category_id,
                        category_name=category_name,
                    )
                    used_model_name = model_impl.name
                
                if message:
                    messages.append(message)

                if forecast_value is not None:
                   confidence = compute_confidence(lookback)
                   results.append(CategoryForecastResult(
                        category_id=category_id,
                        category_name=category_name,
                        forecast_value=forecast_value,
                        model=used_model_name,
                        lookback=lookback,
                        confidence=confidence
                   ))

            except Exception as e:
                logger.error(f"Prediction failed for category {category_id}: {e}")
                continue

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
            return None, f"Not enough data for rolling average (needs {lookback}, has {len(series)})"

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
            return None, f"Not enough data for WMA (needs {lookback}, has {len(series)})"

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
            return None, "Not enough data for SES (needs 2+)"
        
        try:
            from statsmodels.tsa.api import SimpleExpSmoothing
            values = [p.value for p in series]
            model = SimpleExpSmoothing(values, initialization_method="estimated").fit()
            return model.forecast(1)[0], None
        except ImportError:
            raise HTTPException(status_code=501, detail="Statsmodels not installed")
        except Exception:
            return None, "SES calculation failed"

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
        period = 7 if bucket_type == "DAY" else 52 if bucket_type == "WEEK" else 12
        
        if len(series) < period:
            return None, f"Not enough data for Seasonal Naive (needs {period}, has {len(series)})"

        return series[-period].value, None


class ARIMAModel:
    """
    ARIMA (AutoRegressive Integrated Moving Average) model.
    Uses statsmodels ARIMA with order (1,1,1) as a robust default.
    Good for trending data with some autocorrelation.
    """
    name = "arima"

    def forecast(
        self,
        series: List[TimeSeriesPoint],
        lookback: int,
        bucket_type: str,
        category_id: int,
        category_name: str,
    ) -> Tuple[Optional[float], Optional[str]]:
        # ARIMA needs at least 10 observations for reasonable fitting
        if len(series) < 10:
            return None, f"Not enough data for ARIMA (needs 10+, has {len(series)})"
        
        try:
            from statsmodels.tsa.arima.model import ARIMA
            import warnings
            
            values = [p.value for p in series]
            
            # Suppress convergence warnings during fitting
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # ARIMA(1,1,1) is a robust default:
                # - p=1: One autoregressive term
                # - d=1: First differencing (handles trends)
                # - q=1: One moving average term
                model = ARIMA(values, order=(1, 1, 1))
                fitted = model.fit()
                
                # Forecast one step ahead
                forecast_value = fitted.forecast(steps=1)[0]
                
                # Ensure non-negative (sales can't be negative)
                forecast_value = max(0, forecast_value)
                
                return round(forecast_value, 2), None
                
        except ImportError:
            raise HTTPException(status_code=501, detail="Statsmodels not installed")
        except Exception as e:
            logger.warning(f"ARIMA failed for category {category_id}: {e}")
            return None, f"ARIMA calculation failed: {str(e)}"