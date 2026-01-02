from typing import List, Dict, Optional, Protocol, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from fastapi import HTTPException
import pandas as pd
import logging
from .postgres_client import get_postgres_client

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


class ForecastingService:
    """
    Stateless forecasting service.
    - Uses pre-aggregated time series from Postgres
    - Strategy-based model selection
    """
    def __init__(self, default_lookback: int = 4):
        self.default_lookback = default_lookback
        self.pg_client = get_postgres_client()
        # Registry of forecasting models
        self._models: Dict[str, ForecastModel] = {
            "rolling": RollingAverageModel(),
            "wma": WeightedMovingAverageModel(),
            "ses": ExponentialSmoothingModel(),
            "snaive": SeasonalNaiveModel(),
            "arima": ARIMAModel(),
        }

    def _fetch_series(self, merchant_id: int, bucket_type: str, limit_per_category: int = 20) -> Dict[int, List[TimeSeriesPoint]]:
        """
        Fetches time-series data from Postgres (forecasting.category_sales_agg).
        Filters by merchant_id to only return categories belonging to that merchant.
        """
        query = """
            SELECT merchant_id, category_id, bucket_start, total_sales_amount
            FROM forecasting.category_sales_agg
            WHERE merchant_id = %s AND bucket_type = %s
            ORDER BY category_id, bucket_start ASC
        """
        
        category_series: Dict[int, List[TimeSeriesPoint]] = {}
        
        try:
            with self.pg_client.cursor() as cur:
                cur.execute(query, (merchant_id, bucket_type))
                rows = cur.fetchall()
                
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
            logger.error(f"Failed to fetch series from Postgres: {e}")
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

        model_impl = self._models.get(model)
        if not model_impl:
            raise HTTPException(status_code=400, detail=f"Model '{model}' not found.")

        for category_id, series in series_map.items():
            category_name = category_names.get(category_id, str(category_id))
            
            if not series:
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

                if forecast_value is not None:
                   confidence = compute_confidence(lookback)
                   results.append(CategoryForecastResult(
                        category_id=category_id,
                        category_name=category_name,
                        forecast_value=forecast_value,
                        model=model_impl.name,
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