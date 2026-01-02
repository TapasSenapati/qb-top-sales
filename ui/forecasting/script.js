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
});

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
