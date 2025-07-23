#!/bin/bash

# Student Progress Tracking API Tests

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source common utilities
source "$SCRIPT_DIR/../utils/common.sh"

# Test counters
PASSED=0
FAILED=0

# Test: Get overall progress
test_get_overall_progress() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/progress")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "user_id overall_progress milestones recent_activity learning_velocity"; then
            # Verify progress structure
            local total_concepts=$(echo "$response" | jq -r '.overall_progress.total_concepts')
            if [ "$total_concepts" -ge 0 ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Get progress with timeframe filter
test_get_progress_timeframe() {
    if ! authenticate; then
        return 1
    fi
    
    local timeframes=("week" "month" "quarter" "year" "all")
    
    for timeframe in "${timeframes[@]}"; do
        local response=$(make_request "GET" "/progress?timeframe=$timeframe")
        local status=$?
        
        if [ $status -ne 200 ]; then
            print_status "FAIL" "Failed to get progress for timeframe: $timeframe"
            return 1
        fi
        
        if ! validate_json "$response" "user_id overall_progress"; then
            return 1
        fi
    done
    
    return 0
}

# Test: Get progress for specific milestone
test_get_progress_milestone() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/progress?milestone=API%20Development")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "milestones"; then
            # Check milestone data
            local milestone_count=$(echo "$response" | jq '.milestones | length')
            if [ "$milestone_count" -ge 0 ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Get progress for specific user (instructor view)
test_get_user_progress_instructor() {
    # Authenticate as instructor
    if ! authenticate "$TEST_USER_INSTRUCTOR" "$TEST_PASS_INSTRUCTOR"; then
        return 1
    fi
    
    local response=$(make_request "GET" "/progress/${TEST_USER_ID}")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "user_id overall_progress"; then
            # Verify user ID matches
            local response_user_id=$(echo "$response" | jq -r '.user_id')
            if [ "$response_user_id" = "$TEST_USER_ID" ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Get other user's progress as student (should fail)
test_get_user_progress_unauthorized() {
    # Authenticate as student
    if ! authenticate; then
        return 1
    fi
    
    # Try to access another user's progress
    local response=$(make_request "GET" "/progress/other_user_123")
    local status=$?
    
    if [ $status -eq 403 ]; then
        return 0
    fi
    
    return 1
}

# Test: Get progress history
test_get_progress_history() {
    if ! authenticate; then
        return 1
    fi
    
    # Get history for last 30 days
    local start_date=$(date -u -d "30 days ago" +"%Y-%m-%d" 2>/dev/null || date -u -v-30d +"%Y-%m-%d")
    local end_date=$(date -u +"%Y-%m-%d")
    
    local response=$(make_request "GET" "/progress/history?start_date=${start_date}&end_date=${end_date}&granularity=week")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "history totals"; then
            # Verify history array exists
            local history_count=$(echo "$response" | jq '.history | length')
            if [ "$history_count" -ge 0 ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Get progress history with different granularities
test_progress_history_granularity() {
    if ! authenticate; then
        return 1
    fi
    
    local granularities=("day" "week" "month")
    local start_date=$(date -u -d "7 days ago" +"%Y-%m-%d" 2>/dev/null || date -u -v-7d +"%Y-%m-%d")
    local end_date=$(date -u +"%Y-%m-%d")
    
    for granularity in "${granularities[@]}"; do
        local response=$(make_request "GET" "/progress/history?start_date=${start_date}&end_date=${end_date}&granularity=$granularity")
        local status=$?
        
        if [ $status -ne 200 ]; then
            print_status "FAIL" "Failed to get history with granularity: $granularity"
            return 1
        fi
    done
    
    return 0
}

# Test: Verify progress calculations
test_progress_calculations() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/progress")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Extract values
    local total=$(echo "$response" | jq -r '.overall_progress.total_concepts')
    local completed=$(echo "$response" | jq -r '.overall_progress.completed_concepts')
    local mastered=$(echo "$response" | jq -r '.overall_progress.mastered_concepts')
    local completion_pct=$(echo "$response" | jq -r '.overall_progress.completion_percentage')
    
    # Verify calculations
    if [ "$total" -gt 0 ]; then
        local calculated_pct=$(echo "scale=1; $completed * 100 / $total" | bc)
        local pct_diff=$(echo "scale=1; $completion_pct - $calculated_pct" | bc | tr -d -)
        
        # Allow small rounding difference
        if (( $(echo "$pct_diff < 0.5" | bc -l) )); then
            return 0
        fi
    else
        # No concepts is valid
        return 0
    fi
    
    return 1
}

# Test: Progress recommendations
test_progress_recommendations() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/progress")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check recommendations exist
    local recommendations=$(echo "$response" | jq '.recommendations')
    if [ "$recommendations" != "null" ]; then
        # Verify recommendation structure
        local rec_count=$(echo "$recommendations" | jq 'length')
        if [ "$rec_count" -ge 0 ]; then
            # Check first recommendation has required fields
            if [ "$rec_count" -gt 0 ]; then
                local first_rec=$(echo "$recommendations" | jq '.[0]')
                if echo "$first_rec" | jq -e '.concept_id, .title, .reason' >/dev/null 2>&1; then
                    return 0
                fi
            else
                # No recommendations is also valid
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Learning velocity tracking
test_learning_velocity() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/progress")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check learning velocity
    local velocity=$(echo "$response" | jq '.learning_velocity')
    if [ "$velocity" != "null" ]; then
        if echo "$velocity" | jq -e '.concepts_per_week, .hours_per_week, .trend' >/dev/null 2>&1; then
            # Verify trend is valid
            local trend=$(echo "$velocity" | jq -r '.trend')
            if [[ "$trend" =~ ^(increasing|decreasing|stable)$ ]]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Milestone progress tracking
test_milestone_progress() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/progress")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check milestones
    local milestones=$(echo "$response" | jq '.milestones')
    if [ "$milestones" != "null" ]; then
        local milestone_count=$(echo "$milestones" | jq 'length')
        
        for i in $(seq 0 $((milestone_count - 1))); do
            local milestone=$(echo "$milestones" | jq ".[$i]")
            
            # Verify milestone fields
            if ! echo "$milestone" | jq -e '.name, .total_concepts, .completed, .progress_percentage' >/dev/null 2>&1; then
                return 1
            fi
            
            # Verify progress calculation
            local total=$(echo "$milestone" | jq -r '.total_concepts')
            local completed=$(echo "$milestone" | jq -r '.completed')
            local progress=$(echo "$milestone" | jq -r '.progress_percentage')
            
            if [ "$total" -gt 0 ]; then
                local calc_progress=$(echo "scale=1; $completed * 100 / $total" | bc)
                local diff=$(echo "scale=1; $progress - $calc_progress" | bc | tr -d -)
                
                if (( $(echo "$diff > 0.5" | bc -l) )); then
                    print_status "FAIL" "Milestone progress calculation mismatch"
                    return 1
                fi
            fi
        done
        
        return 0
    fi
    
    return 1
}

# Test: Empty progress history
test_empty_progress_history() {
    if ! authenticate; then
        return 1
    fi
    
    # Request history for future dates (should be empty)
    local start_date=$(date -u -d "tomorrow" +"%Y-%m-%d" 2>/dev/null || date -u -v+1d +"%Y-%m-%d")
    local end_date=$(date -u -d "7 days" +"%Y-%m-%d" 2>/dev/null || date -u -v+7d +"%Y-%m-%d")
    
    local response=$(make_request "GET" "/progress/history?start_date=${start_date}&end_date=${end_date}")
    local status=$?
    
    if [ $status -eq 200 ]; then
        local history_count=$(echo "$response" | jq '.history | length')
        if [ "$history_count" -eq 0 ]; then
            return 0
        fi
    fi
    
    return 1
}

# Run all tests
run_all_tests() {
    print_status "INFO" "Starting Student Progress Tracking API Tests"
    
    # Run each test
    if run_test "Get overall progress" test_get_overall_progress; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get progress with timeframe filter" test_get_progress_timeframe; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get progress for specific milestone" test_get_progress_milestone; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get user progress as instructor" test_get_user_progress_instructor; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get other user's progress unauthorized" test_get_user_progress_unauthorized; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get progress history" test_get_progress_history; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Progress history with different granularities" test_progress_history_granularity; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Verify progress calculations" test_progress_calculations; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Progress recommendations" test_progress_recommendations; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Learning velocity tracking" test_learning_velocity; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Milestone progress tracking" test_milestone_progress; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Empty progress history" test_empty_progress_history; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Generate report
    generate_report "Student Progress Tracking API" $PASSED $FAILED
    
    # Cleanup
    cleanup_test_data
}

# Main execution
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    run_all_tests
fi