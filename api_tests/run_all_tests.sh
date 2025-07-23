#!/bin/bash

# LearnTrac API Test Suite Runner
# This script runs all API tests and generates a comprehensive report

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source configuration
source "$SCRIPT_DIR/config.sh"

# Test suite results
TOTAL_PASSED=0
TOTAL_FAILED=0
SUITE_RESULTS=()

# Function to run a test suite
run_test_suite() {
    local suite_name=$1
    local test_script=$2
    
    echo ""
    echo "========================================"
    echo -e "${BLUE}Running Test Suite: ${suite_name}${NC}"
    echo "========================================"
    
    # Run the test script and capture output
    local output_file="${OUTPUT_DIR}/${suite_name}_output.log"
    
    if bash "$test_script" > "$output_file" 2>&1; then
        local exit_code=$?
    else
        local exit_code=$?
    fi
    
    # Parse results from output
    local passed=$(grep -E "Passed:.*[0-9]+" "$output_file" | grep -oE "[0-9]+" | tail -1 || echo "0")
    local failed=$(grep -E "Failed:.*[0-9]+" "$output_file" | grep -oE "[0-9]+" | tail -1 || echo "0")
    
    # Update totals
    TOTAL_PASSED=$((TOTAL_PASSED + passed))
    TOTAL_FAILED=$((TOTAL_FAILED + failed))
    
    # Store result
    SUITE_RESULTS+=("$suite_name|$passed|$failed")
    
    # Display summary
    if [ "$failed" -eq 0 ]; then
        print_status "SUCCESS" "$suite_name: All tests passed ($passed/$passed)"
    else
        print_status "FAIL" "$suite_name: $failed tests failed ($passed passed)"
    fi
    
    # Show output if verbose
    if [ "$VERBOSE" = "true" ]; then
        echo "--- Output ---"
        cat "$output_file"
        echo "--- End Output ---"
    fi
}

