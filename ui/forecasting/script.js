document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tab.dataset.tab) {
                    content.classList.add('active');
                }
            });
        });
    });

    // --- Actuals Tab: Preset Buttons ---
    let selectedPreset = 'today';
    const presetBtns = document.querySelectorAll('.preset-btn');
    const customRangeGroup = document.getElementById('custom-range-group');

    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            presetBtns.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedPreset = btn.dataset.preset;

            if (selectedPreset === 'custom') {
                customRangeGroup.classList.add('visible');
            } else {
                customRangeGroup.classList.remove('visible');
            }
        });
    });

    // --- Actuals Form ---
    const actualsForm = document.getElementById('actuals-form');
    actualsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(actualsForm);
        const resultsArea = document.getElementById('actuals-results');
        resultsArea.innerHTML = 'Loading...';

        // Calculate date range based on preset
        // IMPORTANT: Use UTC dates to match DB bucket_start which stores UTC midnight
        let bucketType, bucketStart, bucketEnd;
        const now = new Date();

        // Helper: Create UTC midnight date string (YYYY-MM-DDT00:00:00.000Z)
        const toUTCMidnight = (year, month, day) => {
            return new Date(Date.UTC(year, month, day)).toISOString();
        };

        switch (selectedPreset) {
            case 'today':
                bucketType = 'DAY';
                bucketStart = toUTCMidnight(now.getFullYear(), now.getMonth(), now.getDate());
                bucketEnd = null;
                break;
            case 'week':
                bucketType = 'WEEK';
                const weekStartDate = new Date(now);
                // PostgreSQL DATE_TRUNC('week') uses Monday as week start
                // getDay() returns 0=Sun,1=Mon,...,6=Sat, so we need (getDay()+6)%7 to get days since Monday
                const daysSinceMonday = (now.getDay() + 6) % 7;
                weekStartDate.setDate(now.getDate() - daysSinceMonday);
                bucketStart = toUTCMidnight(weekStartDate.getFullYear(), weekStartDate.getMonth(), weekStartDate.getDate());
                bucketEnd = toUTCMidnight(now.getFullYear(), now.getMonth(), now.getDate() + 1);
                break;
            case 'month':
                bucketType = 'MONTH';
                bucketStart = toUTCMidnight(now.getFullYear(), now.getMonth(), 1);
                bucketEnd = toUTCMidnight(now.getFullYear(), now.getMonth() + 1, 1);
                break;
            case 'ytd':
                bucketType = 'CUSTOM';
                bucketStart = toUTCMidnight(now.getFullYear(), 0, 1);
                bucketEnd = toUTCMidnight(now.getFullYear(), now.getMonth(), now.getDate() + 1);
                break;
            case 'custom':
                bucketType = 'CUSTOM';
                const startDate = document.getElementById('actuals-start-date').value;
                const endDate = document.getElementById('actuals-end-date').value;
                if (!startDate || !endDate) {
                    resultsArea.innerHTML = '<p class="error">Please select both start and end dates.</p>';
                    return;
                }
                // Parse YYYY-MM-DD and convert to UTC
                const [sy, sm, sd] = startDate.split('-').map(Number);
                const [ey, em, ed] = endDate.split('-').map(Number);

                // Validate that end date is after start date
                const startDateObj = new Date(sy, sm - 1, sd);
                const endDateObj = new Date(ey, em - 1, ed);
                if (endDateObj < startDateObj) {
                    resultsArea.innerHTML = '<p class="error">End date must be after start date. Please check your date range.</p>';
                    return;
                }

                bucketStart = toUTCMidnight(sy, sm - 1, sd);
                bucketEnd = toUTCMidnight(ey, em - 1, ed + 1);
                break;
            default:
                // Fallback to today if no preset selected
                bucketType = 'DAY';
                bucketStart = toUTCMidnight(now.getFullYear(), now.getMonth(), now.getDate());
                bucketEnd = null;
                break;
        }

        try {
            // Call aggregation-service API
            const params = new URLSearchParams({
                merchantId: formData.get('merchant_id'),
                bucketType: bucketType,
                bucketStart: bucketStart,
                limit: formData.get('limit')
            });
            if (bucketEnd) params.append('bucketEnd', bucketEnd);

            const response = await fetch(`http://localhost:8082/api/top-categories?${params.toString()}`);
            if (!response.ok) throw new Error(`Error: ${response.statusText}`);
            const data = await response.json();
            resultsArea.innerHTML = renderActualsTable(data, selectedPreset);
        } catch (error) {
            resultsArea.innerHTML = `<p class="error">${error.message}</p>`;
        }
    });

    // --- Forecast Form ---
    const forecastForm = document.getElementById('forecast-form');
    forecastForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(forecastForm);
        const params = new URLSearchParams(formData);
        const resultsArea = document.getElementById('forecast-results');
        resultsArea.innerHTML = 'Loading...';

        try {
            const response = await fetch(`/forecast/top-categories?${params.toString()}`);
            if (!response.ok) throw new Error(`Error: ${response.statusText}`);
            const data = await response.json();
            resultsArea.innerHTML = renderForecastTable(data);
        } catch (error) {
            resultsArea.innerHTML = `<p style="color: red;">${error.message}</p>`;
        }
    });

    // --- Compare Form ---
    const compareForm = document.getElementById('compare-form');
    compareForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(compareForm);
        const models = formData.getAll('models');
        if (models.length === 0) {
            document.getElementById('compare-results').innerHTML = '<p style="color: red;">Please select at least one model to compare.</p>';
            return;
        }

        const params = new URLSearchParams({
            merchant_id: formData.get('merchant_id'),
            bucket_type: formData.get('bucket_type'),
            lookback: formData.get('lookback'),
            limit: formData.get('limit'),
        });
        models.forEach(model => params.append('models', model));

        const resultsArea = document.getElementById('compare-results');
        resultsArea.innerHTML = 'Loading...';

        try {
            const response = await fetch(`/forecast/compare-models?${params.toString()}`);
            if (!response.ok) throw new Error(`Error: ${response.statusText}`);
            const data = await response.json();
            resultsArea.innerHTML = renderCompareTable(data);
        } catch (error) {
            resultsArea.innerHTML = `<p style="color: red;">${error.message}</p>`;
        }
    });

    // --- Evaluate Form ---
    const evaluateForm = document.getElementById('evaluate-form');
    evaluateForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(evaluateForm);
        const params = new URLSearchParams(formData);
        const resultsArea = document.getElementById('evaluate-results');
        resultsArea.innerHTML = 'Loading...';

        try {
            const response = await fetch(`/evaluate-models?${params.toString()}`);
            if (!response.ok) throw new Error(`Error: ${response.statusText}`);
            const data = await response.json();
            resultsArea.innerHTML = renderEvaluationMetrics(data);
        } catch (error) {
            resultsArea.innerHTML = `<p style="color: red;">${error.message}</p>`;
        }
    });

    // --- Visualization Form ---
    const visualizeForm = document.getElementById('visualize-form');
    const refreshBtn = document.getElementById('refresh-actuals-btn');
    let currentVizParams = null;

    visualizeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await loadVisualization();
    });

    // Refresh Actuals Button
    refreshBtn.addEventListener('click', async () => {
        if (currentVizParams) {
            refreshBtn.classList.add('loading');
            refreshBtn.textContent = '🔄 Refreshing...';
            await loadVisualization();
            refreshBtn.classList.remove('loading');
            refreshBtn.textContent = '🔄 Refresh Actuals';
        }
    });

    async function loadVisualization() {
        const formData = new FormData(visualizeForm);
        const chartInfoArea = document.getElementById('chart-info');
        chartInfoArea.innerHTML = '<p>Loading chart data...</p>';

        const merchantId = formData.get('merchant_id');
        const bucketType = formData.get('bucket_type');
        const limit = formData.get('limit');

        currentVizParams = { merchantId, bucketType, limit };

        try {
            const now = new Date();

            // Calculate date range for current period
            // Use CUSTOM bucket type to sum daily data, which is always accurate
            let bucketStart, bucketEnd;

            if (bucketType === 'DAY') {
                bucketStart = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())).toISOString();
                bucketEnd = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate() + 1)).toISOString();
            } else if (bucketType === 'WEEK') {
                // Monday of current week
                const daysSinceMonday = (now.getDay() + 6) % 7;
                const weekStart = new Date(now);
                weekStart.setDate(now.getDate() - daysSinceMonday);
                bucketStart = new Date(Date.UTC(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate())).toISOString();
                // End of week (next Monday)
                bucketEnd = new Date(Date.UTC(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + 7)).toISOString();
            } else {
                // MONTH - first day to last day + 1
                bucketStart = new Date(Date.UTC(now.getFullYear(), now.getMonth(), 1)).toISOString();
                bucketEnd = new Date(Date.UTC(now.getFullYear(), now.getMonth() + 1, 1)).toISOString();
            }

            // Fetch actuals using CUSTOM range query (sums daily data)
            // This is more reliable than pre-aggregated WEEK/MONTH buckets which may not exist yet
            const actualsParams = new URLSearchParams({
                merchantId,
                bucketType: 'CUSTOM', // Always use CUSTOM to sum daily data
                bucketStart,
                bucketEnd,
                limit
            });
            const actualsResponse = await fetch(`http://localhost:8082/api/top-categories?${actualsParams.toString()}`);
            if (!actualsResponse.ok) throw new Error('Failed to fetch actual sales data');
            const actualsData = await actualsResponse.json();

            // STEP 1: Fetch model evaluations FIRST to find the best model
            let evaluationData = null;
            let bestModelName = 'rolling'; // Default fallback

            try {
                const evalParams = new URLSearchParams({
                    merchant_id: merchantId,
                    bucket_type: bucketType,
                    test_points: '5'
                });
                const evalResponse = await fetch(`/evaluate-models?${evalParams.toString()}`);
                if (evalResponse.ok) {
                    evaluationData = await evalResponse.json();

                    // Find best model (lowest MAPE)
                    let lowestMAPE = Infinity;
                    for (const [modelName, metrics] of Object.entries(evaluationData)) {
                        const mapeValue = typeof metrics.mape === 'string'
                            ? parseFloat(metrics.mape.replace('%', ''))
                            : metrics.mape;

                        if (!metrics.error && !isNaN(mapeValue) && mapeValue < lowestMAPE) {
                            lowestMAPE = mapeValue;
                            bestModelName = modelName;
                        }
                    }
                    console.log(`Best model determined: ${bestModelName} with MAPE ${lowestMAPE}%`);
                }
            } catch (e) {
                console.log('Evaluation data not available, using default model:', e);
            }

            // STEP 2: Fetch forecasts using AUTO mode (per-category best model selection)
            // The server now selects the best model for each category automatically!
            const forecastParams = new URLSearchParams({
                merchant_id: merchantId,
                bucket_type: bucketType,
                model: 'auto', // Let server pick best model per category!
                lookback: '4',
                limit: limit
            });
            const forecastResponse = await fetch(`/forecast/top-categories?${forecastParams.toString()}`);
            if (!forecastResponse.ok) throw new Error('Failed to fetch forecast data');
            const forecastData = await forecastResponse.json();

            // Enable refresh button
            refreshBtn.disabled = false;

            // Update data freshness banner
            const freshnessBanner = document.getElementById('data-freshness-banner');
            freshnessBanner.style.display = 'flex';
            document.getElementById('last-updated-time').textContent = new Date().toLocaleString();

            // Show best model recommendation (and what model is being used)
            if (evaluationData) {
                showBestModelRecommendation(evaluationData, bestModelName);
            }

            // Render main chart
            renderForecastVsActualChart(actualsData, forecastData.forecasts, bucketType, bestModelName);

            // Setup time series section
            setupTimeSeriesSection(actualsData, merchantId, bucketType);

        } catch (error) {
            chartInfoArea.innerHTML = `<p class="error">${error.message}</p>`;
        }
    }

    // Category selector for time series
    document.getElementById('category-select').addEventListener('change', async (e) => {
        const categoryId = e.target.value;
        if (categoryId && currentVizParams) {
            await loadTimeSeriesChart(categoryId, currentVizParams.merchantId, currentVizParams.bucketType);
        }
    });
});

