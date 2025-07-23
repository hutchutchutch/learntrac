# LearnTrac API Test Suite

Comprehensive bash-based test suite for the LearnTrac API endpoints.

## Overview

This test suite provides automated testing for all LearnTrac API endpoints including:

- Authentication & Authorization
- Learning Concepts Management
- Student Progress Tracking
- AI Chat Interface
- Analytics & Reporting
- Knowledge Graph
- Exercises & Practice
- Adaptive Learning
- WebSocket/Voice Interactions

## Prerequisites

Required tools:
- `bash` (4.0+)
- `curl`
- `jq` (for JSON parsing)
- `bc` (for calculations)
- `websocat` (for WebSocket tests, optional)

## Quick Start

1. Make scripts executable:
```bash
chmod +x run_all_tests.sh
chmod +x */test_*.sh
```

2. Configure API endpoint (optional):
```bash
export API_BASE_URL="http://localhost:8001"
```

3. Run all tests:
```bash
./run_all_tests.sh
```

## Configuration

Edit `config.sh` to customize:

```bash
# API Configuration
export API_BASE_URL="http://localhost:8001"
export API_VERSION="v1"

# Test Credentials
export TEST_USER_STUDENT="student1"
export TEST_PASS_STUDENT="password123"
export TEST_USER_INSTRUCTOR="instructor1"
export TEST_PASS_INSTRUCTOR="password456"

# Test Options
export VERBOSE="false"
export SAVE_RESPONSES="true"
export OUTPUT_DIR="./test_results"
```

## Running Tests

### Run All Tests
```bash
./run_all_tests.sh
```

### Run Specific Test Suite
```bash
./run_all_tests.sh --suite auth
./run_all_tests.sh --suite concepts
./run_all_tests.sh --suite progress
```

### Run with Options
```bash
# Verbose output
./run_all_tests.sh --verbose

# Different environment
./run_all_tests.sh --env staging --url https://staging-api.learntrac.com

# Enable performance tests
./run_all_tests.sh --perf

# Enable rate limiting tests
./run_all_tests.sh --rate-limit
```

### Run Individual Test Files
```bash
# Run authentication tests only
./auth/test_auth.sh

# Run concept tests only
./concepts/test_concepts.sh
```

## Test Structure

```
api_tests/
├── config.sh              # Configuration file
├── run_all_tests.sh       # Master test runner
├── utils/
│   └── common.sh         # Common utilities and functions
├── auth/
│   └── test_auth.sh      # Authentication tests
├── concepts/
│   └── test_concepts.sh  # Learning concepts tests
├── progress/
│   └── test_progress.sh  # Progress tracking tests
├── chat/
│   └── test_chat.sh      # AI chat tests
├── analytics/
│   └── test_analytics.sh # Analytics tests
└── test_results/         # Test output directory
```

## Test Categories

### Authentication Tests (`auth/test_auth.sh`)
- Login with valid/invalid credentials
- Token refresh
- User profile retrieval
- Logout functionality
- Role-based access
- Concurrent login handling
- Rate limiting (optional)

### Learning Concepts Tests (`concepts/test_concepts.sh`)
- List concepts with filters
- Get specific concept details
- Start learning sessions
- Complete/abandon concepts
- Handle prerequisites
- Pagination testing
- Search functionality

### Progress Tracking Tests (`progress/test_progress.sh`)
- Overall progress retrieval
- Timeframe filtering
- Milestone tracking
- Progress history
- Learning velocity
- Recommendations
- Instructor vs student access

### AI Chat Tests (`chat/test_chat.sh`)
- Start chat sessions
- Send messages
- Handle code examples
- Chat history
- Feedback submission
- Context retention
- Token usage tracking

### Analytics Tests (`analytics/test_analytics.sh`)
- Dashboard data
- Learner analytics
- Export functionality
- Trend analysis
- Top concepts
- Struggling areas
- Engagement patterns

## Output and Reports

Test results are saved to `test_results/` directory:

- Individual test logs: `{suite_name}_output.log`
- Summary report: `test_report_YYYYMMDD_HHMMSS.txt`
- API responses: Timestamped JSON files (if enabled)

### Sample Report
```
========================================
LearnTrac API Test Report
========================================
Date: 2024-01-20 10:30:00
Environment: development
API Base URL: http://localhost:8001

Overall Results:
Total Passed: 87
Total Failed: 3
Success Rate: 96.67%

Test Suite Results:
----------------------------------------
Suite Name                         Passed     Failed
----------------------------------------
Authentication                         10          0
Learning_Concepts                      12          0
Progress_Tracking                      12          0
AI_Chat                               11          0
Analytics                             14          0
----------------------------------------
```

## Environment Variables

Key environment variables:

- `API_BASE_URL`: Base URL for API (default: http://localhost:8001)
- `TEST_MODE`: Test environment (development/staging/production)
- `VERBOSE`: Enable verbose output (true/false)
- `DEBUG`: Enable curl debug output (true/false)
- `RATE_LIMIT_TEST`: Enable rate limiting tests (true/false)
- `PERF_TEST`: Enable performance tests (true/false)

## Troubleshooting

### Common Issues

1. **Authentication failures**
   - Verify credentials in config.sh
   - Check API is running
   - Ensure database has test users

2. **Connection refused**
   - Check API_BASE_URL is correct
   - Verify API service is running
   - Check firewall/network settings

3. **JSON parsing errors**
   - Ensure `jq` is installed
   - Check API response format
   - Enable verbose mode for debugging

### Debug Mode

Enable debug output:
```bash
export DEBUG=true
export VERBOSE=true
./run_all_tests.sh
```

## Adding New Tests

1. Create test file in appropriate directory
2. Source common utilities:
   ```bash
   source "$SCRIPT_DIR/../utils/common.sh"
   ```

3. Implement test functions:
   ```bash
   test_my_feature() {
       if ! authenticate; then
           return 1
       fi
       
       local response=$(make_request "GET" "/my-endpoint")
       local status=$?
       
       if [ $status -eq 200 ]; then
           if validate_json "$response" "expected_field"; then
               return 0
           fi
       fi
       
       return 1
   }
   ```

4. Add to test runner in main function

## CI/CD Integration

### GitHub Actions Example
```yaml
name: API Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq bc curl
      
      - name: Run API tests
        env:
          API_BASE_URL: ${{ secrets.API_URL }}
          TEST_USER_STUDENT: ${{ secrets.TEST_USER }}
          TEST_PASS_STUDENT: ${{ secrets.TEST_PASS }}
        run: |
          cd api_tests
          chmod +x run_all_tests.sh
          ./run_all_tests.sh
```

### Jenkins Pipeline Example
```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            steps {
                sh '''
                    cd api_tests
                    chmod +x run_all_tests.sh
                    ./run_all_tests.sh --env ${ENV}
                '''
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'api_tests/test_results/**/*'
            publishHTML target: [
                reportDir: 'api_tests/test_results',
                reportFiles: 'test_report_*.txt',
                reportName: 'API Test Report'
            ]
        }
    }
}
```

## License

Copyright (c) 2024 LearnTrac Project