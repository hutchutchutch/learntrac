# PDFUploadMacro for Trac

A Trac wiki macro that provides PDF upload functionality integrated with the LearnTrac educational content processing system.

## Overview

PDFUploadMacro enables users to upload PDF documents directly from Trac wiki pages. Uploaded PDFs are automatically processed through the LearnTrac pipeline, which:

- Extracts and analyzes content structure
- Creates intelligent semantic chunks
- Generates high-quality embeddings
- Stores everything in Neo4j for intelligent retrieval
- Enables semantic search and learning path generation

## Features

- **Easy Integration**: Simple wiki macro syntax `[[PDFUpload]]`
- **Rich Metadata**: Capture title, subject, authors
- **Progress Tracking**: Real-time upload and processing feedback
- **Authentication Support**: Optional API token authentication
- **Responsive Design**: Works on desktop and mobile
- **Error Handling**: Clear error messages and recovery
- **Python 2.7 Compatible**: Works with legacy Trac installations

## Requirements

- Trac 1.0 or higher
- Python 2.7+
- LearnTrac API service running
- Neo4j database (via LearnTrac API)

## Quick Start

1. Install the plugin:
   ```bash
   python setup.py install
   ```

2. Enable in `trac.ini`:
   ```ini
   [components]
   pdfuploadmacro.* = enabled
   ```

3. Add to a wiki page:
   ```wiki
   [[PDFUpload]]
   ```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Trac Wiki     │     │  PDFUploadMacro  │     │  LearnTrac API  │
│     Page        │────▶│                  │────▶│                 │
│ [[PDFUpload]]   │     │  - Form render   │     │  - PDF process  │
└─────────────────┘     │  - File upload   │     │  - Embeddings   │
                        │  - API forward   │     │  - Neo4j store  │
                        └──────────────────┘     └─────────────────┘
```

## Configuration

### Basic Configuration

```ini
[learntrac]
api_endpoint = http://localhost:8000/api/trac
```

### Advanced Configuration

```ini
[learntrac]
# API endpoint
api_endpoint = https://api.learntrac.edu/api/trac

# Default API token (optional)
api_token = sk-learntrac-default-token

# Maximum upload size (bytes)
max_upload_size = 104857600  # 100MB

# Upload timeout (seconds)
upload_timeout = 300

# Allowed file extensions
allowed_extensions = .pdf

# Enable debug logging
debug = false
```

## Usage Examples

### Basic Upload Form

```wiki
= Upload Educational Content =

Use the form below to upload PDFs:

[[PDFUpload]]
```

### With Pre-selected Subject

```wiki
= Computer Science Materials =

Upload CS textbooks and papers:

[[PDFUpload(subject=Computer Science)]]
```

### Requiring Authentication

```wiki
= Secure Upload Area =

Authentication required for uploads:

[[PDFUpload(require_auth=true)]]
```

### Custom Parameters

```wiki
[[PDFUpload(subject=Mathematics,require_auth=true)]]
```

## API Integration

The macro integrates with the LearnTrac API endpoints:

### Upload Endpoint
```
POST /api/trac/textbooks/upload
Content-Type: multipart/form-data

Fields:
- file: PDF file (required)
- title: Textbook title (required)
- subject: Subject area (optional)
- authors: JSON array of authors (optional)
```

### Response Format
```json
{
  "textbook_id": "uuid",
  "title": "Introduction to Computer Science",
  "pages_processed": 450,
  "chunks_created": 1823,
  "concepts_extracted": 256,
  "processing_time": 45.2,
  "status": "completed"
}
```

## Processing Pipeline

When a PDF is uploaded:

1. **Upload Stage**
   - File validation
   - Metadata extraction
   - Temporary storage

2. **Processing Stage**
   - PDF content extraction
   - Structure analysis
   - Chapter/section detection

3. **Chunking Stage**
   - Semantic chunking (250-300 words)
   - Context preservation
   - Metadata enrichment

4. **Embedding Stage**
   - Vector generation (OpenAI/Sentence-BERT)
   - Quality assessment
   - Dimension optimization

5. **Storage Stage**
   - Neo4j graph creation
   - Vector indexing
   - Relationship mapping

6. **Completion Stage**
   - Search index update
   - User notification
   - Cleanup

## Permissions

The plugin uses Trac's permission system:

```bash
# Grant to all authenticated users
trac-admin /path/to/trac permission add authenticated LEARNTRAC_UPLOAD

