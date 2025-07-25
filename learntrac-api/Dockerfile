FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY logging.conf .

# Copy scripts
COPY scripts/ ./scripts/
RUN chmod +x ./scripts/*.sh

# Create necessary directories
RUN mkdir -p /var/log/api

# Legacy script location for backward compatibility
RUN ln -s /app/scripts/start-api.sh /usr/local/bin/start-api.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD /app/scripts/health-check-api.sh || exit 1

# Expose port
EXPOSE 8001

# Start API
CMD ["/app/scripts/start-api.sh"]