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
        if(data.messages && data.messages.length > 0) {
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
        if(data.messages && data.messages.length > 0) {
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
