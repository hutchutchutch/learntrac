#!/bin/bash

# Setup script for LearnTrac API with Python 3.13

echo "Setting up LearnTrac API with Python 3.13..."

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.13 first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python version: $PYTHON_VERSION"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
python -m pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env with your configuration values."
fi

echo ""
echo "Setup complete! To start using the API:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Edit .env with your configuration"
echo "3. Run the API: python -m uvicorn src.main:app --reload --port 8001"