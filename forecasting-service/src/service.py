from typing import List, Dict, Optional, Protocol
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

# Prophet is imported lazily inside forecasting to avoid import cost when not used.


MIN_POINTS_FOR_PROPHET = 3

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
            "prophet": ProphetModel(),
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
    ) -> List[CategoryForecastResult]:
        """
        Forecast next-period sales per category.

        Parameters
        ----------
        category_series:
            { category_id -> ordered time series }
        model:
            "rolling" | "prophet"
        lookback:
            number of past periods (rolling window)
        limit:
            top N categories by forecast value
        """

        lookback = lookback or self.default_lookback
        results: List[CategoryForecastResult] = []

        model_impl = self._models.get(model)
        if not model_impl:
            raise ValueError(f"Unknown forecasting model: {model}")

        for category_id, series in category_series.items():
            category_name = category_names.get(category_id, str(category_id))

            # Skip if not enough data in general
            if not series:
                print(f"[forecasting] Skipping category {category_id}: empty series")
                continue

            forecast_value = model_impl.forecast(
                series=series,
                lookback=lookback,
                bucket_type=bucket_type,
                category_id=category_id,
                category_name=category_name,
            )

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

        try:
            from prophet import Prophet
        except Exception as e:
            raise ProphetNotAvailableError("Prophet model requested but not installed") from e

        # Map bucket_type to Prophet frequency
        if bucket_type == "DAY":
            freq = "D"
        elif bucket_type == "WEEK":
            freq = "W"
        elif bucket_type == "MONTH":
            freq = "MS"
        else:
            freq = "D"

        df = pd.DataFrame(
            {
                "ds": [p.bucket_start for p in series],
                "y": [p.value for p in series],
            }
        )

        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            random_state=42,
        )

        model.fit(df)

        future = model.make_future_dataframe(periods=1, freq=freq)
        forecast = model.predict(future)

        return float(forecast.iloc[-1]["yhat"])
