from typing import List, Dict, Literal, Optional
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

# Prophet is imported lazily inside forecasting to avoid import cost when not used.


MIN_POINTS_FOR_PROPHET = 3

class ProphetNotAvailableError(Exception):
    pass

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
    - Deterministic rolling window by default
    - Optional Prophet model
    """

    def __init__(self, default_lookback: int = 4):
        self.default_lookback = default_lookback

    # ---------- PUBLIC API ----------

    def forecast_categories(
        self,
        category_series: Dict[int, List[TimeSeriesPoint]],
        category_names: Dict[int, str],
        bucket_type: Literal["DAY","WEEK","MONTH"],
        model: Literal["rolling", "prophet"] = "rolling",
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

        for category_id, series in category_series.items():
            category_name = category_names.get(category_id, str(category_id))
            # Defaults
            effective_model = model
            effective_lookback = min(lookback, len(series))
            freq = self._freq_for_bucket(bucket_type)

            # Prophet eligibility check -> fallback to rolling if insufficient points
            if model == "prophet" and len(series) < MIN_POINTS_FOR_PROPHET:
                effective_model = "rolling"

            # Final safety check
            if effective_lookback == 0 or len(series) < effective_lookback:
                print(
                    f"[forecasting] Skipping category {category_id}: "
                    f"only {len(series)} points, need {lookback}"
                )
                continue  # insufficient history

            forecast_value = self._forecast_series(
                series=series,
                model=effective_model,
                lookback=effective_lookback,
                freq=freq
            )
            confidence = compute_confidence(effective_lookback)

            if forecast_value is None:
                continue

            results.append(
                CategoryForecastResult(
                    category_id=category_id,
                    category_name=category_name,
                    forecast_value=forecast_value,
                    model=effective_model,
                    lookback=effective_lookback,
                    confidence=confidence
                )
            )

        # Sort by forecasted value descending
        results.sort(key=lambda r: r.forecast_value, reverse=True)
        return results[:limit]

    # ---------- INTERNAL MODELS ----------

    def _forecast_series(
        self,
        series: List[TimeSeriesPoint],
        model: str,
        lookback: int,
        freq: Optional[str] = None
    ) -> Optional[float]:

        if model == "rolling":
            return self._rolling_average(series, lookback)

        if model == "prophet":
            return self._prophet_forecast(series, freq=freq)

        raise ValueError(f"Unknown forecasting model: {model}")
    

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

    @staticmethod
    def _rolling_average(
        series: List[TimeSeriesPoint],
        lookback: int
    ) -> float:
        """
        Deterministic baseline forecast.
        """
        values = [p.value for p in series[-lookback:]]
        return sum(values) / lookback

    @staticmethod
    def _prophet_forecast(
        series: List[TimeSeriesPoint],
        freq: str
    ) -> float:
        """
        Prophet-based time-series forecast.

        Predicts ONE future period.
        """
        try:
            from prophet import Prophet
        except Exception as e:
            raise ProphetNotAvailableError("Prophet model requested but not installed") from e

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
            random_state=42
        )

        model.fit(df)

        # Predict ONE future period
        future = model.make_future_dataframe(periods=1, freq=freq)
        forecast = model.predict(future)

        return float(forecast.iloc[-1]["yhat"])
