#!/bin/bash
# Master Infrastructure Test Runner
# Executes all infrastructure validation tests

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITES_DIR="$SCRIPT_DIR/suites"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Source configuration and utilities
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/utils/common.sh"

# Test execution configuration
PARALLEL_EXECUTION="${TEST_PARALLEL:-false}"
OUTPUT_DIR="${TEST_OUTPUT_DIR:-$SCRIPT_DIR/test-results}"
LOG_FILE="$OUTPUT_DIR/infrastructure_tests_$TIMESTAMP.log"
SUMMARY_FILE="$OUTPUT_DIR/test_summary_$TIMESTAMP.txt"

# Colors for summary
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test suite definitions
declare -A TEST_SUITES=(
    ["terraform"]="Terraform Configuration (Subtasks 1.1, 1.9)"
    ["cognito"]="Cognito User Pool (Subtask 1.2)"
    ["apigw"]="API Gateway (Subtask 1.3)"
    ["rds"]="RDS PostgreSQL (Subtasks 1.4, 1.6)"
    ["redis"]="ElastiCache Redis (Subtask 1.5)"
    ["learning_schema"]="Learning Schema (Subtask 1.7)"
    ["network"]="VPC and Security (Subtask 1.8)"
    ["docs"]="Documentation (Subtask 1.10)"
)

# Test execution order (dependencies)
TEST_ORDER=(
    "terraform"
    "network"
    "rds"
    "redis"
    "cognito"
    "apigw"
    "learning_schema"
    "docs"
)

# Initialize
initialize() {
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Start logging
    exec > >(tee -a "$LOG_FILE")
    exec 2>&1
    
    echo "========================================="
    echo "Infrastructure Validation Test Suite"
    echo "========================================="
    echo "Timestamp: $(date)"
    echo "Output Directory: $OUTPUT_DIR"
    echo "Parallel Execution: $PARALLEL_EXECUTION"
    echo "========================================="
    echo
    
    # Validate AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo -e "${RED}ERROR: AWS credentials not configured${NC}"
        exit 1
    fi
    
    # Load environment variables if available
    if [ -f "$SCRIPT_DIR/../.env.test" ]; then
        echo "Loading test environment variables..."
        source "$SCRIPT_DIR/../.env.test"
    fi
}

# Run a single test suite
run_test_suite() {
    local suite_name="$1"
    local suite_script="$SUITES_DIR/test_${suite_name}.sh"
    local suite_log="$OUTPUT_DIR/test_${suite_name}_$TIMESTAMP.log"
    
    if [ ! -f "$suite_script" ]; then
        echo -e "${RED}[SKIP]${NC} Test suite not found: $suite_name"
        return 1
    fi
    
    if [ ! -x "$suite_script" ]; then
        chmod +x "$suite_script"
    fi
    
    echo -e "${BLUE}[START]${NC} ${TEST_SUITES[$suite_name]}"
    
    # Run the test suite
    if "$suite_script" > "$suite_log" 2>&1; then
        echo -e "${GREEN}[PASS]${NC} ${TEST_SUITES[$suite_name]}"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} ${TEST_SUITES[$suite_name]}"
        echo "       See: $suite_log"
        return 1
    fi
}

# Run tests in parallel
run_tests_parallel() {
    echo "Running tests in parallel..."
    echo
    
    # Use GNU parallel if available, otherwise fallback to background jobs
    if command -v parallel >/dev/null 2>&1; then
        export -f run_test_suite
        export OUTPUT_DIR TIMESTAMP SCRIPT_DIR SUITES_DIR
        printf '%s\n' "${TEST_ORDER[@]}" | parallel -j 4 run_test_suite
    else
        # Fallback to shell background jobs
        local pids=()
        
        for suite in "${TEST_ORDER[@]}"; do
            run_test_suite "$suite" &
            pids+=($!)
        done
        
        # Wait for all tests to complete
        local failed=0
        for pid in "${pids[@]}"; do
            if ! wait "$pid"; then
                failed=$((failed + 1))
            fi
        done
        
        return $failed
    fi
}

