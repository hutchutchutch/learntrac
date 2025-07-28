#!/usr/bin/env python3
"""
Test script for enhanced vector search API endpoint
Tests the LLM-enhanced vector search functionality against Neo4j vector store
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# API configuration
API_BASE_URL = "http://localhost:8001/api/learntrac"
VECTOR_SEARCH_ENHANCED_URL = f"{API_BASE_URL}/vector/search/enhanced"
VECTOR_SEARCH_COMPARE_URL = f"{API_BASE_URL}/vector/search/compare"

# Test queries covering different topics
TEST_QUERIES = [
    # Computer Science fundamentals
    "What are binary search trees and how do they work?",
    "Explain recursion in programming",
    "How does dynamic programming optimize algorithms?",
    
    # Machine Learning / AI
    "What is gradient descent in machine learning?",
    "Explain neural networks and backpropagation",
    "How do transformers work in NLP?",
    
    # Data Structures
    "What are hash tables and their time complexity?",
    "Explain graph traversal algorithms",
    "How do priority queues work?",
    
    # Software Engineering
    "What are design patterns in software development?",
    "Explain SOLID principles",
    "How does version control work?",
    
    # Specific technical concepts
    "TCP/IP protocol stack",
    "Database normalization",
    "Concurrency and multithreading"
]

class VectorSearchTester:
    def __init__(self):
        self.session = None
        self.results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_enhanced_search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test the enhanced vector search endpoint"""
        default_params = {
            "query": query,
            "generate_sentences": 5,
            "min_score": 0.7,
            "limit": 10,
            "include_prerequisites": True,
            "include_generated_context": True
        }
        
        if params:
            default_params.update(params)
        
        start_time = time.time()
        
        try:
            async with self.session.post(
                VECTOR_SEARCH_ENHANCED_URL,
                json=default_params,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.time() - start_time
                
                result = {
                    "query": query,
                    "status_code": response.status,
                    "response_time": response_time,
                    "timestamp": datetime.now().isoformat()
                }
                
                if response.status == 200:
                    data = await response.json()
                    result["success"] = True
                    result["data"] = data
                    result["result_count"] = data.get("result_count", 0)
                    result["search_method"] = data.get("search_method", "unknown")
                else:
                    result["success"] = False
                    result["error"] = await response.text()
                
                return result
                
        except Exception as e:
            return {
                "query": query,
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_search_comparison(self, query: str) -> Dict[str, Any]:
        """Test the search comparison endpoint"""
        start_time = time.time()
        
        try:
            async with self.session.post(
                VECTOR_SEARCH_COMPARE_URL,
                json={
                    "query": query,
                    "min_score": 0.65,
                    "limit": 10
                },
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "query": query,
                        "success": True,
                        "data": data,
                        "response_time": response_time
                    }
                else:
                    return {
                        "query": query,
                        "success": False,
                        "error": await response.text(),
                        "response_time": response_time
                    }
                    
        except Exception as e:
            return {
                "query": query,
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    def print_result_summary(self, result: Dict[str, Any]):
        """Print a formatted summary of search results"""
        print(f"\n{'='*80}")
        print(f"Query: {result['query']}")
        print(f"Status: {'✅ Success' if result.get('success') else '❌ Failed'}")
        print(f"Response Time: {result.get('response_time', 0):.2f}s")
        
        if result.get('success'):
            data = result.get('data', {})
            print(f"Search Method: {data.get('search_method', 'unknown')}")
            print(f"Results Found: {data.get('result_count', 0)}")
            
            # Show generated context if available
            if 'generated_context' in data:
                context = data['generated_context']
                print(f"\nGenerated Academic Context ({context.get('sentence_count', 0)} sentences):")
                for i, sentence in enumerate(context.get('sentences', [])[:3], 1):
                    print(f"  {i}. {sentence[:100]}...")
                if context.get('sentence_count', 0) > 3:
                    print(f"  ... and {context['sentence_count'] - 3} more sentences")
            
            # Show top results
            results = data.get('results', [])
            if results:
                print(f"\nTop {min(3, len(results))} Results:")
                for i, result_item in enumerate(results[:3], 1):
                    print(f"  {i}. ID: {result_item.get('id')}")
                    print(f"     Score: {result_item.get('score', 0):.4f}")
                    print(f"     Content: {result_item.get('content', '')[:100]}...")
                    
                    # Show prerequisites if available
                    prereqs = result_item.get('prerequisites', [])
                    if prereqs:
                        print(f"     Prerequisites: {len(prereqs)} found")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    def print_comparison_summary(self, comparison_result: Dict[str, Any]):
        """Print a formatted summary of search comparison"""
        if not comparison_result.get('success'):
            print(f"\n❌ Comparison failed for '{comparison_result['query']}': {comparison_result.get('error')}")
            return
        
        data = comparison_result['data']
        comp = data['comparison']
        
        print(f"\n{'='*80}")
        print(f"Search Comparison for: {data['query']}")
        print(f"\nRegular Search:")
        print(f"  - Results: {comp['regular_search']['result_count']}")
        print(f"  - Top Scores: {', '.join(f'{s:.3f}' for s in comp['regular_search']['top_scores'])}")
        print(f"  - Unique Results: {comp['regular_search']['unique_results']}")
        
        print(f"\nEnhanced Search:")
        print(f"  - Results: {comp['enhanced_search']['result_count']}")
        print(f"  - Top Scores: {', '.join(f'{s:.3f}' for s in comp['enhanced_search']['top_scores'])}")
        print(f"  - Unique Results: {comp['enhanced_search']['unique_results']}")
        print(f"  - Generated Sentences: {len(comp['enhanced_search']['generated_sentences'])}")
        
        print(f"\nOverlap:")
        print(f"  - Common Results: {comp['overlap']['common_results']}")
        print(f"  - Overlap Percentage: {comp['overlap']['percentage']:.1f}%")

async def run_all_tests():
    """Run comprehensive tests on the enhanced vector search API"""
    print("🔍 Enhanced Vector Search API Test Suite")
    print("="*80)
    
    async with VectorSearchTester() as tester:
        # Test 1: Basic enhanced search with all test queries
        print("\n📋 Test 1: Enhanced Search with Various Queries")
        print("-"*40)
        
        enhanced_results = []
        for query in TEST_QUERIES:
            print(f"\nTesting: {query}")
            result = await tester.test_enhanced_search(query)
            tester.print_result_summary(result)
            enhanced_results.append(result)
            await asyncio.sleep(0.5)  # Small delay between requests
        
        # Test 2: Test with different parameters
        print("\n\n📋 Test 2: Enhanced Search with Different Parameters")
        print("-"*40)
        
        param_tests = [
            {
                "query": "What is machine learning?",
                "params": {"generate_sentences": 3, "min_score": 0.8}
            },
            {
                "query": "Database indexing strategies",
                "params": {"generate_sentences": 10, "min_score": 0.6, "limit": 20}
            },
            {
                "query": "REST API design",
                "params": {"include_prerequisites": False, "include_generated_context": False}
            }
        ]
        
        for test in param_tests:
            print(f"\nTesting with custom params: {test['query']}")
            print(f"Parameters: {test['params']}")
            result = await tester.test_enhanced_search(test['query'], test['params'])
            tester.print_result_summary(result)
            await asyncio.sleep(0.5)
        
        # Test 3: Search comparison
        print("\n\n📋 Test 3: Regular vs Enhanced Search Comparison")
        print("-"*40)
        
        comparison_queries = [
            "What are algorithms?",
            "Explain distributed systems",
            "How does caching work?"
        ]
        
        for query in comparison_queries:
            comparison = await tester.test_search_comparison(query)
            tester.print_comparison_summary(comparison)
            await asyncio.sleep(0.5)
        
        # Generate summary statistics
        print("\n\n📊 Test Summary Statistics")
        print("="*80)
        
        successful_tests = [r for r in enhanced_results if r.get('success')]
        failed_tests = [r for r in enhanced_results if not r.get('success')]
        
        print(f"Total Tests Run: {len(enhanced_results)}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Failed: {len(failed_tests)}")
        
        if successful_tests:
            avg_response_time = sum(r['response_time'] for r in successful_tests) / len(successful_tests)
            avg_results = sum(r.get('result_count', 0) for r in successful_tests) / len(successful_tests)
            
            print(f"\nAverage Response Time: {avg_response_time:.2f}s")
            print(f"Average Results per Query: {avg_results:.1f}")
            
            # Count search methods used
            methods = {}
            for r in successful_tests:
                method = r.get('data', {}).get('search_method', 'unknown')
                methods[method] = methods.get(method, 0) + 1
            
            print("\nSearch Methods Used:")
            for method, count in methods.items():
                print(f"  - {method}: {count} times")
        
        if failed_tests:
            print("\n⚠️  Failed Tests:")
            for r in failed_tests:
                print(f"  - {r['query']}: {r.get('error', 'Unknown error')}")
        
        # Save detailed results to file
        results_file = f"vector_search_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "test_run": datetime.now().isoformat(),
                "enhanced_search_results": enhanced_results,
                "summary": {
                    "total_tests": len(enhanced_results),
                    "successful": len(successful_tests),
                    "failed": len(failed_tests),
                    "average_response_time": avg_response_time if successful_tests else 0,
                    "average_results_count": avg_results if successful_tests else 0
                }
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(run_all_tests())