# Function to generate final report
generate_final_report() {
    local report_file="${OUTPUT_DIR}/test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "========================================"
        echo "LearnTrac API Test Report"
        echo "========================================"
        echo "Date: $(date)"
        echo "Environment: $TEST_MODE"
        echo "API Base URL: $API_BASE_URL"
        echo ""
        echo "Overall Results:"
        echo "Total Passed: $TOTAL_PASSED"
        echo "Total Failed: $TOTAL_FAILED"
        echo "Success Rate: $(echo "scale=2; $TOTAL_PASSED * 100 / ($TOTAL_PASSED + $TOTAL_FAILED)" | bc)%"
        echo ""
        echo "Test Suite Results:"
        echo "----------------------------------------"
        printf "%-30s %10s %10s\n" "Suite Name" "Passed" "Failed"
        echo "----------------------------------------"
        
        for result in "${SUITE_RESULTS[@]}"; do
            IFS='|' read -r suite passed failed <<< "$result"
            printf "%-30s %10s %10s\n" "$suite" "$passed" "$failed"
        done
        
        echo "----------------------------------------"
        echo ""
        
        if [ $TOTAL_FAILED -eq 0 ]; then
            echo "Result: ALL TESTS PASSED ✓"
        else
            echo "Result: SOME TESTS FAILED ✗"
            echo ""
            echo "Failed Test Details:"
            echo "----------------------------------------"
            
            # Extract failed test details from logs
            for log_file in "$OUTPUT_DIR"/*_output.log; do
                if grep -q "FAIL" "$log_file"; then
                    echo ""
                    echo "From $(basename "$log_file"):"
                    grep "✗" "$log_file" || grep "FAIL" "$log_file" | head -10
                fi
            done
        fi
        
        echo ""
        echo "Full logs available in: $OUTPUT_DIR"
        echo "========================================"
    } | tee "$report_file"
    
    echo ""
    print_status "INFO" "Report saved to: $report_file"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "INFO" "Checking prerequisites..."
    
    # Check for required commands
    local required_commands=("curl" "jq" "bc")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            print_status "FAIL" "Required command not found: $cmd"
            exit 1
        fi
    done
    
    # Check API availability
    print_status "INFO" "Checking API availability at $API_BASE_URL..."
    
    if curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}${API_PATH}/health" | grep -q "200"; then
        print_status "SUCCESS" "API is available"
    else
        print_status "WARN" "API may not be available, continuing anyway..."
    fi
    
    # Create test data directory
    mkdir -p "$TEST_DATA_DIR"
    
    # Create sample test files if needed
    if [ ! -f "$TEST_DATA_DIR/sample_audio.mp3" ]; then
        # Create a dummy audio file for testing
        echo "dummy audio content" > "$TEST_DATA_DIR/sample_audio.mp3"
    fi
}

# Main execution
main() {
    echo -e "${GREEN}LearnTrac API Test Suite${NC}"
    echo "========================================"
    
    # Check prerequisites
    check_prerequisites
    
    # Clear previous results
    SUITE_RESULTS=()
    
    # Run test suites based on configuration
    if [ "$TEST_AUTH" = "true" ]; then
        run_test_suite "Authentication" "$SCRIPT_DIR/auth/test_auth.sh"
    fi
    
    if [ "$TEST_CONCEPTS" = "true" ]; then
        run_test_suite "Learning_Concepts" "$SCRIPT_DIR/concepts/test_concepts.sh"
    fi
    
    if [ "$TEST_PROGRESS" = "true" ]; then
        run_test_suite "Progress_Tracking" "$SCRIPT_DIR/progress/test_progress.sh"
    fi
    
    if [ "$TEST_CHAT" = "true" ]; then
        run_test_suite "AI_Chat" "$SCRIPT_DIR/chat/test_chat.sh"
    fi
    
    if [ "$TEST_ANALYTICS" = "true" ]; then
        run_test_suite "Analytics" "$SCRIPT_DIR/analytics/test_analytics.sh"
    fi
    
    if [ "$TEST_KNOWLEDGE" = "true" ] && [ -f "$SCRIPT_DIR/knowledge/test_knowledge.sh" ]; then
        run_test_suite "Knowledge_Graph" "$SCRIPT_DIR/knowledge/test_knowledge.sh"
    fi
    
    if [ "$TEST_EXERCISES" = "true" ] && [ -f "$SCRIPT_DIR/exercises/test_exercises.sh" ]; then
        run_test_suite "Exercises" "$SCRIPT_DIR/exercises/test_exercises.sh"
    fi
    
    if [ "$TEST_ADAPTIVE" = "true" ] && [ -f "$SCRIPT_DIR/adaptive/test_adaptive.sh" ]; then
        run_test_suite "Adaptive_Learning" "$SCRIPT_DIR/adaptive/test_adaptive.sh"
    fi
    
    if [ "$TEST_WEBSOCKET" = "true" ] && [ -f "$SCRIPT_DIR/websocket/test_websocket.sh" ]; then
        run_test_suite "WebSocket" "$SCRIPT_DIR/websocket/test_websocket.sh"
    fi
    
    # Performance tests if enabled
    if [ "$PERF_TEST" = "true" ]; then
        if [ -f "$SCRIPT_DIR/performance/test_performance.sh" ]; then
            run_test_suite "Performance" "$SCRIPT_DIR/performance/test_performance.sh"
        fi
    fi
    
    # Generate final report
    generate_final_report
    
    # Exit with appropriate code
    if [ $TOTAL_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            export VERBOSE=true
            shift
            ;;
        --env)
            export TEST_MODE="$2"
            shift 2
            ;;
        --url)
            export API_BASE_URL="$2"
            shift 2
            ;;
        --auth-only)
            export TEST_AUTH=true
            export TEST_CONCEPTS=false
            export TEST_PROGRESS=false
            export TEST_CHAT=false
            export TEST_ANALYTICS=false
            export TEST_KNOWLEDGE=false
            export TEST_EXERCISES=false
            export TEST_ADAPTIVE=false
            export TEST_WEBSOCKET=false
            shift
            ;;
        --suite)
            # Run only specific suite
            case $2 in
                auth) export TEST_AUTH=true ;;
                concepts) export TEST_CONCEPTS=true ;;
                progress) export TEST_PROGRESS=true ;;
                chat) export TEST_CHAT=true ;;
                analytics) export TEST_ANALYTICS=true ;;
                knowledge) export TEST_KNOWLEDGE=true ;;
                exercises) export TEST_EXERCISES=true ;;
                adaptive) export TEST_ADAPTIVE=true ;;
                websocket) export TEST_WEBSOCKET=true ;;
                *) print_status "WARN" "Unknown suite: $2" ;;
            esac
            # Disable others
            for suite in AUTH CONCEPTS PROGRESS CHAT ANALYTICS KNOWLEDGE EXERCISES ADAPTIVE WEBSOCKET; do
                var_name="TEST_$suite"
                if [ "${!var_name}" != "true" ]; then
                    export "TEST_$suite=false"
                fi
            done
            shift 2
            ;;
        --perf)
            export PERF_TEST=true
            shift
            ;;
        --rate-limit)
            export RATE_LIMIT_TEST=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --verbose, -v         Enable verbose output"
            echo "  --env ENV            Set test environment (development, staging, production)"
            echo "  --url URL            Set API base URL"
            echo "  --auth-only          Run only authentication tests"
            echo "  --suite SUITE        Run only specific test suite"
            echo "  --perf               Enable performance tests"
            echo "  --rate-limit         Enable rate limiting tests"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Available test suites:"
            echo "  auth        Authentication tests"
            echo "  concepts    Learning concepts tests"
            echo "  progress    Progress tracking tests"
            echo "  chat        AI chat interface tests"
            echo "  analytics   Analytics and reporting tests"
            echo "  knowledge   Knowledge graph tests"
            echo "  exercises   Exercise tests"
            echo "  adaptive    Adaptive learning tests"
            echo "  websocket   WebSocket tests"
            exit 0
            ;;
        *)
            print_status "WARN" "Unknown option: $1"
            shift
            ;;
    esac
done

# Run main function
main