# Run tests sequentially
run_tests_sequential() {
    echo "Running tests sequentially..."
    echo
    
    local failed=0
    
    for suite in "${TEST_ORDER[@]}"; do
        if ! run_test_suite "$suite"; then
            failed=$((failed + 1))
        fi
        echo
    done
    
    return $failed
}

# Generate summary report
generate_summary() {
    local total_suites=${#TEST_ORDER[@]}
    local passed_suites=$((total_suites - $1))
    local failed_suites=$1
    
    {
        echo "========================================="
        echo "Infrastructure Test Summary"
        echo "========================================="
        echo "Timestamp: $(date)"
        echo "Total Test Suites: $total_suites"
        echo "Passed: $passed_suites"
        echo "Failed: $failed_suites"
        echo "========================================="
        echo
        
        echo "Individual Test Results:"
        echo "------------------------"
        
        # Parse individual test logs for detailed results
        for suite in "${TEST_ORDER[@]}"; do
            local suite_log="$OUTPUT_DIR/test_${suite}_$TIMESTAMP.log"
            if [ -f "$suite_log" ]; then
                echo
                echo "${TEST_SUITES[$suite]}:"
                
                # Extract test summary from log
                if grep -q "Test Summary" "$suite_log"; then
                    sed -n '/Test Summary/,/=========/p' "$suite_log" | grep -E "(Total|Passed|Failed|Skipped)" || true
                else
                    echo "  No summary available"
                fi
            fi
        done
        
        echo
        echo "========================================="
        echo "Recommendations:"
        echo "========================================="
        
        if [ "$failed_suites" -gt 0 ]; then
            echo "❌ Some infrastructure tests failed. Please review:"
            echo
            for suite in "${TEST_ORDER[@]}"; do
                local suite_log="$OUTPUT_DIR/test_${suite}_$TIMESTAMP.log"
                if [ -f "$suite_log" ] && grep -q "\[FAIL\]" "$suite_log"; then
                    echo "- Check $suite_log for ${TEST_SUITES[$suite]} failures"
                fi
            done
        else
            echo "✅ All infrastructure tests passed!"
            echo "   Your AWS infrastructure is properly configured."
        fi
        
    } | tee "$SUMMARY_FILE"
}

# Cleanup function
cleanup() {
    # Remove empty log files
    find "$OUTPUT_DIR" -name "*.log" -size 0 -delete 2>/dev/null || true
}

# Main execution
main() {
    local exit_code=0
    
    # Initialize
    initialize
    
    # Run tests
    if [ "$PARALLEL_EXECUTION" = "true" ]; then
        run_tests_parallel || exit_code=$?
    else
        run_tests_sequential || exit_code=$?
    fi
    
    echo
    echo "========================================="
    
    # Generate summary
    generate_summary $exit_code
    
    # Cleanup
    cleanup
    
    # Final message
    echo
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ All infrastructure tests completed successfully!${NC}"
    else
        echo -e "${RED}❌ Some infrastructure tests failed. Please review the logs.${NC}"
    fi
    
    echo
    echo "Full test results available in: $OUTPUT_DIR"
    echo "Summary report: $SUMMARY_FILE"
    
    exit $exit_code
}

# Handle script arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --parallel|-p)
            TEST_PARALLEL="true"
            shift
            ;;
        --output|-o)
            TEST_OUTPUT_DIR="$2"
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --suite|-s)
            # Run specific suite only
            TEST_ORDER=("$2")
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  -p, --parallel        Run tests in parallel"
            echo "  -o, --output DIR      Output directory for results"
            echo "  -s, --suite NAME      Run specific test suite only"
            echo "  -h, --help           Show this help message"
            echo
            echo "Available test suites:"
            for suite in "${!TEST_SUITES[@]}"; do
                echo "  - $suite: ${TEST_SUITES[$suite]}"
            done
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Execute main function
main