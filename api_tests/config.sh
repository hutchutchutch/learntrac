#!/bin/bash

# LearnTrac API Test Configuration
# This file contains all configuration variables for API testing

# API Base URLs
export API_BASE_URL="${API_BASE_URL:-http://localhost:8001}"
export TRAC_BASE_URL="${TRAC_BASE_URL:-http://localhost:8000}"
export WS_BASE_URL="${WS_BASE_URL:-ws://localhost:8001}"

# API Version
export API_VERSION="v1"
export API_PATH="/api/learntrac/${API_VERSION}"

# Test User Credentials
export TEST_USER_STUDENT="${TEST_USER_STUDENT:-student1}"
export TEST_PASS_STUDENT="${TEST_PASS_STUDENT:-password123}"
export TEST_USER_INSTRUCTOR="${TEST_USER_INSTRUCTOR:-instructor1}"
export TEST_PASS_INSTRUCTOR="${TEST_PASS_INSTRUCTOR:-password456}"

# Test Data
export TEST_CONCEPT_ID="${TEST_CONCEPT_ID:-1234}"
export TEST_EXERCISE_ID="${TEST_EXERCISE_ID:-ex-123}"
export TEST_USER_ID="${TEST_USER_ID:-user123}"

# Output Configuration
export OUTPUT_DIR="${OUTPUT_DIR:-./test_results}"
export VERBOSE="${VERBOSE:-false}"
export SAVE_RESPONSES="${SAVE_RESPONSES:-true}"

# Timing Configuration
export REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-30}"
export RETRY_COUNT="${RETRY_COUNT:-3}"
export RETRY_DELAY="${RETRY_DELAY:-2}"

# Colors for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m' # No Color

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Test mode (development, staging, production)
export TEST_MODE="${TEST_MODE:-development}"

# Rate limiting test configuration
export RATE_LIMIT_TEST="${RATE_LIMIT_TEST:-false}"
export RATE_LIMIT_REQUESTS="${RATE_LIMIT_REQUESTS:-100}"

# WebSocket test configuration
export WS_TEST_DURATION="${WS_TEST_DURATION:-30}"
export WS_AUDIO_FILE="${WS_AUDIO_FILE:-./test_data/sample_audio.mp3}"

# Feature flags
export TEST_AUTH="${TEST_AUTH:-true}"
export TEST_CONCEPTS="${TEST_CONCEPTS:-true}"
export TEST_PROGRESS="${TEST_PROGRESS:-true}"
export TEST_CHAT="${TEST_CHAT:-true}"
export TEST_ANALYTICS="${TEST_ANALYTICS:-true}"
export TEST_KNOWLEDGE="${TEST_KNOWLEDGE:-true}"
export TEST_EXERCISES="${TEST_EXERCISES:-true}"
export TEST_ADAPTIVE="${TEST_ADAPTIVE:-true}"
export TEST_WEBSOCKET="${TEST_WEBSOCKET:-true}"
export TEST_MISC="${TEST_MISC:-true}"

# Performance test configuration
export PERF_TEST="${PERF_TEST:-false}"
export PERF_CONCURRENT="${PERF_CONCURRENT:-10}"
export PERF_DURATION="${PERF_DURATION:-60}"

# Debug configuration
export DEBUG="${DEBUG:-false}"
export CURL_OPTIONS="${CURL_OPTIONS:--s}"

if [ "$DEBUG" = "true" ]; then
    CURL_OPTIONS="-v"
fi

# Test data directory
export TEST_DATA_DIR="${TEST_DATA_DIR:-./test_data}"
mkdir -p "$TEST_DATA_DIR"

echo -e "${GREEN}Configuration loaded successfully${NC}"
echo -e "API Base URL: ${BLUE}${API_BASE_URL}${NC}"
echo -e "Test Mode: ${BLUE}${TEST_MODE}${NC}"