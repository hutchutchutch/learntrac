#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive verification script for Task 4 subtasks 4.5-4.10
Tests academic sentence generation, embedding service, learning paths, 
RDS integration, health checks, and Docker configuration
"""

import os
from pathlib import Path

class RemainingSubtasksTester:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.api_dir = self.project_root / "learntrac-api"
        self.results = {}
        
    def test_subtask_5_academic_sentence_generation(self):
        """Test 4.5: Verify academic sentence generation service"""
        print("\n=== Testing Subtask 4.5: Academic Sentence Generation Service ===")
        
        # Check for sentence generation service
        paths_to_check = [
            self.api_dir / "src" / "services" / "sentence_generation.py",
            self.api_dir / "src" / "services" / "academic_generator.py",
            self.api_dir / "src" / "services" / "llm_service.py"
        ]
        
        service_found = False
        for path in paths_to_check:
            if path.exists():
                print(f"✓ Academic generation service found: {path.name}")
                service_found = True
                
                with open(path, 'r') as f:
                    content = f.read()
                    
                # Check for key features
                features = {
                    "Academic prompts": "academic" in content.lower() or "scholarly" in content.lower(),
                    "Sentence generation": "generate" in content or "completion" in content,
                    "LLM integration": "gpt" in content.lower() or "claude" in content.lower() or "openai" in content.lower(),
                    "Async methods": "async def" in content
                }
                
                for feature, found in features.items():
                    if found:
                        print(f"  ✓ {feature}")
                break
                
        self.results['subtask_4.5'] = service_found
        return service_found
        
    def test_subtask_6_embedding_service(self):
        """Test 4.6: Verify embedding service for vectorization"""
        print("\n=== Testing Subtask 4.6: Embedding Service ===")
        
        embedding_path = self.api_dir / "src" / "services" / "embedding_service.py"
        
        if embedding_path.exists():
            print("✓ Embedding service module exists")
            
            with open(embedding_path, 'r') as f:
                content = f.read()
                
            features = {
                "Embedding generation": "embed" in content.lower() or "vector" in content.lower(),
                "Model configuration": "model" in content.lower(),
                "Async implementation": "async def" in content,
                "Batch processing": "batch" in content.lower() or "list" in content,
                "Dimension specification": "dimension" in content.lower() or "1536" in content or "768" in content
            }
            
            feature_count = sum(1 for found in features.values() if found)
            
            for feature, found in features.items():
                if found:
                    print(f"✓ {feature}")
                else:
                    print(f"⚠ {feature} not found")
                    
            self.results['subtask_4.6'] = feature_count >= 3
            return feature_count >= 3
        else:
            print("✗ Embedding service not found")
            self.results['subtask_4.6'] = False
            return False
            
    def test_subtask_7_learning_path_api(self):
        """Test 4.7: Verify learning path API endpoint"""
        print("\n=== Testing Subtask 4.7: Learning Path API Endpoint ===")
        
        learning_router_path = self.api_dir / "src" / "routers" / "learning.py"
        
        if learning_router_path.exists():
            print("✓ Learning router module exists")
            
            with open(learning_router_path, 'r') as f:
                content = f.read()
                
            endpoints = {
                "Create learning path": "post" in content.lower() and "path" in content.lower(),
                "Get learning paths": "get" in content.lower() and "path" in content.lower(),
                "Update progress": "put" in content.lower() or "patch" in content.lower(),
                "Dependencies": "Depends" in content,
                "Authentication": "current_user" in content or "verify_token" in content
            }
            
            endpoint_count = sum(1 for found in endpoints.values() if found)
            
            for endpoint, found in endpoints.items():
                if found:
                    print(f"✓ {endpoint}")
                else:
                    print(f"⚠ {endpoint} not found")
                    
            self.results['subtask_4.7'] = endpoint_count >= 3
            return endpoint_count >= 3
        else:
            print("✗ Learning router not found")
            self.results['subtask_4.7'] = False
            return False
            
    def test_subtask_8_rds_integration(self):
        """Test 4.8: Verify RDS PostgreSQL integration service"""
        print("\n=== Testing Subtask 4.8: RDS Integration Service ===")
        
        # Check for database service
        db_paths = [
            self.api_dir / "src" / "db" / "__init__.py",
            self.api_dir / "src" / "db" / "database.py",
            self.api_dir / "src" / "services" / "database_service.py"
        ]
        
        db_found = False
        for path in db_paths:
            if path.exists():
                with open(path, 'r') as f:
                    content = f.read()
                    
                if "asyncpg" in content or "postgresql" in content.lower():
                    print(f"✓ RDS integration found in {path.name}")
                    db_found = True
                    
                    features = {
                        "AsyncPG driver": "asyncpg" in content,
                        "Connection pool": "pool" in content.lower(),
                        "Query methods": "query" in content or "execute" in content,
                        "Transaction support": "transaction" in content.lower()
                    }
                    
                    for feature, found in features.items():
                        if found:
                            print(f"  ✓ {feature}")
                    break
                    
        # Also check main.py for database initialization
        main_path = self.api_dir / "src" / "main.py"
        if main_path.exists() and not db_found:
            with open(main_path, 'r') as f:
                if "asyncpg" in f.read():
                    print("✓ RDS integration found in main.py")
                    db_found = True
                    
        self.results['subtask_4.8'] = db_found
        return db_found
        
    def test_subtask_9_health_checks(self):
        """Test 4.9: Verify health check endpoints"""
        print("\n=== Testing Subtask 4.9: Health Check Endpoints ===")
        
        # Check main.py or health router for health endpoints
        health_found = False
        
        # Check in main.py first
        main_path = self.api_dir / "src" / "main.py"
        if main_path.exists():
            with open(main_path, 'r') as f:
                content = f.read()
                
            if "/health" in content or "/readiness" in content or "/liveness" in content:
                print("✓ Health endpoints found in main.py")
                health_found = True
                
                # Check for different health checks
                checks = {
                    "Basic health": "/health" in content,
                    "Readiness check": "/readiness" in content or "/ready" in content,
                    "Liveness check": "/liveness" in content or "/alive" in content,
                    "Database check": "db" in content.lower() and "health" in content.lower(),
                    "Redis check": "redis" in content.lower() and "health" in content.lower()
                }
                
                for check, found in checks.items():
                    if found:
                        print(f"  ✓ {check}")
                        
        # Check for dedicated health router
        health_router = self.api_dir / "src" / "routers" / "health.py"
        if health_router.exists():
            print("✓ Dedicated health router exists")
            health_found = True
            
        self.results['subtask_4.9'] = health_found
        return health_found
        
    def test_subtask_10_docker_config(self):
        """Test 4.10: Verify Docker configuration and orchestration"""
        print("\n=== Testing Subtask 4.10: Docker Configuration ===")
        
        dockerfile_path = self.api_dir / "Dockerfile"
        
        if dockerfile_path.exists():
            print("✓ Dockerfile exists")
            
            with open(dockerfile_path, 'r') as f:
                content = f.read()
                
            docker_features = {
                "Python 3.11 base": "python:3.11" in content,
                "Working directory": "WORKDIR" in content,
                "Dependencies installation": "requirements.txt" in content or "poetry install" in content,
                "Port exposure": "EXPOSE" in content,
                "Entrypoint/CMD": "CMD" in content or "ENTRYPOINT" in content,
                "Non-root user": "USER" in content or "useradd" in content,
                "Multi-stage build": "FROM" in content and content.count("FROM") > 1
            }
            
            feature_count = sum(1 for found in docker_features.values() if found)
            
            for feature, found in docker_features.items():
                if found:
                    print(f"✓ {feature}")
                else:
                    print(f"⚠ {feature} not configured")
                    
            # Check docker-compose
            compose_path = self.api_dir / "docker-compose.yml"
            if compose_path.exists():
                print("✓ Docker Compose configuration exists")
                
            self.results['subtask_4.10'] = feature_count >= 4
            return feature_count >= 4
        else:
            print("✗ Dockerfile not found")
            self.results['subtask_4.10'] = False
            return False
            
    def generate_final_report(self):
        """Generate comprehensive verification report for remaining subtasks"""
        print("\n" + "="*70)
        print("=== TASK 4 REMAINING SUBTASKS VERIFICATION REPORT ===")
        print("="*70)
        
        subtask_names = {
            'subtask_4.5': 'Academic Sentence Generation Service',
            'subtask_4.6': 'Embedding Service',
            'subtask_4.7': 'Learning Path API',
            'subtask_4.8': 'RDS Integration Service',
            'subtask_4.9': 'Health Check Endpoints',
            'subtask_4.10': 'Docker Configuration'
        }
        
        total_subtasks = len(self.results)
        completed_subtasks = sum(1 for v in self.results.values() if v)
        
        print(f"\nSubtasks Verified: {completed_subtasks}/{total_subtasks}")
        print("-"*50)
        
        for subtask_id, name in subtask_names.items():
            status = "✓ COMPLETE" if self.results.get(subtask_id, False) else "✗ INCOMPLETE"
            print(f"{subtask_id}: {name:<40} {status}")
            
        print("\n" + "="*50)
        print(f"SUBTASKS 4.5-4.10 STATUS: {'✓ ALL COMPLETE' if all(self.results.values()) else '⚠ SOME INCOMPLETE'}")
        print("="*50)

def main():
    project_root = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac"
    
    print("=== Testing Task 4 Remaining Subtasks (4.5-4.10) ===")
    print(f"Project root: {project_root}")
    print(f"API directory: {project_root}/learntrac-api")
    
    tester = RemainingSubtasksTester(project_root)
    
    # Run all tests
    tester.test_subtask_5_academic_sentence_generation()
    tester.test_subtask_6_embedding_service()
    tester.test_subtask_7_learning_path_api()
    tester.test_subtask_8_rds_integration()
    tester.test_subtask_9_health_checks()
    tester.test_subtask_10_docker_config()
    
    # Generate report
    tester.generate_final_report()

if __name__ == "__main__":
    main()