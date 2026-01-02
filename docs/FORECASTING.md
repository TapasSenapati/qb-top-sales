# Forecasting Strategy Guide

This document explains the forecasting models, evaluation methodology, and design decisions in this project.

## Overview

This service implements **5 forecasting models** with a **Strategy Pattern** architecture, allowing easy comparison and extension.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Time Series    │────▶│  Model Registry  │────▶│  Forecast       │
│  Data (Postgres)│     │  (5 strategies)  │     │  Results + MAE  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## Models Implemented

### 1. Rolling Average (`rolling`)
**Formula**: `forecast = mean(last N values)`

| Pros | Cons |
|------|------|
| Simple, interpretable | Lags behind trends |
| Robust to outliers | Ignores seasonality |

**Best for**: Stable demand, baseline comparison

---

### 2. Weighted Moving Average (`wma`)
**Formula**: `forecast = Σ(weight_i × value_i) / Σ(weights)`

Weights: `[1, 2, 3, 4]` (recent values weighted more)

| Pros | Cons |
|------|------|
| Responds faster to trends | Arbitrary weight selection |
| Easy to tune | Still lags sudden changes |

**Best for**: Slow-trending products

---

### 3. Simple Exponential Smoothing (`ses`)
**Formula**: `S_t = α × Y_t + (1-α) × S_{t-1}`

Uses statsmodels with estimated α.

| Pros | Cons |
|------|------|
| Optimal α estimation | No trend/seasonality |
| Noise reduction | Single parameter |

**Best for**: Noisy data without patterns

---

### 4. Seasonal Naive (`snaive`)
**Formula**: `forecast = value from same period last cycle`

| Bucket | Period |
|--------|--------|
| DAY | 7 (weekly) |
| WEEK | 52 (yearly) |
| MONTH | 12 (yearly) |

| Pros | Cons |
|------|------|
| Captures seasonality | Needs full cycle of data |
| Strong baseline | Ignores trends |

**Best for**: Products with strong weekly/yearly patterns

---

### 5. ARIMA (`arima`)
**Model**: ARIMA(1,1,1)

| Parameter | Meaning |
|-----------|---------|
| p=1 | 1 autoregressive term |
| d=1 | First differencing (removes trend) |
| q=1 | 1 moving average term |

| Pros | Cons |
|------|------|
| Handles trends | Slower computation |
| Statistical foundation | Needs 10+ data points |
| Confidence intervals | Order selection matters |

**Best for**: Trending categories (Electronics, Jewelry growth)

---

## Walk-Forward Validation (Backtesting)

The `/evaluate-models` endpoint implements **walk-forward validation**, the gold standard for time series backtesting.

### How It Works:

```
Training Window (expanding)          Test Point
[────────────────────────────────]   [X]  → Error₁
[────────────────────────────────────][X] → Error₂
[────────────────────────────────────────][X] → Error₃
                                          ...

Final Metrics = aggregate(Error₁, Error₂, ... Errorₙ)
```

### Metrics Calculated:

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **MAE** | mean(\|actual - predicted\|) | Average error in units |
| **MSE** | mean((actual - predicted)²) | Penalizes large errors |
| **RMSE** | √MSE | Error in original units |
| **MAPE** | mean(\|error\| / actual) × 100 | Percentage error |

### Why Walk-Forward?

- ❌ **Train/Test Split**: Wastes data, single evaluation point
- ❌ **Cross-Validation**: Violates temporal order
- ✅ **Walk-Forward**: Realistic, multiple test points, respects time order

---

## Model Selection Guide

| Scenario | Recommended Model | Why |
|----------|-------------------|-----|
| Quick baseline | `rolling` | Simple, interpretable |
| Stable demand | `ses` | Noise reduction |
| Weekend spikes | `snaive` | Captures weekly cycle |
| Growing category | `arima` | Handles trends |
| Unknown pattern | Compare all → lowest MAE | Data-driven selection |

---

## Architecture Decisions

### 1. Strategy Pattern
```python
class ForecastModel(Protocol):
    name: str
    def forecast(self, series, lookback, ...) -> Tuple[float, Optional[str]]
```
**Why**: Easy to add new models, swap algorithms, A/B test

### 2. Pre-computed vs Real-time

| Endpoint | Type | Use Case |
|----------|------|----------|
| `/forecast/top-categories` | Real-time | Custom parameters |
| `/forecast/compare-models` | Pre-computed | Fast dashboard display |
| `/evaluate-models` | Real-time | Model selection |

**Why**: Balance between freshness and performance

### 3. Batch Timestamp for Worker
All forecasts in a batch share one timestamp to enable querying "latest batch".

---

## Interview Talking Points

1. **Design Patterns**: Strategy pattern for models, Registry pattern for lookup
2. **Observability**: Custom OpenTelemetry spans on DB operations
3. **Testing Philosophy**: Walk-forward validation vs naive train/test
4. **Trade-offs**: Pre-computation speed vs real-time freshness
5. **Extensibility**: Adding ARIMA required ~50 lines, no changes to API

---

## Future Improvements

- [ ] **Prophet**: Multi-seasonality + holiday effects
- [ ] **Auto-ARIMA**: Automatic order selection (pmdarima)
- [ ] **Model Ensemble**: Weighted average of top models
- [ ] **Confidence Intervals**: Return prediction intervals
- [ ] **Feature Store**: Add external regressors (promotions, weather)