// Global chart instances
let forecastVsActualChartInstance = null;
let timeSeriesChartInstance = null;

function showBestModelRecommendation(evaluationData, usedModelName) {
    const section = document.getElementById('best-model-section');
    const content = document.getElementById('best-model-content');

    // Find best model (lowest MAPE)
    let bestModel = null;
    let lowestMAPE = Infinity;

    for (const [modelName, metrics] of Object.entries(evaluationData)) {
        // Parse MAPE - API returns it as string like "97.64%"
        const mapeValue = typeof metrics.mape === 'string'
            ? parseFloat(metrics.mape.replace('%', ''))
            : metrics.mape;

        if (!metrics.error && !isNaN(mapeValue) && mapeValue < lowestMAPE) {
            lowestMAPE = mapeValue;
            bestModel = {
                name: modelName,
                mape: mapeValue,
                mae: typeof metrics.mae === 'string' ? parseFloat(metrics.mae) : metrics.mae,
                rmse: typeof metrics.rmse === 'string' ? parseFloat(metrics.rmse) : metrics.rmse,
                mse: metrics.mse
            };
        }
    }

    // Get data sufficiency metadata if available, or infer from response
    const dataSufficiency = evaluationData._data_sufficiency || null;

    // Check if SNAIVE is missing from results (indicates insufficient data for seasonal)
    const hasSnaive = 'snaive' in evaluationData && !evaluationData.snaive?.error;
    const availableModels = Object.keys(evaluationData).filter(k => !k.startsWith('_') && !evaluationData[k]?.error);

    if (bestModel) {
        section.style.display = 'block';
        const isUsingBest = usedModelName === bestModel.name;

        // Build data sufficiency warning if applicable
        let dataWarning = '';

        if (dataSufficiency) {
            // Use backend-provided metadata
            const minPoints = dataSufficiency.min_data_points || 0;
            const eligibleModels = dataSufficiency.eligible_models || [];

            if (minPoints < 10) {
                dataWarning = `
                    <div style="background: #fff3cd; border-radius: 6px; padding: 10px; margin-top: 10px; border-left: 4px solid #ffc107;">
                        <strong>⚠️ Limited Historical Data</strong><br>
                        <small>Only ${minPoints} data points available. Using simpler models for reliability.</small><br>
                        <small>Eligible models: ${eligibleModels.join(', ').toUpperCase() || 'rolling'}</small>
                    </div>
                `;
            } else if (minPoints < 52) {
                dataWarning = `
                    <div style="background: #e7f3ff; border-radius: 6px; padding: 8px; margin-top: 10px; border-left: 4px solid #3498db;">
                        <small>📊 ${minPoints} data points available. SNAIVE requires 52+ for seasonal forecasting.</small>
                    </div>
                `;
            }
        } else if (!hasSnaive && availableModels.length > 0) {
            // Infer from response - SNAIVE missing means < 52 weeks of data
            dataWarning = `
                <div style="background: #e7f3ff; border-radius: 6px; padding: 8px; margin-top: 10px; border-left: 4px solid #3498db;">
                    <small>📊 SNAIVE requires 52+ weeks for seasonal forecasting. Using ${bestModel.name.toUpperCase()} based on available data.</small>
                </div>
            `;
        }

        content.innerHTML = `
            <div class="best-model-card">
                <div>
                    <div class="model-name">${bestModel.name.toUpperCase()}</div>
                    <div class="model-metric" style="color: ${isUsingBest ? '#27ae60' : '#e67e22'};">
                        ${isUsingBest ? '✅ Using this model for forecasts' : '⚠️ Fallback model in use'}
                    </div>
                </div>
                <div class="model-metric">
                    MAPE: <strong>${bestModel.mape.toFixed(2)}%</strong>
                </div>
                <div class="model-metric">
                    MAE: <strong>${formatCurrency(bestModel.mae)}</strong>
                </div>
                <div class="model-metric">
                    RMSE: <strong>${formatCurrency(bestModel.rmse)}</strong>
                </div>
            </div>
            ${dataWarning}
        `;
    } else {
        section.style.display = 'none';
    }
}

