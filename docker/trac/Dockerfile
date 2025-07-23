FROM python:2.7-slim-buster

# Fix Debian archive issues for old release
RUN echo "deb http://archive.debian.org/debian/ buster main" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security buster/updates main" >> /etc/apt/sources.list && \
    echo "Acquire::Check-Valid-Until false;" > /etc/apt/apt.conf.d/99no-check-valid-until

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    subversion \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Trac and dependencies
RUN pip install --no-cache-dir \
    Trac==1.4.4 \
    psycopg2==2.8.6 \
    Genshi==0.7.7 \
    Babel==2.9.1 \
    Pygments==2.5.2 \
    pytz

# Create Trac environment directory
RUN mkdir -p /var/trac/projects

# Copy configuration and scripts
COPY scripts/start-trac.sh /usr/local/bin/
COPY scripts/init-trac.py /usr/local/bin/
COPY config/trac.ini.template /app/config/
COPY config/trac.ini /app/config/

# Copy plugins
COPY plugins/ /app/plugins/

# Copy templates
COPY templates/ /app/templates/

RUN chmod +x /usr/local/bin/start-trac.sh

# Create health check script
COPY scripts/health-check.py /usr/local/bin/
RUN chmod +x /usr/local/bin/health-check.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python /usr/local/bin/health-check.py || exit 1

CMD ["/usr/local/bin/start-trac.sh"]