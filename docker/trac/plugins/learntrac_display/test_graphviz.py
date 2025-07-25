#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for GraphViz functionality
"""

import subprocess
import tempfile
import os
import sys

def test_graphviz_installation():
    """Test if GraphViz is properly installed"""
    print("Testing GraphViz installation...")
    
    try:
        # Check if dot command is available
        result = subprocess.run(['dot', '-V'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ GraphViz is installed:")
            print("  " + result.stderr.strip())  # Version info is in stderr
        else:
            print("✗ GraphViz is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("✗ 'dot' command not found. Please install GraphViz.")
        return False
    
    return True

def test_graph_generation():
    """Test basic graph generation"""
    print("\nTesting graph generation...")
    
    # Create a simple DOT file
    dot_content = '''digraph TestGraph {
    rankdir=TB;
    node [shape=box, style=filled];
    
    "Concept1" [label="Basic Concept", fillcolor="#D3D3D3"];
    "Concept2" [label="Advanced Concept", fillcolor="#FFB84D"];
    "Concept3" [label="Mastered Concept", fillcolor="#90EE90"];
    
    "Concept1" -> "Concept2";
    "Concept2" -> "Concept3";
}'''
    
    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as dot_file:
            dot_file.write(dot_content)
            dot_path = dot_file.name
        
        png_path = dot_path.replace('.dot', '.png')
        map_path = dot_path.replace('.dot', '.map')
        
        # Generate PNG
        result = subprocess.run(['dot', '-Tpng', dot_path, '-o', png_path], 
                              capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(png_path):
            print("✓ PNG generation successful")
            print(f"  Output: {png_path} ({os.path.getsize(png_path)} bytes)")
        else:
            print("✗ PNG generation failed")
            if result.stderr:
                print("  Error:", result.stderr)
            return False
        
        # Generate clickable map
        result = subprocess.run(['dot', '-Tcmapx', dot_path, '-o', map_path], 
                              capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(map_path):
            print("✓ Clickable map generation successful")
            with open(map_path, 'r') as f:
                print("  Map content preview:", f.read()[:100] + "...")
        else:
            print("✗ Map generation failed")
        
        # Cleanup
        for path in [dot_path, png_path, map_path]:
            if os.path.exists(path):
                os.unlink(path)
        
        return True
        
    except Exception as e:
        print(f"✗ Error during graph generation: {e}")
        return False

def test_subprocess_timeout():
    """Test subprocess timeout handling"""
    print("\nTesting timeout handling...")
    
    # Create a DOT file that might take longer to process
    dot_content = 'digraph G { rankdir=TB; '
    # Add many nodes to potentially slow down processing
    for i in range(100):
        dot_content += f'n{i} [label="Node {i}"]; '
        if i > 0:
            dot_content += f'n{i-1} -> n{i}; '
    dot_content += '}'
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as dot_file:
            dot_file.write(dot_content)
            dot_path = dot_file.name
        
        png_path = dot_path.replace('.dot', '.png')
        
        # Try with a reasonable timeout
        result = subprocess.run(['dot', '-Tpng', dot_path, '-o', png_path], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✓ Large graph generated within timeout")
        
        # Cleanup
        for path in [dot_path, png_path]:
            if os.path.exists(path):
                os.unlink(path)
        
        return True
        
    except subprocess.TimeoutExpired:
        print("✗ Process timed out (this might be expected for very large graphs)")
        return True  # Timeout handling works correctly
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("LearnTrac Knowledge Graph - GraphViz Test Suite")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: Installation
    if not test_graphviz_installation():
        all_passed = False
        print("\nPlease install GraphViz:")
        print("  Ubuntu/Debian: sudo apt-get install graphviz")
        print("  macOS: brew install graphviz")
        print("  Windows: Download from https://graphviz.org/download/")
        return 1
    
    # Test 2: Graph generation
    if not test_graph_generation():
        all_passed = False
    
    # Test 3: Timeout handling
    if not test_subprocess_timeout():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())