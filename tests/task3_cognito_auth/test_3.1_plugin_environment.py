#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test 3.1: Verify Trac plugin development environment
This test verifies that the Trac plugin development environment is properly set up
with all required dependencies and the plugin structure follows Trac conventions.
"""

import os
import sys
import subprocess
import importlib
import json
from pathlib import Path

class PluginEnvironmentTester:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.plugin_dir = self.project_root / "plugins" / "cognitoauth"
        self.results = {}
        
    def test_plugin_structure(self):
        """Test 3.1.1: Verify plugin directory structure follows Trac conventions"""
        print("\n=== Test 3.1.1: Plugin Directory Structure ===")
        
        required_files = [
            "setup.py",
            "cognitoauth/__init__.py",
            "cognitoauth/plugin.py",
        ]
        
        optional_files = [
            "README.md",
            "MANIFEST.in",
            "cognitoauth/tests/__init__.py",
        ]
        
        all_good = True
        for file in required_files:
            filepath = self.plugin_dir / file
            if filepath.exists():
                print(f"✓ Required: {file}")
            else:
                print(f"✗ Missing required file: {file}")
                all_good = False
                
        for file in optional_files:
            filepath = self.plugin_dir / file
            if filepath.exists():
                print(f"✓ Optional: {file}")
            else:
                print(f"⚠ Optional file not found: {file}")
                
        self.results['plugin_structure'] = all_good
        return all_good
        
    def test_setup_py(self):
        """Test 3.1.2: Verify setup.py is properly configured"""
        print("\n=== Test 3.1.2: Setup.py Configuration ===")
        
        setup_path = self.plugin_dir / "setup.py"
        if not setup_path.exists():
            print("✗ setup.py not found")
            self.results['setup_py'] = False
            return False
            
        # Read setup.py content
        with open(setup_path, 'r') as f:
            content = f.read()
            
        # Check for required elements
        checks = {
            'name': 'name=' in content or 'name =' in content,
            'version': 'version=' in content or 'version =' in content,
            'packages': 'packages=' in content or 'find_packages()' in content,
            'entry_points': 'entry_points=' in content,
            'trac.plugins': '[trac.plugins]' in content,
        }
        
        all_good = True
        for check, present in checks.items():
            if present:
                print(f"✓ {check} defined")
            else:
                print(f"✗ {check} not found")
                all_good = False
                
        self.results['setup_py'] = all_good
        return all_good
        
    def test_dependencies(self):
        """Test 3.1.3: Verify required dependencies are available"""
        print("\n=== Test 3.1.3: Required Dependencies ===")
        
        required_modules = {
            'trac': 'Trac framework',
            'jwt': 'PyJWT for token validation',
            'requests': 'HTTP requests library',
            'boto3': 'AWS SDK (optional but recommended)',
        }
        
        all_good = True
        for module, description in required_modules.items():
            try:
                importlib.import_module(module)
                print(f"✓ {module} - {description}")
            except ImportError:
                if module == 'boto3':  # Optional
                    print(f"⚠ {module} - {description} (optional)")
                else:
                    print(f"✗ {module} - {description}")
                    all_good = False
                    
        self.results['dependencies'] = all_good
        return all_good
        
    def test_plugin_imports(self):
        """Test 3.1.4: Verify plugin can be imported without errors"""
        print("\n=== Test 3.1.4: Plugin Import Test ===")
        
        # Add plugin directory to Python path
        sys.path.insert(0, str(self.plugin_dir))
        
        try:
            # Try to import the plugin module
            import cognitoauth
            print("✓ cognitoauth package imports successfully")
            
            # Try to import the main plugin class
            from cognitoauth.plugin import CognitoAuthPlugin
            print("✓ CognitoAuthPlugin class imports successfully")
            
            # Check if it implements required interfaces
            from trac.core import Component, implements
            from trac.web.api import IAuthenticator, IRequestHandler
            
            print("✓ Required Trac interfaces available")
            
            self.results['plugin_imports'] = True
            return True
            
        except Exception as e:
            print(f"✗ Import error: {e}")
            self.results['plugin_imports'] = False
            return False
        finally:
            # Remove from path
            sys.path.remove(str(self.plugin_dir))
            
    def test_trac_ini_example(self):
        """Test 3.1.5: Verify trac.ini example configuration exists"""
        print("\n=== Test 3.1.5: Configuration Example ===")
        
        example_files = [
            self.project_root / "plugins" / "trac.ini.cognito.example",
            self.plugin_dir / "trac.ini.example",
        ]
        
        found = False
        for filepath in example_files:
            if filepath.exists():
                print(f"✓ Configuration example found: {filepath}")
                
                # Verify it contains cognito section
                with open(filepath, 'r') as f:
                    content = f.read()
                    if '[cognito]' in content:
                        print("✓ Contains [cognito] section")
                        found = True
                    else:
                        print("✗ Missing [cognito] section")
                break
        
        if not found:
            print("✗ No configuration example found")
            
        self.results['config_example'] = found
        return found
        
    def test_egg_build(self):
        """Test 3.1.6: Verify plugin can be built as egg"""
        print("\n=== Test 3.1.6: Plugin Build Test ===")
        
        # Check if egg file exists
        egg_files = list(self.plugin_dir.glob("dist/*.egg"))
        if egg_files:
            print(f"✓ Built egg found: {egg_files[0].name}")
            self.results['egg_build'] = True
            return True
            
        # Try to build
        try:
            os.chdir(self.plugin_dir)
            result = subprocess.run(
                [sys.executable, "setup.py", "bdist_egg"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✓ Plugin builds successfully")
                egg_files = list(self.plugin_dir.glob("dist/*.egg"))
                if egg_files:
                    print(f"✓ Egg created: {egg_files[0].name}")
                self.results['egg_build'] = True
                return True
            else:
                print(f"✗ Build failed: {result.stderr}")
                self.results['egg_build'] = False
                return False
                
        except Exception as e:
            print(f"✗ Build error: {e}")
            self.results['egg_build'] = False
            return False
            
    def test_aws_connectivity(self):
        """Test 3.1.7: Verify connectivity to AWS Cognito services"""
        print("\n=== Test 3.1.7: AWS Connectivity Test ===")
        
        import requests
        
        # Test connectivity to Cognito endpoints
        region = "us-east-2"
        user_pool_id = "us-east-2_IvxzMrWwg"
        
        endpoints = {
            'JWKS': f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json",
            'User Pool': f"https://cognito-idp.{region}.amazonaws.com/",
        }
        
        all_good = True
        for name, url in endpoints.items():
            try:
                response = requests.head(url, timeout=5)
                if response.status_code < 400 or response.status_code == 405:  # HEAD might not be allowed
                    print(f"✓ {name} endpoint accessible")
                else:
                    print(f"✗ {name} endpoint returned {response.status_code}")
                    all_good = False
            except Exception as e:
                print(f"✗ {name} endpoint error: {e}")
                all_good = False
                
        self.results['aws_connectivity'] = all_good
        return all_good
        
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("=== SUBTASK 3.1 VERIFICATION REPORT ===")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for v in self.results.values() if v)
        
        print(f"\nTest Results: {passed_tests}/{total_tests} passed")
        print("-"*40)
        
        for test, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{test:20} : {status}")
            
        print("\nSubtask 3.1 Status:", "✓ COMPLETE" if all(self.results.values()) else "✗ INCOMPLETE")
        
        if not all(self.results.values()):
            print("\nRequired Actions:")
            if not self.results.get('plugin_structure'):
                print("- Create missing plugin files")
            if not self.results.get('dependencies'):
                print("- Install missing Python dependencies")
            if not self.results.get('egg_build'):
                print("- Fix setup.py configuration")

def main():
    # Get project root
    project_root = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac"
    
    print("=== Testing Subtask 3.1: Trac Plugin Development Environment ===")
    print(f"Project root: {project_root}")
    
    tester = PluginEnvironmentTester(project_root)
    
    # Run all tests
    tester.test_plugin_structure()
    tester.test_setup_py()
    tester.test_dependencies()
    tester.test_plugin_imports()
    tester.test_trac_ini_example()
    tester.test_egg_build()
    tester.test_aws_connectivity()
    
    # Generate report
    tester.generate_report()

if __name__ == "__main__":
    main()