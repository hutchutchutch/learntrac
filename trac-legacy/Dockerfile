FROM python:2.7-slim-buster

# Update to archived repositories for Debian Buster
RUN echo "deb http://archive.debian.org/debian buster main" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security buster/updates main" >> /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian buster-updates main" >> /etc/apt/sources.list

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    subversion \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Trac configuration
COPY config/ /etc/trac/

# Copy custom Trac plugins if any
COPY plugins/ /usr/local/lib/python2.7/site-packages/

# Create Trac environment directory
RUN mkdir -p /var/trac/projects

# Copy startup script
COPY scripts/start-trac.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-trac.sh

# Expose port
EXPOSE 8000

# Start Trac
CMD ["/usr/local/bin/start-trac.sh"]