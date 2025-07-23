#!/bin/bash

# AI Chat Interface API Tests

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source common utilities
source "$SCRIPT_DIR/../utils/common.sh"

# Test counters
PASSED=0
FAILED=0

# Global chat variables
CHAT_ID=""

# Test: Start AI tutoring session
test_start_chat_session() {
    if ! authenticate; then
        return 1
    fi
    
    local chat_data=$(cat <<EOF
{
    "context": {
        "concept_id": $TEST_CONCEPT_ID,
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "mode": "tutoring"
    },
    "initial_message": "I'm having trouble understanding REST API versioning"
}
EOF
)
    
    local response=$(make_request "POST" "/chat/start" "$chat_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "chat_id status ai_model context_loaded initial_response"; then
            # Store chat ID for subsequent tests
            CHAT_ID=$(echo "$response" | jq -r '.chat_id')
            export CHAT_ID
            
            # Verify initial response structure
            local initial_response=$(echo "$response" | jq '.initial_response')
            if echo "$initial_response" | jq -e '.message' >/dev/null 2>&1; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Start chat with different modes
test_start_chat_modes() {
    if ! authenticate; then
        return 1
    fi
    
    local modes=("tutoring" "debugging" "explaining" "practice")
    
    for mode in "${modes[@]}"; do
        local chat_data=$(cat <<EOF
{
    "context": {
        "concept_id": $TEST_CONCEPT_ID,
        "mode": "$mode"
    },
    "initial_message": "Help me with this concept"
}
EOF
)
        
        local response=$(make_request "POST" "/chat/start" "$chat_data")
        local status=$?
        
        if [ $status -ne 200 ]; then
            print_status "FAIL" "Failed to start chat with mode: $mode"
            return 1
        fi
    done
    
    return 0
}

# Test: Send message in chat session
test_send_chat_message() {
    if ! authenticate; then
        return 1
    fi
    
    # Start a chat session first if needed
    if [ -z "$CHAT_ID" ]; then
        test_start_chat_session
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    local message_data=$(cat <<EOF
{
    "message": "Can you show me how to implement versioning in FastAPI?",
    "include_code_examples": true
}
EOF
)
    
    local response=$(make_request "POST" "/chat/${CHAT_ID}/message" "$message_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "message_id response tokens_used context_retention"; then
            # Verify response structure
            local ai_response=$(echo "$response" | jq '.response')
            if echo "$ai_response" | jq -e '.message' >/dev/null 2>&1; then
                # Check for code examples if requested
                local code_examples=$(echo "$ai_response" | jq '.code_examples')
                if [ "$code_examples" != "null" ]; then
                    return 0
                fi
            fi
        fi
    fi
    
    return 1
}

# Test: Send message without code examples
test_send_message_no_code() {
    if ! authenticate; then
        return 1
    fi
    
    if [ -z "$CHAT_ID" ]; then
        test_start_chat_session
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    local message_data=$(cat <<EOF
{
    "message": "What are the benefits of API versioning?",
    "include_code_examples": false
}
EOF
)
    
    local response=$(make_request "POST" "/chat/${CHAT_ID}/message" "$message_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "message_id response"; then
            return 0
        fi
    fi
    
    return 1
}

# Test: Get chat history
test_get_chat_history() {
    if ! authenticate; then
        return 1
    fi
    
    if [ -z "$CHAT_ID" ]; then
        test_start_chat_session
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    local response=$(make_request "GET" "/chat/${CHAT_ID}/history")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "chat_id started_at messages total_messages"; then
            # Verify messages array
            local message_count=$(echo "$response" | jq '.messages | length')
            if [ "$message_count" -gt 0 ]; then
                # Check message structure
                local first_msg=$(echo "$response" | jq '.messages[0]')
                if echo "$first_msg" | jq -e '.message_id, .role, .content, .timestamp' >/dev/null 2>&1; then
                    return 0
                fi
            fi
        fi
    fi
    
    return 1
}

# Test: Provide feedback on AI response
test_provide_feedback() {
    if ! authenticate; then
        return 1
    fi
    
    if [ -z "$CHAT_ID" ]; then
        test_start_chat_session
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    # Send a message first to get a message ID
    local message_data=$(cat <<EOF
{
    "message": "Explain REST principles",
    "include_code_examples": false
}
EOF
)
    
    local msg_response=$(make_request "POST" "/chat/${CHAT_ID}/message" "$message_data")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    local message_id=$(echo "$msg_response" | jq -r '.message_id')
    
    # Provide feedback
    local feedback_data=$(cat <<EOF
{
    "message_id": "$message_id",
    "rating": 5,
    "helpful": true,
    "feedback": "Clear explanation with great examples",
    "improvement_suggestions": "Could include more real-world scenarios"
}
EOF
)
    
    local response=$(make_request "POST" "/chat/${CHAT_ID}/feedback" "$feedback_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "feedback_recorded"; then
            return 0
        fi
    fi
    
    return 1
}

# Test: Invalid chat ID
test_invalid_chat_id() {
    if ! authenticate; then
        return 1
    fi
    
    local message_data=$(cat <<EOF
{
    "message": "Test message",
    "include_code_examples": false
}
EOF
)
    
    local response=$(make_request "POST" "/chat/invalid-chat-id-12345/message" "$message_data")
    local status=$?
    
    if [ $status -eq 404 ] || [ $status -eq 400 ]; then
        return 0
    fi
    
    return 1
}

# Test: Chat without authentication
test_chat_unauthorized() {
    local saved_token=$ACCESS_TOKEN
    ACCESS_TOKEN=""
    
    local chat_data=$(cat <<EOF
{
    "context": {
        "mode": "tutoring"
    },
    "initial_message": "Help me learn"
}
EOF
)
    
    local response=$(make_request "POST" "/chat/start" "$chat_data")
    local status=$?
    
    ACCESS_TOKEN=$saved_token
    
    if [ $status -eq 401 ]; then
        return 0
    fi
    
    return 1
}

# Test: Long conversation context
test_long_conversation() {
    if ! authenticate; then
        return 1
    fi
    
    # Start new chat
    local chat_data=$(cat <<EOF
{
    "context": {
        "mode": "tutoring"
    },
    "initial_message": "Let's have a detailed discussion about REST APIs"
}
EOF
)
    
    local start_response=$(make_request "POST" "/chat/start" "$chat_data")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    local test_chat_id=$(echo "$start_response" | jq -r '.chat_id')
    
    # Send multiple messages
    local messages=(
        "What are the main REST principles?"
        "How does statelessness work in REST?"
        "Can you explain HATEOAS?"
        "What about caching strategies?"
        "How do I handle authentication?"
    )
    
    local last_context_retention=1.0
    
    for msg in "${messages[@]}"; do
        local message_data=$(cat <<EOF
{
    "message": "$msg",
    "include_code_examples": false
}
EOF
)
        
        local response=$(make_request "POST" "/chat/${test_chat_id}/message" "$message_data")
        if [ $? -ne 200 ]; then
            return 1
        fi
        
        # Check context retention
        local context_retention=$(echo "$response" | jq -r '.context_retention')
        if (( $(echo "$context_retention < 0.5" | bc -l) )); then
            print_status "WARN" "Context retention dropping: $context_retention"
        fi
        
        last_context_retention=$context_retention
        
        # Small delay between messages
        sleep 0.5
    done
    
    # Verify context was maintained
    if (( $(echo "$last_context_retention > 0.7" | bc -l) )); then
        return 0
    fi
    
    return 1
}

# Test: Follow-up questions
test_follow_up_questions() {
    if ! authenticate; then
        return 1
    fi
    
    if [ -z "$CHAT_ID" ]; then
        test_start_chat_session
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    local message_data=$(cat <<EOF
{
    "message": "What is REST?",
    "include_code_examples": false
}
EOF
)
    
    local response=$(make_request "POST" "/chat/${CHAT_ID}/message" "$message_data")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    # Check for follow-up questions
    local follow_ups=$(echo "$response" | jq '.response.follow_up_questions')
    if [ "$follow_ups" != "null" ]; then
        local question_count=$(echo "$follow_ups" | jq 'length')
        if [ "$question_count" -gt 0 ]; then
            return 0
        fi
    fi
    
    return 1
}

# Test: Token usage tracking
test_token_usage() {
    if ! authenticate; then
        return 1
    fi
    
    if [ -z "$CHAT_ID" ]; then
        test_start_chat_session
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    # Send a message and check token usage
    local message_data=$(cat <<EOF
{
    "message": "Explain the concept of RESTful APIs in detail with examples",
    "include_code_examples": true
}
EOF
)
    
    local response=$(make_request "POST" "/chat/${CHAT_ID}/message" "$message_data")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    local tokens_used=$(echo "$response" | jq -r '.tokens_used')
    if [ "$tokens_used" -gt 0 ]; then
        print_status "INFO" "Tokens used: $tokens_used"
        return 0
    fi
    
    return 1
}

# Run all tests
run_all_tests() {
    print_status "INFO" "Starting AI Chat Interface API Tests"
    
    # Run each test
    if run_test "Start AI tutoring session" test_start_chat_session; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Start chat with different modes" test_start_chat_modes; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Send message in chat session" test_send_chat_message; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Send message without code examples" test_send_message_no_code; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get chat history" test_get_chat_history; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Provide feedback on AI response" test_provide_feedback; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Invalid chat ID" test_invalid_chat_id; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Chat without authentication" test_chat_unauthorized; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Long conversation context" test_long_conversation; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Follow-up questions" test_follow_up_questions; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Token usage tracking" test_token_usage; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Test rate limiting if enabled
    if [ "$RATE_LIMIT_TEST" = "true" ]; then
        if run_test "Chat API rate limiting" test_chat_rate_limit; then
            ((PASSED++))
        else
            ((FAILED++))
        fi
    fi
    
    # Generate report
    generate_report "AI Chat Interface API" $PASSED $FAILED
    
    # Cleanup
    cleanup_test_data
}

# Test: Chat API rate limiting
test_chat_rate_limit() {
    if ! authenticate; then
        return 1
    fi
    
    # Start a chat session
    local chat_data=$(cat <<EOF
{
    "context": {
        "mode": "tutoring"
    },
    "initial_message": "Test rate limiting"
}
EOF
)
    
    local start_response=$(make_request "POST" "/chat/start" "$chat_data")
    if [ $? -ne 200 ]; then
        return 1
    fi
    
    local test_chat_id=$(echo "$start_response" | jq -r '.chat_id')
    
    # Send messages rapidly
    local blocked_count=0
    local limit=20  # Chat API has lower rate limit
    
    for i in $(seq 1 $limit); do
        local message_data=$(cat <<EOF
{
    "message": "Test message $i",
    "include_code_examples": false
}
EOF
)
        
        local response=$(make_request "POST" "/chat/${test_chat_id}/message" "$message_data" 2>&1)
        local status=$?
        
        if [ $status -eq 429 ]; then
            ((blocked_count++))
        fi
        
        # Very small delay
        sleep 0.05
    done
    
    if [ $blocked_count -gt 0 ]; then
        print_status "INFO" "Rate limit triggered: $blocked_count requests blocked"
        return 0
    fi
    
    return 1
}

# Main execution
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    run_all_tests
fi