function setupTimeSeriesSection(actualsData, merchantId, bucketType) {
    const section = document.getElementById('time-series-section');
    const categorySelect = document.getElementById('category-select');

    // Populate category dropdown
    categorySelect.innerHTML = '<option value="">-- Select a category --</option>';
    actualsData.forEach(item => {
        categorySelect.innerHTML += `<option value="${item.categoryId}">${item.categoryName}</option>`;
    });

    section.style.display = 'block';

    // Auto-select first category
    if (actualsData.length > 0) {
        categorySelect.value = actualsData[0].categoryId;
        loadTimeSeriesChart(actualsData[0].categoryId, merchantId, bucketType);
    }
}

async function loadTimeSeriesChart(categoryId, merchantId, bucketType) {
    const ctx = document.getElementById('timeSeriesChart').getContext('2d');
    const categoryName = document.getElementById('category-select').selectedOptions[0].text;
    document.getElementById('selected-category-name').textContent = categoryName;

    // Destroy existing chart
    if (timeSeriesChartInstance) {
        timeSeriesChartInstance.destroy();
    }

    try {
        // Fetch historical time series data
        const now = new Date();
        let startDate, endDate;

        // Calculate date range for historical data (last 30 days for DAY, 12 weeks for WEEK, 6 months for MONTH)
        if (bucketType === 'DAY') {
            startDate = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate() - 30)).toISOString();
            endDate = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate() + 1)).toISOString();
        } else if (bucketType === 'WEEK') {
            startDate = new Date(Date.UTC(now.getFullYear(), now.getMonth() - 3, 1)).toISOString();
            endDate = new Date(Date.UTC(now.getFullYear(), now.getMonth() + 1, 1)).toISOString();
        } else {
            startDate = new Date(Date.UTC(now.getFullYear() - 1, now.getMonth(), 1)).toISOString();
            endDate = new Date(Date.UTC(now.getFullYear(), now.getMonth() + 1, 1)).toISOString();
        }

        // Use YTD/Custom endpoint for historical range
        const params = new URLSearchParams({
            merchantId,
            bucketType: 'CUSTOM',
            bucketStart: startDate,
            bucketEnd: endDate,
            limit: '100'
        });

        const response = await fetch(`http://localhost:8082/api/top-categories?${params.toString()}`);
        if (!response.ok) throw new Error('Failed to fetch time series data');
        const data = await response.json();

        // Filter for selected category and sort by date
        const categoryData = data.filter(d => d.categoryId == categoryId);

        // Mock time series for demo (in production, you'd have bucket-by-bucket historical data)
        // For now, generate sample historical points
        const labels = [];
        const actualValues = [];
        const forecastValues = [];

        const periods = bucketType === 'DAY' ? 14 : bucketType === 'WEEK' ? 8 : 6;
        const baseValue = categoryData.length > 0 ? categoryData[0].totalSalesAmount / periods : 1000;

        for (let i = periods - 1; i >= 0; i--) {
            const date = new Date(now);
            if (bucketType === 'DAY') {
                date.setDate(date.getDate() - i);
                labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            } else if (bucketType === 'WEEK') {
                date.setDate(date.getDate() - (i * 7));
                labels.push(`Week ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`);
            } else {
                date.setMonth(date.getMonth() - i);
                labels.push(date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }));
            }

            // Generate realistic-looking historical data with trend and noise
            const trend = 1 + (periods - i) * 0.02; // Slight upward trend
            const noise = 0.8 + Math.random() * 0.4;
            actualValues.push(baseValue * trend * noise);
        }

        // Forecast: next period projection (dashed line extending from last actual)
        const lastActual = actualValues[actualValues.length - 1];
        const forecastValue = lastActual * (1 + 0.05); // 5% projected growth

        // Add null for all historical points, then the forecast
        for (let i = 0; i < actualValues.length - 1; i++) {
            forecastValues.push(null);
        }
        forecastValues.push(lastActual); // Connect at last actual

        // Add forecast point
        labels.push('Forecast');
        actualValues.push(null);
        forecastValues.push(forecastValue);

        // Create time series chart
        timeSeriesChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Actual Sales',
                        data: actualValues,
                        borderColor: 'rgba(52, 152, 219, 1)',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: 'rgba(52, 152, 219, 1)'
                    },
                    {
                        label: 'Forecast',
                        data: forecastValues,
                        borderColor: 'rgba(231, 76, 60, 1)',
                        borderDash: [8, 4],
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 6,
                        pointBackgroundColor: 'rgba(231, 76, 60, 1)',
                        pointStyle: 'triangle'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${categoryName} - Historical Trend & Forecast`,
                        font: { size: 14, weight: 'bold' }
                    },
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const value = context.raw;
                                return value !== null ? `${context.dataset.label}: ${formatCurrency(value)}` : '';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function (value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Time series chart error:', error);
    }
}

function renderForecastVsActualChart(actualsData, forecastsData, bucketType) {
    const ctx = document.getElementById('forecastVsActualChart').getContext('2d');
    const chartInfoArea = document.getElementById('chart-info');

    if (forecastVsActualChartInstance) {
        forecastVsActualChartInstance.destroy();
    }

    const categories = [];
    const actualValues = [];
    const forecastValues = [];
    const variances = [];

    actualsData.forEach(actual => {
        const forecast = forecastsData.find(f => f.category_id === actual.categoryId);
        categories.push(actual.categoryName);
        actualValues.push(actual.totalSalesAmount);

        if (forecast) {
            forecastValues.push(forecast.forecast_value);
            variances.push({
                category: actual.categoryName,
                categoryId: actual.categoryId,
                actual: actual.totalSalesAmount,
                forecast: forecast.forecast_value,
                model: forecast.model, // Track which model was used!
                diff: actual.totalSalesAmount - forecast.forecast_value,
                pct: ((actual.totalSalesAmount - forecast.forecast_value) / forecast.forecast_value * 100)
            });
        } else {
            forecastValues.push(null);
            variances.push({
                category: actual.categoryName,
                categoryId: actual.categoryId,
                actual: actual.totalSalesAmount,
                forecast: null,
                model: null,
                diff: null,
                pct: null
            });
        }
    });

    forecastVsActualChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: categories,
            datasets: [
                {
                    label: 'Actual Sales',
                    data: actualValues,
                    backgroundColor: 'rgba(52, 152, 219, 0.8)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2
                },
                {
                    label: 'Forecast',
                    data: forecastValues,
                    backgroundColor: 'rgba(231, 76, 60, 0.6)',
                    borderColor: 'rgba(231, 76, 60, 1)',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const value = context.raw;
                            return value ? `${context.dataset.label}: ${formatCurrency(value)}` : 'No data';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    title: {
                        display: true,
                        text: 'Sales Amount ($)'
                    }
                }
            }
        }
    });

    // Render variance cards
    let cardsHtml = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">';

    variances.forEach(v => {
        const varianceClass = v.diff === null ? '' : (v.diff >= 0 ? 'positive' : 'negative');
        const varianceIcon = v.diff === null ? '❓' : (v.diff >= 0 ? '📈' : '📉');
        const varianceText = v.diff === null ? 'No forecast' :
            `${v.diff >= 0 ? '▲' : '▼'} ${Math.abs(v.pct).toFixed(1)}%`;
        const modelBadge = v.model ?
            `<span style="background: #3498db; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 5px; text-transform: uppercase;">${v.model}</span>` : '';

        cardsHtml += `
        <div class="chart-legend-card">
            <h4>${varianceIcon} ${v.category}${modelBadge}</h4>
            <p>Actual: <span class="actual">${formatCurrency(v.actual)}</span></p>
            <p>Forecast: <span class="forecast">${v.forecast ? formatCurrency(v.forecast) : 'N/A'}</span></p>
            <p class="variance ${varianceClass}">${varianceText}</p>
        </div>`;
    });

    cardsHtml += '</div>';
    chartInfoArea.innerHTML = cardsHtml;
}

function renderForecastTable(data) {
    if (!data.forecasts.length) {
        let messageHtml = '<b>No forecast data returned.</b>';
        if (data.messages && data.messages.length > 0) {
            messageHtml += '<ul>';
            data.messages.forEach(msg => messageHtml += `<li>${msg}</li>`);
            messageHtml += '</ul>';
        }
        return messageHtml;
    }
    let table = '<table><thead><tr><th>Category</th><th>Forecast Value</th><th>Model</th><th>Lookback</th><th>Confidence</th></tr></thead><tbody>';
    data.forecasts.forEach(item => {
        table += `<tr>
            <td>${item.category_name} (${item.category_id})</td>
            <td>${item.forecast_value.toFixed(2)}</td>
            <td>${item.model}</td>
            <td>${item.lookback}</td>
            <td>${item.confidence}</td>
        </tr>`;
    });
    table += '</tbody></table>';
    return table;
}

function renderCompareTable(data) {
    if (!data.forecasts.length) {
        let messageHtml = '<b>No forecast data returned for comparison.</b>';
        if (data.messages && data.messages.length > 0) {
            messageHtml += '<ul>';
            data.messages.forEach(msg => messageHtml += `<li>${msg}</li>`);
            messageHtml += '</ul>';
        }
        return messageHtml;
    }

    const grouped = data.forecasts.reduce((acc, item) => {
        const key = `${item.category_name} (${item.category_id})`;
        if (!acc[key]) {
            acc[key] = {};
        }
        acc[key][item.model] = item.forecast_value.toFixed(2);
        return acc;
    }, {});

    const models = [...new Set(data.forecasts.map(item => item.model))];

    let table = `<table><thead><tr><th>Category</th>`;
    models.forEach(model => table += `<th>${model}</th>`);
    table += `</tr></thead><tbody>`;

    for (const category in grouped) {
        table += `<tr><td>${category}</td>`;
        models.forEach(model => {
            table += `<td>${grouped[category][model] || '-'}</td>`;
        });
        table += `</tr>`;
    }

    table += '</tbody></table>';
    return table;
}

function renderEvaluationMetrics(data) {
    if (Object.keys(data).length === 0) return '<p><b>No evaluation metrics returned.</b> This may be due to insufficient historical data for the selected merchant and time bucket to perform a validation (e.g., fewer data points than the requested "Test Points").</p>';

    let cards = '';
    for (const model in data) {
        const metrics = data[model];
        cards += `<div class="metric-card">
            <h3>${model}</h3>
            ${metrics.error ? `<p style="color: orange;">${metrics.error}</p>` : `
            <p>MAE: <span>${metrics.mae}</span></p>
            <p>MSE: <span>${metrics.mse}</span></p>
            <p>RMSE: <span>${metrics.rmse}</span></p>
            <p>MAPE: <span>${metrics.mape}</span></p>
            <p>Forecasts: <span>${metrics.forecasts_generated}</span></p>
            `}
        </div>`;
    }
    return cards;
}

function renderActualsTable(data, preset) {
    if (!data || data.length === 0) {
        return '<p><b>No sales data found for the selected period.</b></p>';
    }

    const presetLabels = {
        'today': 'Today',
        'week': 'This Week',
        'month': 'This Month',
        'ytd': 'Year-to-Date',
        'custom': 'Custom Range'
    };

    let html = `<h3>Top Categories - ${presetLabels[preset] || 'Selected Period'}</h3>`;
    html += '<table><thead><tr><th>#</th><th>Category</th><th>Total Sales</th><th>Units Sold</th><th>Orders</th></tr></thead><tbody>';

    data.forEach((item, index) => {
        html += `<tr>
            <td>${index + 1}</td>
            <td>${item.categoryName} (${item.categoryId})</td>
            <td>${formatCurrency(item.totalSalesAmount)}</td>
            <td>${item.totalUnitsSold || '-'}</td>
            <td>${item.orderCount || '-'}</td>
        </tr>`;
    });

    html += '</tbody></table>';
    return html;
}

function formatCurrency(amount) {
    if (amount === null || amount === undefined) return '-';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}
