  const http = require('http');
  
  // Mock textbooks data
  const textbooks = [
    {
      textbook_id: '123e4567-e89b-12d3-a456-426614174000',
      title: 'Introduction to Computer Science',
      subject: 'Computer Science',
      authors: ['John Doe', 'Jane Smith'],
      pages_processed: 450,
      chunks_created: 1823,
      created_at: '2024-01-15T10:30:00Z'
    },
    {
      textbook_id: '123e4567-e89b-12d3-a456-426614174001',
      title: 'Advanced Mathematics',
      subject: 'Mathematics',
      authors: ['Alice Johnson'],
      pages_processed: 320,
      chunks_created: 1290,
      created_at: '2024-01-14T15:45:00Z'
    },
    {
      textbook_id: '123e4567-e89b-12d3-a456-426614174002',
      title: 'Physics Fundamentals',
      subject: 'Physics',
      authors: ['Bob Wilson', 'Carol Davis'],
      pages_processed: 580,
      chunks_created: 2340,
      created_at: '2024-01-13T09:20:00Z'
    }
  ];
  
  const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    if (req.url === '/api/trac/textbooks' || req.url.startsWith('/api/trac/textbooks?')) {
      res.writeHead(200);
      res.end(JSON.stringify({ textbooks }));
    } else if (req.url === '/api/trac/textbooks/upload' && req.method === 'POST') {
      res.writeHead(200);
      res.end(JSON.stringify({
        textbook_id: '123e4567-e89b-12d3-a456-426614174003',
        title: 'Uploaded Textbook',
        pages_processed: 200,
        chunks_created: 800,
        concepts_extracted: 150,
        processing_time: 45.2,
        status: 'completed'
      }));
    } else {
      res.writeHead(404);
      res.end(JSON.stringify({ error: 'Not found' }));
    }
  });
  
  server.listen(8001, () => {
    console.log('Mock API server running on http://localhost:8001');
    console.log('Available endpoints:');
    console.log('  GET  /api/trac/textbooks');
    console.log('  POST /api/trac/textbooks/upload');
  });
  EOF
  
  node server.js
