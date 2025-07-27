FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements-complete.txt /tmp/requirements-complete.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements-complete.txt

# Copy application code
COPY . /app

# Set Python path
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs

# Set default environment variables (can be overridden)
ENV NEO4J_URI=bolt://neo4j:7687
ENV NEO4J_PASSWORD=neo4jpassword
ENV DATABASE_URL=postgresql://learntrac:learntrac@postgres:5432/learntrac
ENV OPENAI_API_KEY=""
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]