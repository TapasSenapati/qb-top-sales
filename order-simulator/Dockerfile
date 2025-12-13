FROM python:3.11-slim

WORKDIR /app
COPY simulate_orders.py .
RUN pip install --no-cache-dir requests

CMD ["python", "simulate_orders.py"]