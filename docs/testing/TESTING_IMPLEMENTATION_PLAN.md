# LearnTrac Testing Implementation Plan

## Executive Summary

This document outlines the comprehensive testing strategy for the LearnTrac project based on the current task list and system architecture. The plan prioritizes critical user paths and aligns with the development roadmap in `.taskmaster/tasks/tasks.json`.

## Testing Philosophy

- **Shift-left approach**: Every PR must include appropriate tests
- **Test pyramid**: Many unit tests → fewer integration tests → minimal E2E tests
- **Stop-the-line policy**: Failed tests block merges to main branch
- **Test-driven development**: Write tests alongside or before implementation

## Component Testing Requirements

### 1. FastAPI Learning Service (`/learntrac-api`) - High Priority

**Related Tasks**: 4, 5, 7, 8, 9, 11

#### Unit Tests Required:
```python
# Core modules to test
- src/config.py - Configuration loading and validation
- src/auth.py - JWT token validation logic
- src/routers/*.py - Request/response validation
- Core service classes:
  - Neo4jAuraClient (Task 5)
  - ElastiCacheClient (Task 7)
  - LLMService (Task 8)
  - TicketCreationService (Task 9)
  - AnswerEvaluationService (Task 11)
```

#### Integration Tests Required:
- Learning path generation workflow (Task 4)
- Neo4j vector search with real data (Task 5)
- Redis caching behavior (Task 7)
- Ticket creation with prerequisites (Task 9)
- Answer evaluation flow (Task 11)

### 2. Trac Plugins - High Priority

**Related Tasks**: 3, 6, 10, 12, 15

#### Unit Tests Required:
```python
# Plugin components
- CognitoAuthenticator (Task 3)
  - JWT validation
  - Session management
  - Permission mapping
- LearningPathMacro (Task 6)
  - Form rendering
  - Authentication checks
- LearningTicketDisplay (Task 10)
  - Custom field retrieval
  - Answer submission handling
- KnowledgeGraphGenerator (Task 12)
  - DOT file generation
  - Cache key management
```

### 3. Infrastructure Tests - Medium Priority

**Related Tasks**: 1, 13, 14

#### Terraform Tests:
- Cognito User Pool configuration
- API Gateway routes and authorizers
- Lambda function deployment
- RDS and ElastiCache setup
- Security group rules

#### Docker Tests:
- Container build validation
- Health check endpoints
- Environment variable handling
- Inter-container networking

## Testing Frameworks and Tools

### Python Testing Stack
```yaml
Core:
  - pytest: Primary test framework
  - pytest-asyncio: Async test support
  - pytest-cov: Coverage reporting (target: ≥90%)

Mocking:
  - pytest-mock: General mocking
  - moto: AWS service mocking
  - responses: HTTP request mocking

Integration:
  - testcontainers: Disposable service containers
  - httpx: Async HTTP client testing
  - FastAPI TestClient: API endpoint testing

Quality:
  - hypothesis: Property-based testing
  - schemathesis: API contract testing
  - mypy: Static type checking
```

### Infrastructure Testing
```yaml
Terraform:
  - Terratest: Infrastructure validation
  - tflint: Terraform linting
  - terraform validate: Configuration validation

Containers:
  - Trivy: Security scanning
  - Hadolint: Dockerfile linting
  - docker-compose: Integration testing
```

### JavaScript/Frontend Testing
```yaml
Unit:
  - Jest: JavaScript unit tests
  - jsdom: DOM manipulation testing

E2E:
  - Cypress: Browser automation
  - Playwright: Cross-browser testing
```

## Implementation Priority

### Phase 1: Critical Path (Weeks 1-2)
1. **FastAPI Core Tests**
   ```bash
   # Set up pytest infrastructure
   learntrac-api/
   ├── tests/
   │   ├── __init__.py
   │   ├── conftest.py  # Shared fixtures
   │   ├── unit/
   │   │   ├── test_auth.py
   │   │   ├── test_config.py
   │   │   └── test_models.py
   │   └── integration/
   │       ├── test_learning_path.py
   │       └── test_ticket_creation.py
   ```

2. **Trac Authentication Tests**
   ```bash
   plugins/cognitoauth/tests/
   ├── test_jwt_validation.py
   ├── test_session_management.py
   └── test_permission_mapping.py
   ```

### Phase 2: Core Workflows (Weeks 3-4)
1. **Integration Test Suite**
   - Learning path generation E2E
   - Neo4j vector search accuracy
   - Redis caching behavior
   - Answer evaluation workflow

2. **Docker Compose Tests**
   ```yaml
   # docker-compose.test.yml
   services:
     test-runner:
       build: ./tests
       depends_on:
         - trac
         - learntrac-api
         - postgres
         - redis
         - neo4j
   ```

