# LearnTrac API Installation Guide

## Python Version Requirements

This project requires **Python 3.13** or higher.

## Installation Steps

### 1. Check Python Version

First, ensure you have Python 3.13 installed:

```bash
python3 --version
# Should output: Python 3.13.x
```

### 2. Use the Setup Script (Recommended)

We provide a setup script that handles the virtual environment and dependencies:

```bash
./setup.sh
```

### 3. Manual Installation

If you prefer to install manually:

```bash
# Create virtual environment with Python 3.13
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
python -m pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- Database credentials
- Redis URL
- AWS Cognito settings
- Neo4j credentials (if using)
- OpenAI API key (if using AI features)

## Troubleshooting

### Wrong Python Version

If you see errors about Python 2.7 or an old pip version:

1. Make sure you're using `python3` instead of `python`
2. Use `python3 -m pip` instead of just `pip`
3. Ensure your virtual environment is activated

### Package Compatibility

If you encounter package compatibility issues with Python 3.13:

1. The requirements.txt uses flexible version constraints (>=) to allow compatible versions
2. You can check for the latest compatible versions:
   ```bash
   python -m pip install fastapi --upgrade
   python -m pip install uvicorn[standard] --upgrade
   # etc.
   ```

### Missing System Dependencies

Some packages require system libraries:

**macOS:**
```bash
brew install postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y gcc libpq-dev python3-dev
```

**CentOS/RHEL:**
```bash
sudo yum install -y gcc postgresql-devel python3-devel
```

## Running the API

Once installed, run the API:

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run with auto-reload (development)
python -m uvicorn src.main:app --reload --port 8001

# Or run production server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --workers 4
```

## Docker Alternative

If you prefer using Docker (no Python installation required):

```bash
docker-compose up
```

This will handle all dependencies automatically.