# Multi-stage Dockerfile for FederalRunner MCP Server
# Optimized for Google Cloud Run deployment with WebKit browser

FROM python:3.11-slim as base

# Install system dependencies for Playwright WebKit
# CRITICAL: Use WebKit (NOT Chromium) - FSA website blocks headless Chromium
# Installing all WebKit dependencies manually since Cloud Build doesn't support playwright install --with-deps
RUN apt-get update && apt-get install -y \
    # Basic tools
    wget \
    gnupg \
    ca-certificates \
    # WebKit-specific dependencies (from Playwright ubuntu20.04 dependency list)
    libasound2t64 \
    libatk-bridge2.0-0t64 \
    libatk1.0-0t64 \
    libatspi2.0-0t64 \
    libcairo2 \
    libcups2t64 \
    libdbus-1-3 \
    libdrm2 \
    libegl1 \
    libgbm1 \
    libglib2.0-0t64 \
    libgtk-3-0t64 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    libxkbcommon0 \
    # GStreamer (required for video/audio in WebKit)
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgstreamer-plugins-bad1.0-0 \
    libopus0 \
    libharfbuzz0b \
    libharfbuzz-icu0 \
    libhyphen0 \
    libmanette-0.2-0 \
    libflite1 \
    libwoff1 \
    libxslt1.1 \
    libevent-2.1-7t64 \
    libgles2 \
    # Additional libraries WebKit needs (from Playwright warnings)
    libicu76 \
    libwebpdemux2 \
    libjpeg62-turbo \
    libwebpmux3 \
    libwebp7 \
    libenchant-2-2 \
    libsecret-1-0 \
    libffi8 \
    libjson-glib-1.0-0 \
    # Fonts
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright WebKit browser binaries only (dependencies already installed above)
# CRITICAL: FSA website only works in headless mode with WebKit
RUN playwright install webkit

# Copy application code
COPY src/ ./src/

# Copy wizards directory (from shared location - see deployment script)
# This will be populated by the deployment script copying ../../wizards/
COPY wizards/ ./wizards/

# Verify wizards are present (critical for execution)
RUN echo "Verifying wizards directory structure..."
RUN ls -la /app/wizards/ || echo "WARNING: wizards directory not found!"
RUN test -d /app/wizards/wizard-structures || echo "ERROR: wizard-structures not found!"
RUN test -d /app/wizards/data-schemas || echo "ERROR: data-schemas not found!"
RUN echo "Wizard structures:" && ls -la /app/wizards/wizard-structures/ || exit 1
RUN echo "Data schemas:" && ls -la /app/wizards/data-schemas/ || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV FEDERALRUNNER_WIZARDS_DIR=/app/wizards
ENV FEDERALRUNNER_BROWSER_TYPE=webkit
ENV FEDERALRUNNER_HEADLESS=true
ENV FEDERALRUNNER_SAVE_SCREENSHOTS=false
ENV FEDERALRUNNER_EXECUTION_TIMEOUT=60

# Expose port (Cloud Run uses PORT env var, default to 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health', timeout=5.0)" || exit 1

# Run the FastAPI server
CMD uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8080}