# Grant to specific user
trac-admin /path/to/trac permission add john LEARNTRAC_UPLOAD

# Grant to user group
trac-admin /path/to/trac permission add students LEARNTRAC_UPLOAD
```

## Styling and Customization

### CSS Classes

The macro generates HTML with these CSS classes:
- `.pdf-upload-container` - Main container
- `.pdf-upload-form` - Upload form
- `.form-group` - Form field groups
- `.pdf-upload-submit` - Submit button
- `.upload-progress` - Progress indicator
- `.upload-results` - Results display

### Custom Styling

Add to your Trac theme:
```css
.pdf-upload-container {
    border: 2px solid #4CAF50;
    background: #f0f9f0;
}

.pdf-upload-submit {
    background: linear-gradient(to right, #4CAF50, #45a049);
}
```

## JavaScript Events

The macro triggers these events:

```javascript
// Upload started
document.addEventListener('pdfupload:start', function(e) {
    console.log('Upload started:', e.detail.filename);
});

// Upload progress
document.addEventListener('pdfupload:progress', function(e) {
    console.log('Progress:', e.detail.percent);
});

// Upload completed
document.addEventListener('pdfupload:complete', function(e) {
    console.log('Completed:', e.detail.textbook_id);
});

// Upload error
document.addEventListener('pdfupload:error', function(e) {
    console.error('Error:', e.detail.message);
});
```

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| "No file uploaded" | No file selected | User must select a file |
| "Upload timeout" | Large file or slow connection | Increase timeout settings |
| "Permission denied" | Missing LEARNTRAC_UPLOAD permission | Grant permission to user |
| "API connection failed" | LearnTrac API down | Check API service status |
| "Invalid PDF" | Corrupted or non-PDF file | Verify file is valid PDF |

## Development

### Project Structure

```
pdfuploadmacro/
├── pdfuploadmacro/
│   ├── __init__.py       # Package initialization
│   └── macro.py          # Main macro implementation
├── setup.py              # Plugin setup
├── README.md            # This file
├── INSTALL.md           # Installation guide
└── LICENSE              # License file
```

### Running Tests

```bash
# Run unit tests
python -m unittest discover tests/

# Run integration tests
python tests/integration_test.py
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Troubleshooting

### Enable Debug Logging

```ini
[learntrac]
debug = true

[logging]
log_type = file
log_level = DEBUG
```

### Check Plugin Status

```bash
trac-admin /path/to/trac plugin list | grep PDFUpload
```

### Manual API Test

```bash
# Test API connectivity
curl -X POST http://localhost:8000/api/trac/textbooks/upload \
  -H "Authorization: Bearer your-token" \
  -F "file=@test.pdf" \
  -F "title=Test Upload" \
  -F "subject=Computer Science"
```

## Performance Considerations

- **Large Files**: Files over 50MB may take several minutes
- **Concurrent Uploads**: Limit concurrent uploads to prevent overload
- **Caching**: Results are cached for 1 hour
- **Cleanup**: Temporary files are cleaned up after processing

## Security

- File type validation (PDF only)
- Size limits enforced
- Authentication support
- XSS protection in form rendering
- CSRF protection via Trac

## License

This plugin is released under the MIT License. See LICENSE file for details.

## Support

- Documentation: [LearnTrac Docs](https://learntrac.edu/docs)
- Issues: [GitHub Issues](https://github.com/learntrac/pdfuploadmacro/issues)
- Email: support@learntrac.edu

## Version History

- **1.0.0** (2024-01-15)
  - Initial release
  - Basic upload functionality
  - Authentication support
  - Progress tracking

---

*Part of the LearnTrac Educational Platform*