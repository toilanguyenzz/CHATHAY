FROM python:3.12-slim

WORKDIR /app

# Install system deps for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories for temp files and persistent data
RUN mkdir -p temp/audio /data

# SQLite token store location — mount Railway Volume tại /data
ENV DATA_DIR=/data

CMD ["python", "-m", "uvicorn", "zalo_webhook:app", "--host", "0.0.0.0", "--port", "8000"]
