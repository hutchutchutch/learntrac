#!/bin/bash

# Learning Concepts API Tests

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source common utilities
source "$SCRIPT_DIR/../utils/common.sh"

# Test counters
PASSED=0
FAILED=0

# Test: List all concepts
test_list_concepts() {
    # Ensure authenticated
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/concepts")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "concepts total limit offset"; then
            # Verify concepts array exists
            local concepts_count=$(echo "$response" | jq '.concepts | length')
            if [ "$concepts_count" -ge 0 ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: List concepts with filters
test_list_concepts_filtered() {
    if ! authenticate; then
        return 1
    fi
    
    # Test different filter combinations
    local filters=(
        "?status=learning"
        "?type=task"
        "?difficulty=3"
        "?component=backend"
        "?limit=10&offset=0"
        "?status=learning&type=task&limit=5"
    )
    
    for filter in "${filters[@]}"; do
        local response=$(make_request "GET" "/concepts${filter}")
        local status=$?
        
        if [ $status -ne 200 ]; then
            print_status "FAIL" "Filter failed: $filter"
            return 1
        fi
        
        if ! validate_json "$response" "concepts total"; then
            return 1
        fi
    done
    
    return 0
}

# Test: Get specific concept
test_get_concept() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/concepts/${TEST_CONCEPT_ID}")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "id title description type status difficulty mastery_threshold"; then
            # Verify concept ID matches
            local concept_id=$(echo "$response" | jq -r '.id')
            if [ "$concept_id" = "$TEST_CONCEPT_ID" ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Get non-existent concept
test_get_concept_not_found() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/concepts/999999")
    local status=$?
    
    if [ $status -eq 404 ]; then
        return 0
    fi
    
    return 1
}

# Test: Start learning a concept
test_start_concept() {
    if ! authenticate; then
        return 1
    fi
    
    local start_data=$(cat <<EOF
{
    "learning_mode": "guided",
    "time_commitment": 120,
    "preferred_resources": ["documentation", "video"]
}
EOF
)
    
    local response=$(make_request "POST" "/concepts/${TEST_CONCEPT_ID}/start" "$start_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "session_id concept_id status started_at learning_path"; then
            # Store session ID for later tests
            export TEST_SESSION_ID=$(echo "$response" | jq -r '.session_id')
            return 0
        fi
    fi
    
    return 1
}

# Test: Start already started concept
test_start_concept_conflict() {
    if ! authenticate; then
        return 1
    fi
    
    local start_data=$(cat <<EOF
{
    "learning_mode": "guided",
    "time_commitment": 120,
    "preferred_resources": ["documentation"]
}
EOF
)
    
    # First start
    make_request "POST" "/concepts/${TEST_CONCEPT_ID}/start" "$start_data" >/dev/null 2>&1
    
    # Try to start again
    local response=$(make_request "POST" "/concepts/${TEST_CONCEPT_ID}/start" "$start_data")
    local status=$?
    
    if [ $status -eq 409 ]; then
        return 0
    fi
    
    return 1
}

# Test: Complete a concept
test_complete_concept() {
    if ! authenticate; then
        return 1
    fi
    
    # Start a concept first if no session exists
    if [ -z "$TEST_SESSION_ID" ]; then
        local start_data=$(cat <<EOF
{
    "learning_mode": "self-paced",
    "time_commitment": 60,
    "preferred_resources": ["documentation"]
}
EOF
)
        local start_response=$(make_request "POST" "/concepts/${TEST_CONCEPT_ID}/start" "$start_data")
        if [ $? -eq 200 ]; then
            TEST_SESSION_ID=$(echo "$start_response" | jq -r '.session_id')
        else
            return 1
        fi
    fi
    
    local complete_data=$(cat <<EOF
{
    "session_id": "$TEST_SESSION_ID",
    "completion_type": "mastered",
    "time_spent": 7200,
    "exercises_completed": ["ex1", "ex2"],
    "quiz_score": 0.85,
    "feedback": "Great tutorial, very clear explanations"
}
EOF
)
    
    local response=$(make_request "POST" "/concepts/${TEST_CONCEPT_ID}/complete" "$complete_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "concept_id status mastery_score completion_date"; then
            return 0
        fi
    fi
    
    return 1
}

# Test: Complete with invalid session
test_complete_invalid_session() {
    if ! authenticate; then
        return 1
    fi
    
    local complete_data=$(cat <<EOF
{
    "session_id": "invalid-session-id-12345",
    "completion_type": "completed",
    "time_spent": 3600,
    "exercises_completed": [],
    "quiz_score": 0.75
}
EOF
)
    
    local response=$(make_request "POST" "/concepts/${TEST_CONCEPT_ID}/complete" "$complete_data")
    local status=$?
    
    if [ $status -eq 400 ] || [ $status -eq 404 ]; then
        return 0
    fi
    
    return 1
}

# Test: Pagination
test_concepts_pagination() {
    if ! authenticate; then
        return 1
    fi
    
    # Get first page
    local page1=$(make_request "GET" "/concepts?limit=5&offset=0")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Get second page
    local page2=$(make_request "GET" "/concepts?limit=5&offset=5")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Verify different concepts
    local page1_ids=$(echo "$page1" | jq -r '.concepts[].id' | sort)
    local page2_ids=$(echo "$page2" | jq -r '.concepts[].id' | sort)
    
    if [ "$page1_ids" != "$page2_ids" ]; then
        return 0
    fi
    
    return 1
}

# Test: Search concepts by keyword
test_search_concepts() {
    if ! authenticate; then
        return 1
    fi
    
    # Search for API-related concepts
    local response=$(make_request "GET" "/concepts?search=API")
    local status=$?
    
    if [ $status -eq 200 ]; then
        local concepts=$(echo "$response" | jq -r '.concepts')
        if [ "$concepts" != "null" ] && [ "$concepts" != "[]" ]; then
            return 0
        fi
    fi
    
    return 1
}

# Test: Get prerequisite concepts
test_prerequisite_concepts() {
    if ! authenticate; then
        return 1
    fi
    
    local response=$(make_request "GET" "/concepts/${TEST_CONCEPT_ID}")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check if prerequisites exist and are properly formatted
    local prerequisites=$(echo "$response" | jq '.prerequisites')
    if [ "$prerequisites" != "null" ]; then
        # Verify each prerequisite has required fields
        local valid=true
        local prereq_count=$(echo "$prerequisites" | jq 'length')
        
        for i in $(seq 0 $((prereq_count - 1))); do
            local prereq=$(echo "$prerequisites" | jq ".[$i]")
            if ! echo "$prereq" | jq -e '.id' >/dev/null 2>&1; then
                valid=false
                break
            fi
        done
        
        if [ "$valid" = true ]; then
            return 0
        fi
    else
        # No prerequisites is also valid
        return 0
    fi
    
    return 1
}

# Test: Access concept without authentication
test_concept_unauthorized() {
    # Clear token
    local saved_token=$ACCESS_TOKEN
    ACCESS_TOKEN=""
    
    local response=$(make_request "GET" "/concepts/${TEST_CONCEPT_ID}")
    local status=$?
    
    # Restore token
    ACCESS_TOKEN=$saved_token
    
    if [ $status -eq 401 ]; then
        return 0
    fi
    
    return 1
}

# Run all tests
run_all_tests() {
    print_status "INFO" "Starting Learning Concepts API Tests"
    
    # Run each test
    if run_test "List all concepts" test_list_concepts; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "List concepts with filters" test_list_concepts_filtered; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get specific concept" test_get_concept; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get non-existent concept" test_get_concept_not_found; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Start learning a concept" test_start_concept; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Start already started concept" test_start_concept_conflict; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Complete a concept" test_complete_concept; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Complete with invalid session" test_complete_invalid_session; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Concepts pagination" test_concepts_pagination; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Search concepts" test_search_concepts; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get prerequisite concepts" test_prerequisite_concepts; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Access concept without auth" test_concept_unauthorized; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Generate report
    generate_report "Learning Concepts API" $PASSED $FAILED
    
    # Cleanup
    cleanup_test_data
}

# Main execution
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    run_all_tests
fi