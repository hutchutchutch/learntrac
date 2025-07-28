#!/usr/bin/env python3
"""
Test script for LearnTrac API endpoints
Demonstrates how to test LLM and Vector Search functionality
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, List

# API Configuration
BASE_URL = "http://localhost:8001"
AUTH_COOKIE = "trac_auth=YOUR_SESSION_TOKEN_HERE"  # Replace with actual session token

# Or use basic auth
BASIC_AUTH = aiohttp.BasicAuth("admin", "admin")  # Replace with actual credentials


class LearnTracAPITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "Cookie": AUTH_COOKIE
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_llm_generate_question(self) -> Dict[str, Any]:
        """Test single question generation"""
        print("\n=== Testing LLM Generate Question ===")
        
        payload = {
            "chunk_content": "Python functions are reusable blocks of code that perform specific tasks. They are defined using the 'def' keyword, followed by the function name and parameters in parentheses. Functions can accept arguments and return values using the 'return' statement. They help in organizing code, avoiding repetition, and making programs more modular.",
            "concept": "Python Functions",
            "difficulty": 3,
            "context": "Introduction to Programming course",
            "question_type": "comprehension"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/learntrac/llm/generate-question",
            json=payload
        ) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            print(f"Response: {json.dumps(result, indent=2)}")
            return result
    
    async def test_llm_multiple_questions(self) -> Dict[str, Any]:
        """Test multiple question generation"""
        print("\n=== Testing LLM Generate Multiple Questions ===")
        
        payload = {
            "chunk_content": "Object-oriented programming (OOP) is a programming paradigm based on the concept of objects, which contain data (attributes) and code (methods). The four main principles of OOP are encapsulation, inheritance, polymorphism, and abstraction. Classes serve as blueprints for creating objects.",
            "concept": "Object-Oriented Programming",
            "count": 3,
            "difficulty_range": [2, 4],
            "question_types": ["comprehension", "application", "analysis"]
        }
        
        async with self.session.post(
            f"{self.base_url}/api/learntrac/llm/generate-multiple-questions",
            json=payload
        ) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            print(f"Generated {result.get('generated_count', 0)} questions")
            return result
    
    async def test_llm_analyze_content(self) -> Dict[str, Any]:
        """Test content analysis"""
        print("\n=== Testing LLM Analyze Content ===")
        
        payload = {
            "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It uses algorithms to analyze data, identify patterns, and make decisions. Common types include supervised learning, unsupervised learning, and reinforcement learning.",
            "analysis_type": "difficulty"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/learntrac/llm/analyze-content",
            json=payload
        ) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            print(f"Analysis: {result.get('analysis', 'No analysis')}")
            return result
    
    async def test_vector_search(self) -> Dict[str, Any]:
        """Test vector similarity search"""
        print("\n=== Testing Vector Search ===")
        
        payload = {
            "query": "How do neural networks learn from data?",
            "min_score": 0.65,
            "limit": 5,
            "include_prerequisites": True,
            "include_dependents": False
        }
        
        async with self.session.post(
            f"{self.base_url}/api/learntrac/vector/search",
            json=payload
        ) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            print(f"Found {result.get('count', 0)} results")
            
            # Display top results
            for i, item in enumerate(result.get('results', [])[:3]):
                print(f"\nResult {i+1}:")
                print(f"  Score: {item.get('score', 0):.3f}")
                print(f"  Concept: {item.get('concept', 'N/A')}")
                print(f"  Content: {item.get('content', '')[:100]}...")
            
            return result
    
    async def test_create_chunk(self) -> Dict[str, Any]:
        """Test creating a new chunk"""
        print("\n=== Testing Create Chunk ===")
        
        payload = {
            "content": "Recursion is a programming technique where a function calls itself to solve a problem. Each recursive call works on a smaller subset of the problem until reaching a base case that can be solved directly. Common examples include factorial calculation and tree traversal.",
            "subject": "Computer Science",
            "concept": "Recursion",
            "has_prerequisite": [],
            "metadata": {
                "difficulty_level": 3,
                "estimated_learning_time": "30 minutes",
                "programming_language": "Python"
            }
        }
        
        async with self.session.post(
            f"{self.base_url}/api/learntrac/vector/chunks",
            json=payload
        ) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            print(f"Created chunk: {result.get('chunk_id', 'Unknown')}")
            return result
    
    async def test_enhanced_vector_search(self) -> Dict[str, Any]:
        """Test enhanced vector search with LLM-generated context"""
        print("\n=== Testing Enhanced Vector Search ===")
        
        payload = {
            "query": "neural network backpropagation",
            "generate_sentences": 5,
            "min_score": 0.7,
            "limit": 10,
            "include_prerequisites": True,
            "include_generated_context": True
        }
        
        async with self.session.post(
            f"{self.base_url}/api/learntrac/vector/search/enhanced",
            json=payload
        ) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            print(f"Search Method: {result.get('search_method', 'unknown')}")
            print(f"Found {result.get('result_count', 0)} results")
            
            # Display generated context
            if 'generated_context' in result:
                context = result['generated_context']
                print(f"\nGenerated {context.get('sentence_count', 0)} academic sentences:")
                for i, sentence in enumerate(context.get('sentences', [])[:3]):
                    print(f"  {i+1}: {sentence[:100]}...")
            
            # Display top results
            for i, item in enumerate(result.get('results', [])[:2]):
                print(f"\nResult {i+1}:")
                print(f"  Score: {item.get('score', 0):.3f}")
                print(f"  Concept: {item.get('concept', 'N/A')}")
                print(f"  Prerequisites: {len(item.get('prerequisites', []))} found")
            
            return result
    
    async def test_search_comparison(self) -> Dict[str, Any]:
        """Test comparison between regular and enhanced search"""
        print("\n=== Testing Search Method Comparison ===")
        
        payload = {
            "query": "database optimization techniques",
            "min_score": 0.65,
            "limit": 10
        }
        
        async with self.session.post(
            f"{self.base_url}/api/learntrac/vector/search/compare",
            json=payload
        ) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            
            comparison = result.get('comparison', {})
            regular = comparison.get('regular_search', {})
            enhanced = comparison.get('enhanced_search', {})
            overlap = comparison.get('overlap', {})
            
            print(f"\nRegular Search: {regular.get('result_count', 0)} results")
            print(f"Enhanced Search: {enhanced.get('result_count', 0)} results")
            print(f"Common Results: {overlap.get('common_results', 0)} ({overlap.get('percentage', 0):.1f}% overlap)")
            print(f"Unique to Enhanced: {enhanced.get('unique_results', 0)} results")
            
            # Show sample generated sentences
            sentences = enhanced.get('generated_sentences', [])
            if sentences:
                print(f"\nGenerated Sentences (first 2):")
                for i, sentence in enumerate(sentences[:2]):
                    print(f"  {i+1}: {sentence[:100]}...")
            
            return result
    
    async def test_bulk_vector_search(self) -> Dict[str, Any]:
        """Test bulk vector search"""
        print("\n=== Testing Bulk Vector Search ===")
        
        payload = {
            "queries": [
                "What is polymorphism in OOP?",
                "How do databases handle transactions?",
                "Explain REST API principles"
            ],
            "min_score": 0.65,
            "limit_per_query": 3
        }
        
        async with self.session.post(
            f"{self.base_url}/api/learntrac/vector/search/bulk",
            json=payload
        ) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            print(f"Processed {result.get('successful_queries', 0)} queries")
            
            # Display results for each query
            for search in result.get('searches', []):
                print(f"\nQuery: {search.get('query')}")
                print(f"Results: {search.get('count', 0)}")
            
            return result
    
    async def test_health_checks(self) -> Dict[str, Any]:
        """Test health check endpoints"""
        print("\n=== Testing Health Check Endpoints ===")
        
        # Test LLM health
        async with self.session.get(
            f"{self.base_url}/api/learntrac/llm/health"
        ) as response:
            llm_health = await response.json()
            print(f"LLM Health Status: {llm_health.get('status', 'Unknown')}")
            if llm_health.get('circuit_breaker_state'):
                print(f"Circuit Breaker: {llm_health['circuit_breaker_state']}")
        
        # Test Vector Search health
        async with self.session.get(
            f"{self.base_url}/api/learntrac/vector/health"
        ) as response:
            vector_health = await response.json()
            print(f"Vector Search Health Status: {vector_health.get('status', 'Unknown')}")
            if vector_health.get('chunk_count'):
                print(f"Total Chunks: {vector_health['chunk_count']}")
        
        return {"llm": llm_health, "vector": vector_health}
    
    async def test_llm_stats(self) -> Dict[str, Any]:
        """Test LLM statistics endpoint (requires admin)"""
        print("\n=== Testing LLM Stats (Admin Only) ===")
        
        try:
            async with self.session.get(
                f"{self.base_url}/api/learntrac/llm/stats"
            ) as response:
                if response.status == 403:
                    print("Access denied - admin permissions required")
                    return {"error": "Admin permissions required"}
                
                stats = await response.json()
                print(f"Circuit Breaker State: {stats.get('circuit_breaker', {}).get('state', 'Unknown')}")
                print(f"Failure Count: {stats.get('circuit_breaker', {}).get('failure_count', 0)}")
                return stats
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"error": str(e)}


async def run_all_tests():
    """Run all API tests"""
    print("Starting LearnTrac API Tests...")
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    async with LearnTracAPITester() as tester:
        # Run health checks first
        await tester.test_health_checks()
        
        # Test LLM endpoints
        await tester.test_llm_generate_question()
        await tester.test_llm_multiple_questions()
        await tester.test_llm_analyze_content()
        
        # Test Vector Search endpoints
        await tester.test_vector_search()
        await tester.test_create_chunk()
        await tester.test_enhanced_vector_search()
        await tester.test_search_comparison()
        await tester.test_bulk_vector_search()
        
        # Test admin endpoints
        await tester.test_llm_stats()
    
    print("\n" + "=" * 50)
    print("All tests completed!")


async def test_specific_endpoint():
    """Test a specific endpoint for debugging"""
    async with LearnTracAPITester() as tester:
        # Uncomment the test you want to run
        # await tester.test_llm_generate_question()
        # await tester.test_vector_search()
        await tester.test_health_checks()


if __name__ == "__main__":
    # Run all tests
    asyncio.run(run_all_tests())
    
    # Or run specific test
    # asyncio.run(test_specific_endpoint())