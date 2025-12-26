# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libmupdf-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install Python dependencies
RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create upload directories (both for local and volume-based storage)
RUN mkdir -p static/uploads/products static/uploads/recipes static/uploads/books/pdfs static/uploads/books/covers static/uploads/slides/default && \
    mkdir -p /data/uploads 2>/dev/null || true

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose port (Railway will set PORT env var, default to 8080)
EXPOSE 8080

# Start gunicorn (Railway sets PORT env var)
# Use single worker and longer timeout to prevent startup issues
# Remove --preload to allow faster worker startup
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --timeout 300 --workers 1 --worker-class sync --access-logfile - --error-logfile - --log-level info
