#!/usr/bin/env bash
set -euo pipefail

ENV_PATH="/trac"
GUARD="$ENV_PATH/.initialized"

echo "================================================"
echo "Trac Entrypoint Script"
echo "================================================"

# Install dependencies first
echo "Installing dependencies..."
pip install --quiet trac==1.4.3 psycopg2

# Install plugin if exists
if ls /plugins/PDFUploadMacro*.egg 1> /dev/null 2>&1; then
    echo "Installing PDF upload plugin..."
    easy_install /plugins/PDFUploadMacro*.egg
fi

# Check if already initialized
if [ ! -f "$GUARD" ]; then
  echo "⚙️  Initializing Trac environment..."
  
  # Clean up any partial initialization
  if [ -f "$ENV_PATH/VERSION" ] && [ ! -f "$GUARD" ]; then
    echo "🧹 Cleaning up partial initialization..."
    rm -rf "$ENV_PATH"/*
  fi
  
  # Build PostgreSQL connection string
  DB_URL="postgres://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT:-5432}/${DB_NAME}"
  
  # Initialize Trac
  trac-admin "$ENV_PATH" initenv learntrac "$DB_URL" || {
    echo "⚠️  Database may already contain Trac tables. Trying to deploy without init..."
    # Create minimal environment structure
    mkdir -p "$ENV_PATH"/{attachments,chrome,conf,htdocs,log,plugins,templates}
    
    # Create VERSION file
    echo "Trac Environment Version 1" > "$ENV_PATH/VERSION"
    
    # Create minimal trac.ini
    if [ ! -f "$ENV_PATH/conf/trac.ini" ]; then
      cat > "$ENV_PATH/conf/trac.ini" << EOF
[trac]
database = $DB_URL
[components]
pdfuploadmacro.* = enabled
EOF
    fi
  }
  
  # Create necessary directories
  mkdir -p "$ENV_PATH/log" "$ENV_PATH/attachments" "$ENV_PATH/cache" "$ENV_PATH/chrome"
  chmod -R 777 "$ENV_PATH/log"
  
  # Copy custom config if provided
  if [ -f /custom-config/trac.ini ]; then
    echo "📋 Applying custom configuration..."
    cp /custom-config/trac.ini "$ENV_PATH/conf/trac.ini"
  fi
  
  # Mark as initialized
  touch "$GUARD"
  echo "✅ Trac environment initialized successfully!"
else
  echo "✅ Using existing Trac environment"
fi

echo "🚀 Starting Tracd on port 8000..."
exec tracd --port 8000 "$ENV_PATH"