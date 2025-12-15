from typing import List, Dict, Literal, Optional
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


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
    forecast_value: float
    model: str
    lookback: int


# ----------------------------
# Forecasting service
# ----------------------------

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
            if len(series) < lookback:
                print(
                    f"[forecasting] Skipping category {category_id}: "
                    f"only {len(series)} points, need {lookback}"
                )
                continue  # insufficient history

            forecast_value = self._forecast_series(
                series=series,
                model=model,
                lookback=lookback
            )

            if forecast_value is None:
                continue

            results.append(
                CategoryForecastResult(
                    category_id=category_id,
                    forecast_value=forecast_value,
                    model=model,
                    lookback=lookback
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
        lookback: int
    ) -> Optional[float]:

        if model == "rolling":
            return self._rolling_average(series, lookback)

        if model == "prophet":
            if not PROPHET_AVAILABLE:
                raise RuntimeError("Prophet model requested but not installed")
            return self._prophet_forecast(series)

        raise ValueError(f"Unknown forecasting model: {model}")

    # ---------- MODEL IMPLEMENTATIONS ----------

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
        series: List[TimeSeriesPoint]
    ) -> float:
        """
        Prophet-based time-series forecast.

        Predicts ONE future period.
        """

        df = pd.DataFrame(
            {
                "ds": [p.bucket_start for p in series],
                "y": [p.value for p in series],
            }
        )

        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False
        )

        model.fit(df)

        # Predict ONE future period
        future = model.make_future_dataframe(periods=1, freq="D")
        forecast = model.predict(future)

        return float(forecast.iloc[-1]["yhat"])
