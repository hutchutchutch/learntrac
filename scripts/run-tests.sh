#!/bin/bash
# run-tests.sh - Master test runner for LearnTrac

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
COMPOSE_FILE="docker-compose.test.yml"
LOG_FILE="test-results-$(date +%Y%m%d-%H%M%S).log"

# Helper functions
echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    echo_info "Cleaning up test environment..."
    docker-compose -f "$COMPOSE_FILE" down -v > /dev/null 2>&1 || true
}

# Set trap for cleanup
trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check .env file
    if [ ! -f .env ]; then
        echo_warning ".env file not found. Creating from template..."
        if [ -f .env.template ]; then
            cp .env.template .env
            echo_warning "Please edit .env file with your configuration values"
            exit 1
        else
            echo_error ".env.template not found"
            exit 1
        fi
    fi
    
    echo_success "Prerequisites check passed"
}

# Build containers
build_containers() {
    echo_info "Building containers..."
    
    if docker-compose -f "$COMPOSE_FILE" build; then
        echo_success "Containers built successfully"
    else
        echo_error "Failed to build containers"
        exit 1
    fi
}

# Start test environment
start_environment() {
    echo_info "Starting test environment..."
    
    if docker-compose -f "$COMPOSE_FILE" up -d; then
        echo_success "Test environment started"
        
        # Show container status
        echo_info "Container status:"
        docker-compose -f "$COMPOSE_FILE" ps
    else
        echo_error "Failed to start test environment"
        exit 1
    fi
}

# Run test suite
run_test_suite() {
    local suite=$1
    local script=$2
    
    echo ""
    echo_info "Running $suite..."
    
    if [ -x "$script" ]; then
        if $script >> "$LOG_FILE" 2>&1; then
            echo_success "$suite passed"
            return 0
        else
            echo_error "$suite failed (see $LOG_FILE for details)"
            return 1
        fi
    else
        echo_warning "$suite script not found or not executable: $script"
        return 1
    fi
}

# Main execution
main() {
    echo "========================================="
    echo "LearnTrac Test Suite Runner"
    echo "========================================="
    echo "Log file: $LOG_FILE"
    echo ""
    
    # Initialize log
    echo "Test run started at $(date)" > "$LOG_FILE"
    
    # Check prerequisites
    check_prerequisites
    
    # Build containers
    build_containers
    
    # Start environment
    start_environment
    
    # Wait for services to be ready
    echo_info "Waiting for services to initialize..."
    sleep 10
    
    # Run test suites
    local failed=0
    
    # Integration tests
    run_test_suite "Integration Tests" "./scripts/integration-test.sh" || ((failed++))
    
    # API endpoint tests
    run_test_suite "API Endpoint Tests" "./tests/api/test_api_endpoints.sh" || ((failed++))
    
    # Trac endpoint tests
    run_test_suite "Trac Endpoint Tests" "./tests/trac/test_trac_endpoints.sh" || ((failed++))
    
    # Existing API test suite
    if [ -d "api_tests" ]; then
        run_test_suite "Legacy API Tests" "./api_tests/run_all_tests.sh" || ((failed++))
    fi
    
    # Container health verification
    echo ""
    echo_info "Final container health check..."
    docker-compose -f "$COMPOSE_FILE" ps
    
    # Summary
    echo ""
    echo "========================================="
    echo "Test Summary"
    echo "========================================="
    
    if [ $failed -eq 0 ]; then
        echo_success "All test suites passed!"
        echo_info "Test results saved to: $LOG_FILE"
        exit 0
    else
        echo_error "$failed test suite(s) failed!"
        echo_info "Check $LOG_FILE for detailed results"
        
        # Show recent errors from log
        echo ""
        echo "Recent errors:"
        grep -i "error\|fail" "$LOG_FILE" | tail -10
        
        exit 1
    fi
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --quick        Skip container rebuild"
        echo "  --keep         Keep containers running after tests"
        echo ""
        exit 0
        ;;
    --quick)
        echo_info "Quick mode: Skipping container rebuild"
        build_containers() { echo_info "Skipping container build (--quick mode)"; }
        ;;
    --keep)
        echo_info "Keep mode: Containers will remain running after tests"
        trap - EXIT
        ;;
esac

# Run main function
main