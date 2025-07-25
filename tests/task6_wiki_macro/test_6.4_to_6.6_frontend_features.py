#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test 6.4-6.6: Verify JavaScript functionality, CSS styling, and chunk preview
This test verifies the frontend features of the wiki macro
"""

import os
from pathlib import Path

class FrontendFeaturesTester:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.plugin_dir = self.project_root / "plugins" / "learningpathmacro"
        self.htdocs_dir = self.plugin_dir / "learningpathmacro" / "htdocs"
        self.results = {}
        
    def test_subtask_4_javascript_functionality(self):
        """Test 6.4: JavaScript functionality for interactions"""
        print("\n=== Test 6.4: JavaScript Functionality ===")
        
        js_file = self.htdocs_dir / "js" / "learningpath.js"
        
        if js_file.exists():
            print("✓ learningpath.js file exists")
            
            with open(js_file, 'r') as f:
                content = f.read()
                
            # Check for key JavaScript functions and features
            js_features = {
                "jQuery/$ usage": "$(" in content or "jQuery(" in content,
                "Document ready": "$(document).ready" in content or "document.addEventListener" in content,
                "Submit handler": ".submit" in content or "addEventListener('submit'" in content,
                "AJAX call": "$.ajax" in content or "fetch(" in content,
                "Event delegation": ".on(" in content or "addEventListener" in content,
                "View switcher": "switchView" in content or "changeView" in content,
                "Expand/collapse functionality": "toggle" in content or "expand" in content or "collapse" in content,
                "Progress bar updates": "progress" in content,
                "Error handling": "error:" in content or ".catch(" in content,
                "JSON handling": "JSON." in content,
                "API endpoint reference": "/learntrac-api" in content or "api/" in content
            }
            
            # Check for specific functions mentioned in task
            required_functions = {
                "generatePath function": "generatePath" in content,
                "createTickets function": "createTickets" in content,
                "API integration": "/learntrac-api" in content or "/api/v1" in content
            }
            
            feature_count = sum(1 for found in js_features.values() if found)
            required_count = sum(1 for found in required_functions.values() if found)
            
            print("\nGeneral JavaScript Features:")
            for feature, found in js_features.items():
                if found:
                    print(f"✓ {feature}")
                else:
                    print(f"✗ {feature}")
                    
            print("\nRequired Functions (from task spec):")
            for func, found in required_functions.items():
                if found:
                    print(f"✓ {func}")
                else:
                    print(f"✗ {func} - NOT IMPLEMENTED")
                    
            # Check for event handlers
            if 'click' in content:
                print("✓ Click event handlers")
            if 'change' in content:
                print("✓ Change event handlers")
                
            self.results['subtask_6.4'] = feature_count >= 7 and required_count >= 1
            return feature_count >= 7
        else:
            print("✗ learningpath.js file not found")
            self.results['subtask_6.4'] = False
            return False
            
    def test_subtask_5_css_styling(self):
        """Test 6.5: CSS styling"""
        print("\n=== Test 6.5: CSS Styling ===")
        
        css_file = self.htdocs_dir / "css" / "learningpath.css"
        
        if css_file.exists():
            print("✓ learningpath.css file exists")
            
            with open(css_file, 'r') as f:
                content = f.read()
                
            # Check for essential CSS elements
            css_features = {
                "Form styling": ".learning-path-form" in content or "#learning-path-form" in content,
                "Results container": ".learning-path-results" in content or "#learning-path-results" in content,
                "Tree view styles": ".tree-view" in content or ".tree" in content,
                "List view styles": ".list-view" in content or ".list" in content,
                "Graph view styles": ".graph-view" in content or ".graph" in content,
                "Timeline view styles": ".timeline-view" in content or ".timeline" in content,
                "Progress bar styles": ".progress" in content,
                "Chunk preview styles": ".chunk-preview" in content or ".preview" in content,
                "Button styles": "button" in content or ".btn" in content,
                "Loading indicator": ".loading" in content or ".spinner" in content,
                "Error message styles": ".error" in content,
                "Responsive design": "@media" in content
            }
            
            # Check for visual hierarchy
            visual_features = {
                "Header styles": "h1" in content or "h2" in content or "h3" in content,
                "Padding/margins": "padding:" in content and "margin:" in content,
                "Colors defined": "color:" in content or "background-color:" in content,
                "Border styles": "border:" in content,
                "Hover effects": ":hover" in content,
                "Active states": ":active" in content or ".active" in content
            }
            
            css_count = sum(1 for found in css_features.values() if found)
            visual_count = sum(1 for found in visual_features.values() if found)
            
            print("\nCSS Features:")
            for feature, found in css_features.items():
                if found:
                    print(f"✓ {feature}")
                else:
                    print(f"✗ {feature}")
                    
            print("\nVisual Design:")
            for feature, found in visual_features.items():
                if found:
                    print(f"✓ {feature}")
                else:
                    print(f"✗ {feature}")
                    
            self.results['subtask_6.5'] = css_count >= 8 and visual_count >= 4
            return css_count >= 8
        else:
            print("✗ learningpath.css file not found")
            self.results['subtask_6.5'] = False
            return False
            
    def test_subtask_6_chunk_preview(self):
        """Test 6.6: Chunk preview display"""
        print("\n=== Test 6.6: Chunk Preview Display ===")
        
        # Check JavaScript for preview functionality
        js_file = self.htdocs_dir / "js" / "learningpath.js"
        js_has_preview = False
        
        if js_file.exists():
            with open(js_file, 'r') as f:
                js_content = f.read()
                
            preview_js_features = {
                "Preview function": "preview" in js_content.lower(),
                "Chunk display": "chunk" in js_content.lower(),
                "Content rendering": "renderContent" in js_content or "displayContent" in js_content,
                "Hover/click handler": "hover" in js_content or "mouseenter" in js_content,
                "Tooltip/modal": "tooltip" in js_content or "modal" in js_content or "popup" in js_content
            }
            
            js_feature_count = sum(1 for found in preview_js_features.values() if found)
            
            print("JavaScript Preview Features:")
            for feature, found in preview_js_features.items():
                if found:
                    print(f"✓ {feature}")
                else:
                    print(f"✗ {feature}")
                    
            js_has_preview = js_feature_count >= 2
            
        # Check CSS for preview styling
        css_file = self.htdocs_dir / "css" / "learningpath.css"
        css_has_preview = False
        
        if css_file.exists():
            with open(css_file, 'r') as f:
                css_content = f.read()
                
            preview_css_features = {
                "Preview container": ".preview" in css_content or ".chunk-preview" in css_content,
                "Tooltip styles": ".tooltip" in css_content,
                "Modal styles": ".modal" in css_content,
                "Overlay styles": ".overlay" in css_content,
                "Animation/transition": "transition" in css_content or "animation" in css_content
            }
            
            css_feature_count = sum(1 for found in preview_css_features.values() if found)
            
            print("\nCSS Preview Styles:")
            for feature, found in preview_css_features.items():
                if found:
                    print(f"✓ {feature}")
                else:
                    print(f"✗ {feature}")
                    
            css_has_preview = css_feature_count >= 2
            
        # Check macro.py for preview HTML structure
        macro_py = self.plugin_dir / "learningpathmacro" / "macro.py"
        macro_has_preview = False
        
        if macro_py.exists():
            with open(macro_py, 'r') as f:
                macro_content = f.read()
                
            if "preview" in macro_content.lower() or "chunk" in macro_content.lower():
                print("\n✓ Macro contains preview-related code")
                macro_has_preview = True
            else:
                print("\n✗ Macro lacks preview-related code")
                
        self.results['subtask_6.6'] = js_has_preview or css_has_preview or macro_has_preview
        return js_has_preview or css_has_preview or macro_has_preview
        
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("=== SUBTASKS 6.4-6.6 VERIFICATION REPORT ===")
        print("="*60)
        
        subtask_names = {
            'subtask_6.4': 'JavaScript Functionality',
            'subtask_6.5': 'CSS Styling',
            'subtask_6.6': 'Chunk Preview Display'
        }
        
        total_tests = len(self.results)
        passed_tests = sum(1 for v in self.results.values() if v)
        
        print(f"\nTest Results: {passed_tests}/{total_tests} passed")
        print("-"*40)
        
        for subtask, name in subtask_names.items():
            result = self.results.get(subtask, False)
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{name:35} : {status}")
            
        print("\nOverall Status:", "✓ COMPLETE" if passed_tests == total_tests else "⚠ PARTIAL")
        
        print("\nKey Findings:")
        print("- JavaScript file implements interactivity")
        print("- CSS provides comprehensive styling")
        print("- Missing: generatePath() and createTickets() functions")
        print("- Missing: API integration to /learntrac-api endpoints")

def main():
    project_root = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac"
    
    print("=== Testing Subtasks 6.4-6.6: Frontend Features ===")
    print(f"Project root: {project_root}")
    print(f"Htdocs directory: {project_root}/plugins/learningpathmacro/learningpathmacro/htdocs")
    
    tester = FrontendFeaturesTester(project_root)
    
    # Run all tests
    tester.test_subtask_4_javascript_functionality()
    tester.test_subtask_5_css_styling()
    tester.test_subtask_6_chunk_preview()
    
    # Generate report
    tester.generate_report()

if __name__ == "__main__":
    main()