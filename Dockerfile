# Screenshot Organizer Docker Image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install package in development mode
RUN pip install -e .

# Create directories for models and sessions
RUN mkdir -p /app/models /app/sessions /app/logs

# Create a non-root user
RUN useradd -m -u 1000 screenshot_user && \
    chown -R screenshot_user:screenshot_user /app

USER screenshot_user

# Set default environment variables
ENV PYTHONPATH=/app/src \
    LOG_LEVEL=INFO \
    MODEL_CACHE_DIR=/app/models

# Expose port for MCP server (if needed)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.utils.config import load_config; load_config()" || exit 1

# Default command: run CLI interface
CMD ["python", "-m", "src.cli_interface"]
