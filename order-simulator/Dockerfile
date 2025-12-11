FROM python:3.12-slim

WORKDIR /app

# Install runtime deps
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY simulate_orders.py .

CMD ["python", "simulate_orders.py"]
