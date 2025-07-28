#!/usr/bin/env python3
"""
Clear Neo4j database via API
"""

import requests
import sys

# Make API call to clear database
def clear_database():
    try:
        # First check the current graph status
        print("Checking current graph status...")
        response = requests.get("http://localhost:8001/api/trac/debug/graph-status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"Current database status: {data.get('status')}")
            print(f"Node counts: {data.get('node_counts', {})}")
            print(f"Textbooks: {len(data.get('textbooks', []))}")
        else:
            print(f"Failed to get graph status: {response.status_code}")
            return False
        
        print("\nNote: No direct clear endpoint available. Database will be cleared during upload.")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if clear_database():
        print("Database status checked successfully")
        sys.exit(0)
    else:
        print("Failed to check database status")
        sys.exit(1)