#!/usr/bin/env python3
"""
ElastiCache Redis Connection Test Script
Tests Redis connectivity and performs basic operations
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime

try:
    import redis
    import boto3
except ImportError:
    print("Error: Required packages not installed")
    print("Please run: pip install redis boto3")
    sys.exit(1)


class RedisValidator:
    def __init__(self, endpoint, port=6379, region='us-east-2'):
        self.endpoint = endpoint
        self.port = port
        self.region = region
        self.redis_client = None
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.elasticache = boto3.client('elasticache', region_name=region)
        
    def connect(self):
        """Establish connection to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.endpoint,
                port=self.port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            return False
    
    def test_basic_operations(self):
        """Test basic Redis operations"""
        print("\n=== Testing Basic Operations ===")
        tests_passed = 0
        tests_total = 6
        
        # Test 1: SET/GET
        try:
            key = f"learntrac:test:{int(time.time())}"
            value = "Hello LearnTrac!"
            self.redis_client.set(key, value)
            result = self.redis_client.get(key)
            if result == value:
                print("✅ SET/GET operations working")
                tests_passed += 1
            else:
                print("❌ SET/GET operations failed")
            self.redis_client.delete(key)
        except Exception as e:
            print(f"❌ SET/GET test failed: {e}")
        
        # Test 2: Hash operations
        try:
            hash_key = f"learntrac:user:{int(time.time())}"
            self.redis_client.hset(hash_key, mapping={
                "username": "testuser",
                "email": "test@learntrac.com",
                "created": str(datetime.utcnow())
            })
            user_data = self.redis_client.hgetall(hash_key)
            if user_data.get("username") == "testuser":
                print("✅ Hash operations working")
                tests_passed += 1
            else:
                print("❌ Hash operations failed")
            self.redis_client.delete(hash_key)
        except Exception as e:
            print(f"❌ Hash test failed: {e}")
        
        # Test 3: List operations
        try:
            list_key = f"learntrac:queue:{int(time.time())}"
            self.redis_client.lpush(list_key, "task1", "task2", "task3")
            length = self.redis_client.llen(list_key)
            if length == 3:
                print("✅ List operations working")
                tests_passed += 1
            else:
                print("❌ List operations failed")
            self.redis_client.delete(list_key)
        except Exception as e:
            print(f"❌ List test failed: {e}")
        
        # Test 4: Set operations
        try:
            set_key = f"learntrac:tags:{int(time.time())}"
            self.redis_client.sadd(set_key, "python", "redis", "aws")
            members = self.redis_client.smembers(set_key)
            if len(members) == 3:
                print("✅ Set operations working")
                tests_passed += 1
            else:
                print("❌ Set operations failed")
            self.redis_client.delete(set_key)
        except Exception as e:
            print(f"❌ Set test failed: {e}")
        
        # Test 5: Expiration
        try:
            exp_key = f"learntrac:session:{int(time.time())}"
            self.redis_client.setex(exp_key, 2, "temporary")
            ttl = self.redis_client.ttl(exp_key)
            if ttl > 0:
                print("✅ Expiration operations working")
                tests_passed += 1
            else:
                print("❌ Expiration operations failed")
        except Exception as e:
            print(f"❌ Expiration test failed: {e}")
        
        # Test 6: Transactions
        try:
            pipe = self.redis_client.pipeline()
            counter_key = f"learntrac:counter:{int(time.time())}"
            pipe.set(counter_key, 0)
            pipe.incr(counter_key)
            pipe.incr(counter_key)
            pipe.get(counter_key)
            results = pipe.execute()
            if results[-1] == "2":
                print("✅ Transaction operations working")
                tests_passed += 1
            else:
                print("❌ Transaction operations failed")
            self.redis_client.delete(counter_key)
        except Exception as e:
            print(f"❌ Transaction test failed: {e}")
        
        print(f"\nTests passed: {tests_passed}/{tests_total}")
        return tests_passed == tests_total
    
    def test_performance(self, iterations=1000):
        """Test Redis performance"""
        print("\n=== Testing Performance ===")
        
        # Test write performance
        start_time = time.time()
        for i in range(iterations):
            self.redis_client.set(f"perf:test:{i}", f"value{i}")
        write_time = time.time() - start_time
        write_ops_per_sec = iterations / write_time
        
        print(f"✅ Write performance: {write_ops_per_sec:.0f} ops/sec")
        
        # Test read performance
        start_time = time.time()
        for i in range(iterations):
            self.redis_client.get(f"perf:test:{i}")
        read_time = time.time() - start_time
        read_ops_per_sec = iterations / read_time
        
        print(f"✅ Read performance: {read_ops_per_sec:.0f} ops/sec")
        
        # Cleanup
        for i in range(iterations):
            self.redis_client.delete(f"perf:test:{i}")
        
        return write_ops_per_sec, read_ops_per_sec
    
    def check_memory_stats(self):
        """Check Redis memory statistics"""
        print("\n=== Memory Statistics ===")
        try:
            info = self.redis_client.info('memory')
            used_memory_human = info.get('used_memory_human', 'N/A')
            used_memory_peak_human = info.get('used_memory_peak_human', 'N/A')
            mem_fragmentation_ratio = info.get('mem_fragmentation_ratio', 'N/A')
            
            print(f"Used Memory: {used_memory_human}")
            print(f"Peak Memory: {used_memory_peak_human}")
            print(f"Fragmentation Ratio: {mem_fragmentation_ratio}")
            
            if isinstance(mem_fragmentation_ratio, (int, float)) and mem_fragmentation_ratio > 1.5:
                print("⚠️  Warning: High memory fragmentation detected")
            
            return info
        except Exception as e:
            print(f"❌ Failed to get memory stats: {e}")
            return None
    
    def check_replication_stats(self):
        """Check Redis replication statistics"""
        print("\n=== Replication Statistics ===")
        try:
            info = self.redis_client.info('replication')
            role = info.get('role', 'N/A')
            connected_slaves = info.get('connected_slaves', 0)
            
            print(f"Role: {role}")
            print(f"Connected Slaves: {connected_slaves}")
            
            return info
        except Exception as e:
            print(f"❌ Failed to get replication stats: {e}")
            return None
    
    def check_persistence_config(self):
        """Check Redis persistence configuration"""
        print("\n=== Persistence Configuration ===")
        try:
            # Check RDB configuration
            save_config = self.redis_client.config_get('save')
            print(f"RDB Save: {save_config.get('save', 'Not configured')}")
            
            # Check AOF configuration
            aof_enabled = self.redis_client.config_get('appendonly')
            print(f"AOF Enabled: {aof_enabled.get('appendonly', 'no')}")
            
            return True
        except Exception as e:
            print(f"❌ Failed to get persistence config: {e}")
            return False
    
    def generate_report(self):
        """Generate comprehensive validation report"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': self.endpoint,
            'port': self.port,
            'connection_status': 'connected' if self.redis_client else 'disconnected',
            'tests': {},
            'recommendations': []
        }
        
        if self.redis_client:
            # Get server info
            try:
                info = self.redis_client.info()
                report['redis_version'] = info.get('redis_version', 'unknown')
                report['uptime_days'] = info.get('uptime_in_days', 0)
                report['connected_clients'] = info.get('connected_clients', 0)
                
                # Memory info
                memory_info = self.redis_client.info('memory')
                report['memory_used_mb'] = round(memory_info.get('used_memory', 0) / 1024 / 1024, 2)
                report['memory_peak_mb'] = round(memory_info.get('used_memory_peak', 0) / 1024 / 1024, 2)
                
                # Add recommendations based on findings
                if report['memory_used_mb'] > 400:  # ~80% of t3.micro memory
                    report['recommendations'].append("Consider upgrading instance type - memory usage is high")
                
                if memory_info.get('mem_fragmentation_ratio', 1) > 1.5:
                    report['recommendations'].append("High memory fragmentation detected - consider restarting Redis")
                
            except Exception as e:
                report['error'] = str(e)
        
        return report


def main():
    parser = argparse.ArgumentParser(description='Test ElastiCache Redis connection')
    parser.add_argument('--endpoint', help='Redis endpoint (will fetch from AWS if not provided)')
    parser.add_argument('--port', type=int, default=6379, help='Redis port (default: 6379)')
    parser.add_argument('--region', default='us-east-2', help='AWS region (default: us-east-2)')
    parser.add_argument('--cluster-id', default='hutch-learntrac-dev-redis', help='ElastiCache cluster ID')
    parser.add_argument('--performance-test', action='store_true', help='Run performance tests')
    parser.add_argument('--json-report', action='store_true', help='Output JSON report')
    
    args = parser.parse_args()
    
    # Get endpoint from AWS if not provided
    if not args.endpoint:
        try:
            elasticache = boto3.client('elasticache', region_name=args.region)
            response = elasticache.describe_cache_clusters(
                CacheClusterId=args.cluster_id,
                ShowCacheNodeInfo=True
            )
            if response['CacheClusters']:
                cluster = response['CacheClusters'][0]
                if cluster['CacheNodes']:
                    args.endpoint = cluster['CacheNodes'][0]['Endpoint']['Address']
                    print(f"✅ Found Redis endpoint: {args.endpoint}")
                else:
                    print("❌ No cache nodes found in cluster")
                    sys.exit(1)
            else:
                print(f"❌ Cluster {args.cluster_id} not found")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Failed to fetch cluster information: {e}")
            sys.exit(1)
    
    # Create validator
    validator = RedisValidator(args.endpoint, args.port, args.region)
    
    print(f"\n🔍 Testing Redis connection to {args.endpoint}:{args.port}")
    
    # Connect to Redis
    if not validator.connect():
        print("\n❌ Cannot proceed without Redis connection")
        sys.exit(1)
    
    print("✅ Successfully connected to Redis")
    
    # Run tests
    all_passed = True
    
    # Basic operations test
    if not validator.test_basic_operations():
        all_passed = False
    
    # Performance test (optional)
    if args.performance_test:
        validator.test_performance()
    
    # Check various stats
    validator.check_memory_stats()
    validator.check_replication_stats()
    validator.check_persistence_config()
    
    # Generate report
    report = validator.generate_report()
    
    if args.json_report:
        print("\n=== JSON Report ===")
        print(json.dumps(report, indent=2))
    else:
        print("\n=== Summary ===")
        if all_passed:
            print("✅ All validation tests passed!")
        else:
            print("⚠️  Some tests failed - review the output above")
        
        if report['recommendations']:
            print("\n📋 Recommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
    
    # Disconnect
    if validator.redis_client:
        validator.redis_client.close()
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()