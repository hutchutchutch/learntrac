#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

# Mock textbooks data
textbooks = [
    {
        "textbook_id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "Introduction to Computer Science",
        "subject": "Computer Science",
        "authors": ["John Doe", "Jane Smith"],
        "pages_processed": 450,
        "chunks_created": 1823,
        "created_at": "2024-01-15T10:30:00Z"
    },
    {
        "textbook_id": "123e4567-e89b-12d3-a456-426614174001",
        "title": "Advanced Mathematics",
        "subject": "Mathematics",
        "authors": ["Alice Johnson"],
        "pages_processed": 320,
        "chunks_created": 1290,
        "created_at": "2024-01-14T15:45:00Z"
    },
    {
        "textbook_id": "123e4567-e89b-12d3-a456-426614174002",
        "title": "Physics Fundamentals",
        "subject": "Physics",
        "authors": ["Bob Wilson", "Carol Davis"],
        "pages_processed": 580,
        "chunks_created": 2340,
        "created_at": "2024-01-13T09:20:00Z"
    }
]

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/trac/textbooks' or self.path.startswith('/api/trac/textbooks?'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"textbooks": textbooks}).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        if self.path == '/api/trac/textbooks/upload':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "textbook_id": "123e4567-e89b-12d3-a456-426614174003",
                "title": "Uploaded Textbook",
                "pages_processed": 200,
                "chunks_created": 800,
                "concepts_extracted": 150,
                "processing_time": 45.2,
                "status": "completed"
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def log_message(self, format, *args):
        # Override to add timestamp
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {format%args}")

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8001), APIHandler)
    print('Mock API server running on http://localhost:8001')
    print('Available endpoints:')
    print('  GET  /api/trac/textbooks')
    print('  POST /api/trac/textbooks/upload')
    print('  GET  /health')
    server.serve_forever()