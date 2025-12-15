FROM python:3.11-slim

# 1. System dependencies (required for prophet)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Set workdir
WORKDIR /app

# 3. Copy requirements first (layer caching)
COPY requirements.txt .

# 4. Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY . .

# 6. Expose port
EXPOSE 8090

# 7. Run FastAPI
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8090"]
