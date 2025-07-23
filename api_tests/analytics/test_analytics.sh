#!/bin/bash

# Analytics & Reporting API Tests

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source common utilities
source "$SCRIPT_DIR/../utils/common.sh"

# Test counters
PASSED=0
FAILED=0

# Test: Get analytics dashboard
test_get_analytics_dashboard() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/dashboard")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "summary trends top_concepts struggling_areas learning_paths"; then
            # Verify summary structure
            local active_learners=$(echo "$response" | jq -r '.summary.active_learners')
            if [ "$active_learners" -ge 0 ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Dashboard with different timeframes
test_dashboard_timeframes() {
    if ! authenticate; then
        return 1
    fi
    
    local timeframes=("week" "month" "quarter" "year")
    
    for timeframe in "${timeframes[@]}"; do
        local response=$(make_request "GET" "/analytics/dashboard?timeframe=$timeframe")
        local status=$?
        
        if [ $status -ne 200 ]; then
            print_status "FAIL" "Failed to get dashboard for timeframe: $timeframe"
            return 1
        fi
        
        if ! validate_json "$response" "summary trends"; then
            return 1
        fi
    done
    
    return 0
}

# Test: Dashboard for specific user (instructor)
test_dashboard_specific_user() {
    # Authenticate as instructor
    if ! authenticate "$TEST_USER_INSTRUCTOR" "$TEST_PASS_INSTRUCTOR"; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/dashboard?user_id=${TEST_USER_ID}")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "summary"; then
            return 0
        fi
    fi
    
    return 1
}

# Test: Get detailed learner analytics
test_get_learner_analytics() {
    # Authenticate as instructor
    if ! authenticate "$TEST_USER_INSTRUCTOR" "$TEST_PASS_INSTRUCTOR"; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/learner/${TEST_USER_ID}")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "user_id learning_profile performance_metrics engagement_patterns milestone_progress recommendations"; then
            # Verify user ID matches
            local response_user_id=$(echo "$response" | jq -r '.user_id')
            if [ "$response_user_id" = "$TEST_USER_ID" ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Get own learner analytics
test_get_own_analytics() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/learner/${USER_ID}")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "user_id learning_profile performance_metrics"; then
            return 0
        fi
    fi
    
    return 1
}

# Test: Unauthorized learner analytics access
test_learner_analytics_unauthorized() {
    # Authenticate as student
    if ! authenticate; then
        return 1
    fi
    
    # Try to access another user's analytics
    local response=$(make_request "GET" "/analytics/learner/other_user_456")
    local status=$?
    
    if [ $status -eq 403 ]; then
        return 0
    fi
    
    return 1
}

# Test: Export analytics data
test_export_analytics() {
    # Authenticate as instructor
    if ! authenticate "$TEST_USER_INSTRUCTOR" "$TEST_PASS_INSTRUCTOR"; then
        return 1
    fi
    
    local export_data=$(cat <<EOF
{
    "report_type": "learner_progress",
    "format": "pdf",
    "filters": {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "user_ids": ["$TEST_USER_ID"],
        "milestones": ["API Development"]
    },
    "include_sections": ["summary", "detailed_progress", "recommendations"]
}
EOF
)
    
    local response=$(make_request "POST" "/analytics/export" "$export_data")
    local status=$?
    
    if [ $status -eq 200 ] || [ $status -eq 202 ]; then
        if validate_json "$response" "export_id status"; then
            # Store export ID for status check
            export TEST_EXPORT_ID=$(echo "$response" | jq -r '.export_id')
            return 0
        fi
    fi
    
    return 1
}

# Test: Export different formats
test_export_formats() {
    # Authenticate as instructor
    if ! authenticate "$TEST_USER_INSTRUCTOR" "$TEST_PASS_INSTRUCTOR"; then
        return 1
    fi
    
    local formats=("pdf" "csv" "xlsx")
    
    for format in "${formats[@]}"; do
        local export_data=$(cat <<EOF
{
    "report_type": "concept_analytics",
    "format": "$format",
    "filters": {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    },
    "include_sections": ["summary"]
}
EOF
)
        
        local response=$(make_request "POST" "/analytics/export" "$export_data")
        local status=$?
        
        if [ $status -ne 200 ] && [ $status -ne 202 ]; then
            print_status "FAIL" "Failed to export in format: $format"
            return 1
        fi
    done
    
    return 0
}

# Test: Check export status
test_export_status() {
    # Use export from previous test
    if [ -z "$TEST_EXPORT_ID" ]; then
        # Create an export first
        test_export_analytics
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    # Authenticate as instructor
    if ! authenticate "$TEST_USER_INSTRUCTOR" "$TEST_PASS_INSTRUCTOR"; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/export/${TEST_EXPORT_ID}/status")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "export_id status"; then
            local export_status=$(echo "$response" | jq -r '.status')
            if [[ "$export_status" =~ ^(processing|completed|failed)$ ]]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Dashboard trends analysis
test_dashboard_trends() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/dashboard?timeframe=month")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Verify trends structure
    local trends=$(echo "$response" | jq '.trends')
    if [ "$trends" != "null" ]; then
        # Check completion rate trend
        local completion_trend=$(echo "$trends" | jq '.completion_rate')
        if echo "$completion_trend" | jq -e '.current, .previous, .change_percentage' >/dev/null 2>&1; then
            # Verify change calculation
            local current=$(echo "$completion_trend" | jq -r '.current')
            local previous=$(echo "$completion_trend" | jq -r '.previous')
            local change=$(echo "$completion_trend" | jq -r '.change_percentage')
            
            if [ "$previous" != "0" ]; then
                local calc_change=$(echo "scale=1; ($current - $previous) * 100 / $previous" | bc)
                local diff=$(echo "scale=1; $change - $calc_change" | bc | tr -d -)
                
                if (( $(echo "$diff < 1" | bc -l) )); then
                    return 0
                fi
            else
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Top concepts analytics
test_top_concepts() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/dashboard")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check top concepts
    local top_concepts=$(echo "$response" | jq '.top_concepts')
    if [ "$top_concepts" != "null" ]; then
        local concept_count=$(echo "$top_concepts" | jq 'length')
        
        for i in $(seq 0 $((concept_count - 1))); do
            local concept=$(echo "$top_concepts" | jq ".[$i]")
            
            # Verify concept fields
            if ! echo "$concept" | jq -e '.concept_id, .title, .completions, .average_time, .average_score' >/dev/null 2>&1; then
                return 1
            fi
            
            # Verify completions and scores are reasonable
            local completions=$(echo "$concept" | jq -r '.completions')
            local avg_score=$(echo "$concept" | jq -r '.average_score')
            
            if [ "$completions" -lt 0 ] || (( $(echo "$avg_score < 0 || $avg_score > 1" | bc -l) )); then
                return 1
            fi
        done
        
        return 0
    fi
    
    return 1
}

# Test: Struggling areas identification
test_struggling_areas() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/dashboard")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check struggling areas
    local struggling=$(echo "$response" | jq '.struggling_areas')
    if [ "$struggling" != "null" ]; then
        local area_count=$(echo "$struggling" | jq 'length')
        
        if [ "$area_count" -gt 0 ]; then
            local first_area=$(echo "$struggling" | jq '.[0]')
            
            # Verify structure
            if echo "$first_area" | jq -e '.concept_id, .title, .failure_rate, .average_attempts, .common_issues' >/dev/null 2>&1; then
                # Verify failure rate is between 0 and 1
                local failure_rate=$(echo "$first_area" | jq -r '.failure_rate')
                if (( $(echo "$failure_rate >= 0 && $failure_rate <= 1" | bc -l) )); then
                    return 0
                fi
            fi
        else
            # No struggling areas is also valid
            return 0
        fi
    fi
    
    return 1
}

# Test: Learning profile analysis
test_learning_profile() {
    # Authenticate as instructor
    if ! authenticate "$TEST_USER_INSTRUCTOR" "$TEST_PASS_INSTRUCTOR"; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/learner/${TEST_USER_ID}")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check learning profile
    local profile=$(echo "$response" | jq '.learning_profile')
    if [ "$profile" != "null" ]; then
        if echo "$profile" | jq -e '.preferred_time, .average_session_length, .learning_style, .strength_areas, .improvement_areas' >/dev/null 2>&1; then
            # Verify learning style is valid
            local style=$(echo "$profile" | jq -r '.learning_style')
            if [[ "$style" =~ ^(visual|auditory|kinesthetic|reading)$ ]]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Engagement patterns
test_engagement_patterns() {
    # Authenticate as instructor
    if ! authenticate "$TEST_USER_INSTRUCTOR" "$TEST_PASS_INSTRUCTOR"; then
        return 1
    fi
    
    local response=$(make_request "GET" "/analytics/learner/${TEST_USER_ID}")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check engagement patterns
    local engagement=$(echo "$response" | jq '.engagement_patterns')
    if [ "$engagement" != "null" ]; then
        # Verify resource preferences add up to 1
        local prefs=$(echo "$engagement" | jq '.resource_preferences')
        if [ "$prefs" != "null" ]; then
            local doc=$(echo "$prefs" | jq -r '.documentation // 0')
            local video=$(echo "$prefs" | jq -r '.video // 0')
            local interactive=$(echo "$prefs" | jq -r '.interactive // 0')
            
            local total=$(echo "$doc + $video + $interactive" | bc)
            local diff=$(echo "scale=2; $total - 1" | bc | tr -d -)
            
            if (( $(echo "$diff < 0.01" | bc -l) )); then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Run all tests
run_all_tests() {
    print_status "INFO" "Starting Analytics & Reporting API Tests"
    
    # Run each test
    if run_test "Get analytics dashboard" test_get_analytics_dashboard; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Dashboard with different timeframes" test_dashboard_timeframes; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Dashboard for specific user" test_dashboard_specific_user; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get detailed learner analytics" test_get_learner_analytics; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get own learner analytics" test_get_own_analytics; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Unauthorized learner analytics access" test_learner_analytics_unauthorized; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Export analytics data" test_export_analytics; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Export different formats" test_export_formats; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Check export status" test_export_status; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Dashboard trends analysis" test_dashboard_trends; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Top concepts analytics" test_top_concepts; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Struggling areas identification" test_struggling_areas; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Learning profile analysis" test_learning_profile; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Engagement patterns" test_engagement_patterns; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Generate report
    generate_report "Analytics & Reporting API" $PASSED $FAILED
    
    # Cleanup
    cleanup_test_data
}

# Main execution
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    run_all_tests
fi