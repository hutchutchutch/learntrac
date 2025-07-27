#!/usr/bin/env python3
"""Test PDF upload through development endpoint"""

import requests
import sys
import os

def test_upload_dev():
    # Create a dummy PDF file for testing
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000339 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n438\n%%EOF"
    
    with open("test_dev.pdf", "wb") as f:
        f.write(pdf_content)
    
    # Test development API upload
    print("Testing development API upload to http://localhost:8001/api/trac/textbooks/upload-dev")
    
    with open("test_dev.pdf", "rb") as f:
        files = {'file': ('test_dev.pdf', f, 'application/pdf')}
        
        try:
            response = requests.post(
                "http://localhost:8001/api/trac/textbooks/upload-dev",
                files=files,
                headers={'X-Trac-Session': 'test-session'},
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("\n✓ Development upload endpoint works!")
            else:
                print(f"\n✗ Unexpected status code: {response.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Clean up
    os.remove("test_dev.pdf")

if __name__ == "__main__":
    test_upload_dev()