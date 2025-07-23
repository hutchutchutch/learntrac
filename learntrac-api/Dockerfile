FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
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

# Run database migrations on startup
COPY scripts/start-api.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-api.sh

# Expose port
EXPOSE 8001

# Start API
CMD ["/usr/local/bin/start-api.sh"]