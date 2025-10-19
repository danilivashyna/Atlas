# Atlas Semantic Space API - Dockerfile
# Multi-stage build for production deployment

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
COPY setup.py .
COPY pyproject.toml .
COPY src/ src/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi[all] uvicorn[standard] pydantic && \
    pip install --no-cache-dir -e .

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 atlas && \
    chown -R atlas:atlas /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=atlas:atlas src/ src/
COPY --chown=atlas:atlas setup.py .
COPY --chown=atlas:atlas pyproject.toml .

# Install the package
RUN pip install --no-cache-dir -e .

# Switch to non-root user
USER atlas

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ATLAS_LOG_LEVEL=info

# Run the API server
CMD ["uvicorn", "atlas.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
