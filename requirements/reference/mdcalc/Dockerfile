# Multi-stage Dockerfile for MDCalc MCP Server
# Optimized for Google Cloud Run deployment

FROM python:3.11-slim as base

# Install system dependencies for Playwright and Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (chromium only)
# Note: Install dependencies manually instead of --with-deps to avoid package conflicts
RUN playwright install chromium

# Copy application code
COPY src/ ./src/

# Verify calculator catalog is present (debugging)
RUN ls -la /app/src/calculator-catalog/ || echo "WARNING: calculator-catalog directory not found!"
RUN test -f /app/src/calculator-catalog/mdcalc_catalog.json || echo "ERROR: mdcalc_catalog.json not found!"
RUN if [ ! -f /app/src/calculator-catalog/mdcalc_catalog.json ]; then echo "File not found, checking parent dir:"; ls -la /app/src/; fi

# Create directory for auth state (if needed)
RUN mkdir -p /app/auth

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port (Cloud Run uses PORT env var, default to 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health', timeout=5.0)" || exit 1

# Run the FastAPI server
CMD uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8080}
