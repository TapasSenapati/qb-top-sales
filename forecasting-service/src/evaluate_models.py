
import pandas as pd
from collections import defaultdict
from typing import Dict, List
import numpy as np

from .service import ForecastingService, TimeSeriesPoint
from .db import fetch_category_time_series


def evaluate_models(merchant_id: int, bucket_type: str, test_points: int = 5) -> Dict:
    """
    Evaluates all forecasting models using a walk-forward validation approach.

    Args:
        merchant_id: The merchant ID to evaluate.
        bucket_type: The aggregation bucket type (DAY, WEEK, MONTH).
        test_points: The number of recent data points to use for testing.

    Returns:
        A dictionary containing the evaluation metrics for each model,
        plus data sufficiency metadata.
    """
    print(f"Evaluating models for merchant {merchant_id}, bucket {bucket_type}...")

    all_series, category_names = fetch_category_time_series(merchant_id, bucket_type)
    forecasting_service = ForecastingService()
    model_names = forecasting_service._models.keys()

    # Track data sufficiency per category
    data_points_per_category = {}
    for category_id, series in all_series.items():
        data_points_per_category[category_id] = {
            "category_name": category_names.get(category_id, f"Category {category_id}"),
            "data_points": len(series)
        }

    # Minimum data requirements per model
    model_requirements = {
        "rolling": 4,
        "wma": 4,
        "ses": 4,
        "snaive": 52,  # Needs 1 year of data
        "arima": 10
    }

    results = defaultdict(lambda: defaultdict(list))
    for category_id, series in all_series.items():
        if len(series) < test_points + 1:
            continue

        for i in range(1, test_points + 1):
            train_series = series[:-i]
            actual_value = series[-i].value
            if not train_series:
                continue

            for model_name in model_names:
                model = forecasting_service._models[model_name]
                try:
                    lookback = 4
                    forecast_value, _ = model.forecast(
                        series=train_series,
                        lookback=lookback,
                        bucket_type=bucket_type,
                        category_id=category_id,
                        category_name=category_names[category_id],
                    )
                    if forecast_value is not None:
                        results[model_name]["actuals"].append(actual_value)
                        results[model_name]["forecasts"].append(forecast_value)
                except Exception as e:
                    print(f"Error forecasting with {model_name}: {e}")

    metrics = {}
    for model_name, data in results.items():
        actuals = np.array(data["actuals"])
        forecasts = np.array(data["forecasts"])

        if len(actuals) == 0:
            metrics[model_name] = {
                "error": "No forecasts generated",
                "mae": None,
                "mse": None,
                "rmse": None,
                "mape": None,
                "forecasts_generated": 0,
            }
            continue

        mae = np.mean(np.abs(forecasts - actuals))
        mse = np.mean((forecasts - actuals) ** 2)
        rmse = np.sqrt(mse)
        mape = np.mean(np.abs((actuals - forecasts) / actuals)) * 100
        metrics[model_name] = {
            "mae": f"{float(mae):.2f}",
            "mse": f"{float(mse):.2f}",
            "rmse": f"{float(rmse):.2f}",
            "mape": f"{float(mape):.2f}%",
            "forecasts_generated": int(len(forecasts)),
        }

    # Add data sufficiency metadata
    min_data_points = min((d["data_points"] for d in data_points_per_category.values()), default=0)
    max_data_points = max((d["data_points"] for d in data_points_per_category.values()), default=0)
    
    # Determine which models are eligible based on data availability
    eligible_models = []
    for model, required in model_requirements.items():
        if min_data_points >= required:
            eligible_models.append(model)
    
    # Add metadata to response (prefix with _ to indicate metadata)
    metrics["_data_sufficiency"] = {
        "min_data_points": min_data_points,
        "max_data_points": max_data_points,
        "category_count": len(data_points_per_category),
        "eligible_models": eligible_models,
        "model_requirements": model_requirements,
        "recommendation": "rolling" if min_data_points < 10 else ("arima" if min_data_points >= 10 else "ses")
    }

    print("\nEvaluation complete.")
    return metrics


if __name__ == "__main__":
    # Example: Evaluate models for merchant 1, with daily data
    # You might need to ensure your DB is running and populated.
    # You can run this script from the root of the project with:
    # python -m forecasting-service.src.evaluate_models
    evaluation_metrics = evaluate_models(merchant_id=1, bucket_type="DAY")
    import json
    print(json.dumps(evaluation_metrics, indent=2))
