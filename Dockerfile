# SPDX-License-Identifier: AGPL-3.0-or-later
# Multi-stage build: reduces final image size by ~60%

FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install to /build/install
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 atlas && chown -R atlas:atlas /app

# Copy only necessary files from builder
COPY --from=builder --chown=atlas:atlas /root/.local /home/atlas/.local
COPY --chown=atlas:atlas . .

# Set environment
ENV PATH=/home/atlas/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ATLAS_LOG_LEVEL=INFO \
    ATLAS_MEMORY_BACKEND=sqlite

# Switch to non-root user
USER atlas

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Expose port
EXPOSE 8010

# Run
CMD ["uvicorn", "src.atlas.api.app:app", "--host", "0.0.0.0", "--port", "8010"]
