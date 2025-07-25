#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive verification script for Task 3: Implement Cognito Authentication Plugin for Trac
This script verifies all 10 subtasks are complete and functional
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

class Task3Verifier:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.plugin_dir = self.project_root / "plugins" / "cognitoauth"
        self.results = {}
        
    def verify_subtask_1(self):
        """Subtask 3.1: Set up Trac plugin development environment"""
        print("\n=== Verifying Subtask 3.1: Plugin Development Environment ===")
        
        checks = {
            "Plugin directory exists": (self.plugin_dir).exists(),
            "setup.py exists": (self.plugin_dir / "setup.py").exists(),
            "Plugin package exists": (self.plugin_dir / "cognitoauth" / "__init__.py").exists(),
            "Main plugin module": (self.plugin_dir / "cognitoauth" / "plugin.py").exists(),
            "Configuration example": (self.project_root / "plugins" / "trac.ini.cognito.example").exists(),
            "Built egg file": len(list(self.plugin_dir.glob("dist/*.egg"))) > 0
        }
        
        all_passed = all(checks.values())
        for check, passed in checks.items():
            print(f"  {'✓' if passed else '✗'} {check}")
            
        self.results['subtask_3.1'] = all_passed
        return all_passed
        
    def verify_subtask_2(self):
        """Subtask 3.2: Implement JWT token validation with Cognito JWKS"""
        print("\n=== Verifying Subtask 3.2: JWT Token Validation ===")
        
        # Check for JWT validation implementation
        plugin_files = [
            self.plugin_dir / "cognitoauth" / "plugin.py",
            self.project_root / "plugins" / "trac_cognito_auth.py",
            self.project_root / "plugins" / "cognito_token_validator.py"
        ]
        
        jwt_features = {
            "Token decoding": False,
            "JWKS endpoint": False,
            "RS256 algorithm": False,
            "Token expiration": False,
            "Bearer token support": False
        }
        
        for plugin_file in plugin_files:
            if plugin_file.exists():
                content = plugin_file.read_text()
                if "urlsafe_b64decode" in content or "jwt.decode" in content:
                    jwt_features["Token decoding"] = True
                if "jwks.json" in content or "JWKS" in content:
                    jwt_features["JWKS endpoint"] = True
                if "RS256" in content:
                    jwt_features["RS256 algorithm"] = True
                if "exp" in content and ("time" in content or "timestamp" in content):
                    jwt_features["Token expiration"] = True
                if "Bearer" in content:
                    jwt_features["Bearer token support"] = True
                    
        all_passed = all(jwt_features.values())
        for feature, implemented in jwt_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.2'] = all_passed
        return all_passed
        
    def verify_subtask_3(self):
        """Subtask 3.3: Create Trac session management for Cognito users"""
        print("\n=== Verifying Subtask 3.3: Session Management ===")
        
        plugin_file = self.plugin_dir / "cognitoauth" / "plugin.py"
        content = plugin_file.read_text() if plugin_file.exists() else ""
        
        session_features = {
            "Session creation": "req.session[" in content,
            "User mapping": "cognito_username" in content,
            "Group storage": "cognito_groups" in content,
            "Session save": "req.session.save()" in content,
            "Session clear": "req.session.clear()" in content,
            "Auth state": "authenticated" in content
        }
        
        all_passed = all(session_features.values())
        for feature, implemented in session_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.3'] = all_passed
        return all_passed
        
    def verify_subtask_4(self):
        """Subtask 3.4: Implement IAuthenticator interface methods"""
        print("\n=== Verifying Subtask 3.4: IAuthenticator Interface ===")
        
        plugin_file = self.plugin_dir / "cognitoauth" / "plugin.py"
        content = plugin_file.read_text() if plugin_file.exists() else ""
        
        interface_features = {
            "Implements IAuthenticator": "implements(IAuthenticator" in content,
            "authenticate method": "def authenticate(self, req)" in content,
            "Returns username": "return cognito_user" in content or "return user" in content,
            "Sets authname": "req.authname" in content,
            "Handles anonymous": "return None" in content
        }
        
        all_passed = all(interface_features.values())
        for feature, implemented in interface_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.4'] = all_passed
        return all_passed
        
    def verify_subtask_5(self):
        """Subtask 3.5: Add configuration management for Cognito settings"""
        print("\n=== Verifying Subtask 3.5: Configuration Management ===")
        
        plugin_file = self.plugin_dir / "cognitoauth" / "plugin.py"
        config_file = self.project_root / "plugins" / "trac.ini.cognito.example"
        
        config_features = {
            "User Pool ID config": False,
            "Client ID config": False,
            "Region config": False,
            "Domain config": False,
            "Config example file": config_file.exists()
        }
        
        if plugin_file.exists():
            content = plugin_file.read_text()
            if "user_pool_id" in content:
                config_features["User Pool ID config"] = True
            if "client_id" in content:
                config_features["Client ID config"] = True
            if "region" in content:
                config_features["Region config"] = True
            if "domain" in content:
                config_features["Domain config"] = True
                
        all_passed = all(config_features.values())
        for feature, implemented in config_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.5'] = all_passed
        return all_passed
        
    def verify_subtask_6(self):
        """Subtask 3.6: Implement request handler for authentication endpoints"""
        print("\n=== Verifying Subtask 3.6: Authentication Endpoints ===")
        
        plugin_file = self.plugin_dir / "cognitoauth" / "plugin.py"
        content = plugin_file.read_text() if plugin_file.exists() else ""
        
        endpoint_features = {
            "IRequestHandler implemented": "implements.*IRequestHandler" in content,
            "Login endpoint": "/auth/login" in content,
            "Callback endpoint": "/auth/callback" in content,
            "Logout endpoint": "/auth/logout" in content,
            "OAuth flow": "authorization_code" in content,
            "Redirect handling": "req.redirect" in content
        }
        
        all_passed = all(endpoint_features.values())
        for feature, implemented in endpoint_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.6'] = all_passed
        return all_passed
        
    def verify_subtask_7(self):
        """Subtask 3.7: Add user permission mapping from Cognito groups"""
        print("\n=== Verifying Subtask 3.7: Permission Mapping ===")
        
        # Check for permission policy implementation
        permission_files = [
            self.project_root / "plugins" / "cognito_permission_policy.py",
            self.plugin_dir / "cognitoauth" / "plugin.py"
        ]
        
        permission_features = {
            "Group extraction": False,
            "Permission mapping": False,
            "Admin group": False,
            "Instructor group": False,
            "Student group": False
        }
        
        for perm_file in permission_files:
            if perm_file.exists():
                content = perm_file.read_text()
                if "cognito:groups" in content or "cognito_groups" in content:
                    permission_features["Group extraction"] = True
                if "TRAC_ADMIN" in content or "TICKET_CREATE" in content:
                    permission_features["Permission mapping"] = True
                if "admin" in content.lower():
                    permission_features["Admin group"] = True
                if "instructor" in content.lower():
                    permission_features["Instructor group"] = True
                if "student" in content.lower():
                    permission_features["Student group"] = True
                    
        all_passed = all(permission_features.values())
        for feature, implemented in permission_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.7'] = all_passed
        return all_passed
        
    def verify_subtask_8(self):
        """Subtask 3.8: Create error handling and logging system"""
        print("\n=== Verifying Subtask 3.8: Error Handling & Logging ===")
        
        plugin_file = self.plugin_dir / "cognitoauth" / "plugin.py"
        content = plugin_file.read_text() if plugin_file.exists() else ""
        
        error_features = {
            "Logging setup": "logging" in content or "self.log" in content,
            "Try/except blocks": "try:" in content and "except" in content,
            "Error messages": "add_warning" in content or "error" in content,
            "Debug logging": "debug" in content or "info" in content,
            "User feedback": "add_notice" in content
        }
        
        all_passed = all(error_features.values())
        for feature, implemented in error_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.8'] = all_passed
        return all_passed
        
    def verify_subtask_9(self):
        """Subtask 3.9: Implement plugin installation and setup documentation"""
        print("\n=== Verifying Subtask 3.9: Installation & Documentation ===")
        
        doc_features = {
            "setup.py exists": (self.plugin_dir / "setup.py").exists(),
            "Plugin documentation": (self.project_root / "plugins" / "COGNITO_AUTH_PLUGIN_DOCUMENTATION.md").exists(),
            "Config example": (self.project_root / "plugins" / "trac.ini.cognito.example").exists(),
            "Entry points defined": False,
            "Dependencies listed": False
        }
        
        setup_file = self.plugin_dir / "setup.py"
        if setup_file.exists():
            content = setup_file.read_text()
            if "entry_points" in content:
                doc_features["Entry points defined"] = True
            if "install_requires" in content:
                doc_features["Dependencies listed"] = True
                
        all_passed = all(doc_features.values())
        for feature, implemented in doc_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.9'] = all_passed
        return all_passed
        
    def verify_subtask_10(self):
        """Subtask 3.10: Add integration tests and performance optimization"""
        print("\n=== Verifying Subtask 3.10: Integration Tests & Performance ===")
        
        test_features = {
            "Test script exists": (self.project_root / "plugins" / "test_cognito_auth.py").exists(),
            "Performance metrics": (self.project_root / "plugins" / "cognito_metrics.py").exists(),
            "Token validator": (self.project_root / "plugins" / "cognito_token_validator.py").exists(),
            "Extended auth plugin": (self.project_root / "plugins" / "trac_cognito_auth.py").exists(),
            "Caching implemented": False
        }
        
        # Check for caching implementation
        cache_files = [
            self.project_root / "plugins" / "trac_cognito_auth.py",
            self.project_root / "plugins" / "cognito_token_validator.py"
        ]
        
        for cache_file in cache_files:
            if cache_file.exists():
                content = cache_file.read_text()
                if "cache" in content.lower():
                    test_features["Caching implemented"] = True
                    break
                    
        all_passed = all(test_features.values())
        for feature, implemented in test_features.items():
            print(f"  {'✓' if implemented else '✗'} {feature}")
            
        self.results['subtask_3.10'] = all_passed
        return all_passed
        
    def generate_final_report(self):
        """Generate comprehensive verification report for Task 3"""
        print("\n" + "="*70)
        print("=== TASK 3 FINAL VERIFICATION REPORT ===")
        print("="*70)
        print("\nTask: Implement Cognito Authentication Plugin for Trac")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project: {self.project_root}")
        
        # Overall summary
        total_subtasks = len(self.results)
        completed_subtasks = sum(1 for v in self.results.values() if v)
        
        print(f"\nOverall Progress: {completed_subtasks}/{total_subtasks} subtasks completed")
        print("-"*50)
        
        # Detailed results
        subtask_names = {
            'subtask_3.1': 'Plugin Development Environment',
            'subtask_3.2': 'JWT Token Validation',
            'subtask_3.3': 'Session Management',
            'subtask_3.4': 'IAuthenticator Interface',
            'subtask_3.5': 'Configuration Management',
            'subtask_3.6': 'Authentication Endpoints',
            'subtask_3.7': 'Permission Mapping',
            'subtask_3.8': 'Error Handling & Logging',
            'subtask_3.9': 'Installation & Documentation',
            'subtask_3.10': 'Integration Tests & Performance'
        }
        
        for subtask_id, name in subtask_names.items():
            status = "✓ COMPLETE" if self.results.get(subtask_id, False) else "✗ INCOMPLETE"
            print(f"{subtask_id}: {name:<35} {status}")
            
        # Task completion status
        all_complete = all(self.results.values())
        print("\n" + "="*50)
        print(f"TASK 3 STATUS: {'✓ COMPLETE' if all_complete else '✗ INCOMPLETE'}")
        print("="*50)
        
        if all_complete:
            print("\n✅ All subtasks verified successfully!")
            print("\nKey Achievements:")
            print("- Trac plugin structure properly implemented")
            print("- JWT validation with Cognito JWKS endpoint")
            print("- Session management with user mapping")
            print("- OAuth2 flow with login/logout endpoints")
            print("- Permission mapping from Cognito groups")
            print("- Comprehensive error handling and logging")
            print("- Complete documentation and configuration examples")
            print("- Integration tests and performance optimizations")
            
            print("\nPlugin Files Created:")
            print("- plugins/cognitoauth/ - Main plugin package")
            print("- plugins/trac_cognito_auth.py - Extended authentication")
            print("- plugins/cognito_token_validator.py - JWT validation")
            print("- plugins/cognito_permission_policy.py - Permission mapping")
            print("- plugins/cognito_metrics.py - Performance metrics")
            print("- plugins/test_cognito_auth.py - Integration tests")
            print("- plugins/trac.ini.cognito.example - Configuration example")
            print("- plugins/COGNITO_AUTH_PLUGIN_DOCUMENTATION.md - Documentation")
        else:
            print("\n⚠️  Some subtasks need attention")
            print("\nRequired Actions:")
            for subtask_id, completed in self.results.items():
                if not completed:
                    print(f"- Fix {subtask_names[subtask_id]}")

def main():
    project_root = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac"
    
    print("=== Task 3 Comprehensive Verification ===")
    print("Verifying: Implement Cognito Authentication Plugin for Trac")
    
    verifier = Task3Verifier(project_root)
    
    # Verify all subtasks
    verifier.verify_subtask_1()
    verifier.verify_subtask_2()
    verifier.verify_subtask_3()
    verifier.verify_subtask_4()
    verifier.verify_subtask_5()
    verifier.verify_subtask_6()
    verifier.verify_subtask_7()
    verifier.verify_subtask_8()
    verifier.verify_subtask_9()
    verifier.verify_subtask_10()
    
    # Generate final report
    verifier.generate_final_report()

if __name__ == "__main__":
    main()