### Phase 3: Infrastructure & UI (Weeks 5-6)
1. **Terraform Tests**
   ```go
   // learntrac-infrastructure/tests/
   ├── cognito_test.go
   ├── api_gateway_test.go
   └── networking_test.go
   ```

2. **Frontend Tests**
   ```javascript
   // plugins/learningpathmacro/tests/
   ├── unit/
   │   └── learningpath.test.js
   └── e2e/
       └── macro-workflow.cy.js
   ```

## CI/CD Pipeline Configuration

### GitHub Actions Workflow
```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Python Linting
        run: |
          black --check .
          flake8 .
          mypy .

  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Unit Tests
        run: |
          pytest -m unit --cov=src --cov-report=xml
      - name: Upload Coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
      redis:
        image: redis:7
      neo4j:
        image: neo4j:5
    steps:
      - name: Run Integration Tests
        run: |
          pytest -m integration

  docker-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Build and Test Containers
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## Test Data Management

### Fixtures and Factories
```python
# tests/conftest.py
@pytest.fixture
def cognito_user():
    """Mock Cognito user with valid JWT"""
    return {
        "sub": "test-user-123",
        "email": "test@example.com",
        "cognito:groups": ["learners"]
    }

@pytest.fixture
def learning_path_request():
    """Sample learning path generation request"""
    return {
        "query": "Introduction to machine learning",
        "user_id": "test-user-123",
        "difficulty": "beginner"
    }
```

### Test Database Seeds
```sql
-- tests/seeds/learning_schema.sql
INSERT INTO learning.paths (id, user_id, query, created_at)
VALUES 
  ('550e8400-e29b-41d4-a716-446655440000', 'test-user-123', 'ML basics', NOW()),
  ('550e8400-e29b-41d4-a716-446655440001', 'test-user-456', 'Python intro', NOW());
```

## Performance Testing

### API Load Testing
```javascript
// k6/learning-path-load-test.js
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
};

export default function() {
  let response = http.post('https://api.learntrac.com/v1/learning-paths/generate', {
    query: 'test query',
    user_id: 'test-user'
  });
  
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
}
```

## Security Testing

### SAST/DAST Implementation
```yaml
security-scan:
  runs-on: ubuntu-latest
  steps:
    - name: Run Trivy Container Scan
      run: |
        trivy image learntrac-api:latest
        trivy image trac:latest
    
    - name: OWASP ZAP API Scan
      uses: zaproxy/action-api-scan@v0.4.0
      with:
        target: 'https://api.learntrac.com/openapi.json'
```

## Test Metrics and Reporting

### Coverage Requirements
- Core business logic: ≥90%
- API endpoints: ≥85%
- Infrastructure code: ≥70%
- UI components: ≥60%

### Quality Gates
```yaml
quality-gates:
  - coverage: 85%
  - passing-tests: 100%
  - security-vulnerabilities: 0 critical
  - performance-regression: <10%
```

## Migration from Existing Tests

### Current Test Migration Plan
1. **Preserve existing bash tests** as smoke tests
2. **Port to pytest** where appropriate:
   ```python
   # From: api_tests/auth/test_auth.sh
   # To: tests/integration/test_auth_flow.py
   
   def test_cognito_login_flow(api_client):
       response = api_client.post("/auth/login", json={
           "username": "test@example.com",
           "password": "TestPassword123!"
       })
       assert response.status_code == 200
       assert "access_token" in response.json()
   ```

3. **Enhance with property testing**:
   ```python
   @given(
       query=st.text(min_size=5, max_size=100),
       difficulty=st.sampled_from(["beginner", "intermediate", "advanced"])
   )
   def test_learning_path_generation_properties(query, difficulty):
       # Test invariants hold for all valid inputs
   ```

## Timeline and Milestones

### Week 1-2: Foundation
- [ ] Set up pytest infrastructure
- [ ] Create core unit tests
- [ ] Establish CI pipeline

### Week 3-4: Integration
- [ ] Implement testcontainers setup
- [ ] Create integration test suite
- [ ] Add performance benchmarks

### Week 5-6: Coverage
- [ ] Achieve 85% code coverage
- [ ] Complete security scanning
- [ ] Document test patterns

### Week 7-8: Optimization
- [ ] Optimize test execution time
- [ ] Implement parallel testing
- [ ] Create test dashboard

## Success Criteria

1. **All critical user paths have automated tests**
2. **CI pipeline runs in <10 minutes**
3. **Zero critical security vulnerabilities**
4. **Test documentation is comprehensive**
5. **Team follows TDD practices**

## Next Steps

1. **Review and approve this plan** with the team
2. **Set up pytest infrastructure** in learntrac-api
3. **Create first unit tests** for auth module
4. **Configure GitHub Actions** for CI
5. **Schedule testing workshops** for team training

---

*This plan is a living document and should be updated as the project evolves and new testing requirements emerge.*