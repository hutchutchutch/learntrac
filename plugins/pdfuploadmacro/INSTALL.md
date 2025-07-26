# PDFUploadMacro Installation Guide

This guide explains how to install and configure the PDFUploadMacro plugin for Trac, which enables PDF upload functionality in wiki pages.

## Prerequisites

- Trac 1.0 or higher
- Python 2.7 (compatible with legacy Trac installations)
- Access to Trac configuration files
- LearnTrac API running (default: http://localhost:8000)

## Installation Steps

### 1. Install the Plugin

Navigate to the plugin directory and install:

```bash
cd /path/to/learntrac/plugins/pdfuploadmacro
python setup.py install
```

For development mode (if you want to make changes):
```bash
python setup.py develop
```

### 2. Enable the Plugin

Edit your `trac.ini` file and add the following under `[components]`:

```ini
[components]
pdfuploadmacro.* = enabled
```

### 3. Configure LearnTrac API Connection

Add the LearnTrac configuration section to `trac.ini`:

```ini
[learntrac]
# API endpoint for the LearnTrac service
api_endpoint = http://localhost:8000/api/trac

# Optional: Default API token for server-side authentication
# If not set, users will need to provide their own tokens
api_token = your-default-api-token-here

# Optional: Maximum upload size in bytes (default: 100MB)
max_upload_size = 104857600

# Optional: Allowed file extensions (comma-separated)
allowed_extensions = .pdf
```

### 4. Configure Permissions

The plugin uses the `LEARNTRAC_UPLOAD` permission. Grant this to appropriate users:

```bash
# Grant upload permission to authenticated users
trac-admin /path/to/trac permission add authenticated LEARNTRAC_UPLOAD

# Or grant to specific users
trac-admin /path/to/trac permission add username LEARNTRAC_UPLOAD

# Or grant to specific groups
trac-admin /path/to/trac permission add developers LEARNTRAC_UPLOAD
```

### 5. Configure Web Server (if needed)

If using Apache with mod_wsgi, ensure the upload handler is accessible:

```apache
# Add to your Apache configuration
<Location /trac/learntrac/upload>
    # Increase timeout for large file uploads
    TimeOut 600
    
    # Increase request body size limit
    LimitRequestBody 104857600
</Location>
```

For nginx:
```nginx
# Add to your nginx configuration
location /trac/learntrac/upload {
    # Increase timeout for large uploads
    proxy_read_timeout 600;
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    
    # Increase body size limit
    client_max_body_size 100M;
}
```

### 6. Restart Trac

After installation and configuration, restart your Trac instance:

```bash
# If using standalone tracd
killall tracd
tracd --port 8000 /path/to/trac

# If using Apache
sudo service apache2 restart

# If using nginx + gunicorn
sudo service nginx restart
sudo service gunicorn restart
```

## Usage

### Basic Usage in Wiki Pages

Add the following macro to any wiki page:

```wiki
[[PDFUpload]]
```

### Advanced Usage

With custom parameters:
```wiki
[[PDFUpload(subject=Computer Science,require_auth=true)]]
```

Available parameters:
- `subject`: Pre-select the subject dropdown (Computer Science, Mathematics, Physics, etc.)
- `require_auth`: If `true`, users must provide their API token

### Example Wiki Page

Create a new wiki page called `PDFLibrary`:

```wiki
= PDF Library Upload =

Welcome to the LearnTrac PDF Library. Use the form below to upload educational materials.

== Upload New Content ==

[[PDFUpload(subject=Computer Science)]]

== Guidelines ==

 * Only upload educational PDFs (textbooks, course materials, research papers)
 * Files should be under 100MB
 * Ensure you have the rights to upload the content
 * Processing may take several minutes for large files

== After Upload ==

Once your PDF is processed, you can:
 * Search the content using [wiki:LearningSearch]
 * View extracted concepts in [wiki:ConceptExplorer]
 * Track your learning progress in [wiki:LearningDashboard]
```

## Testing the Installation

### 1. Check Plugin Status

Navigate to the Trac admin panel and verify the plugin is enabled:
- Go to `/trac/admin/general/plugin`
- Look for "PDFUploadMacro 1.0.0"
- Ensure it shows as "Enabled"

### 2. Test the Macro

1. Create a test wiki page
2. Add `[[PDFUpload]]` to the page
3. Save and view the page
4. You should see the upload form

### 3. Test Upload Functionality

1. Select a small test PDF
2. Fill in the metadata
3. Click "Upload and Process PDF"
4. Monitor the progress bar
5. Check for success message with processing statistics

### 4. Verify API Connection

Test the upload handler directly:
```bash
curl -X GET http://your-trac-url/learntrac/upload
```

Should return:
```json
{
  "endpoint": "/learntrac/upload",
  "method": "POST",
  "description": "Upload PDF for processing",
  "parameters": {
    "file": "PDF file (required)",
    "title": "Textbook title (required)",
    "subject": "Subject area (optional)",
    "authors": "Comma-separated authors (optional)",
    "auth_token": "API authentication token (optional)"
  }
}
```

## Troubleshooting

### Plugin Not Appearing

1. Check Python path:
```python
python -c "import pdfuploadmacro; print(pdfuploadmacro.__file__)"
```

2. Verify Trac can find the plugin:
```bash
trac-admin /path/to/trac plugin list
```

3. Check Trac logs:
```bash
tail -f /path/to/trac/log/trac.log
```

### Upload Failures

1. **"No file uploaded" error**
   - Ensure form has `enctype="multipart/form-data"`
   - Check browser console for JavaScript errors

2. **"Upload timeout" error**
   - Increase timeout settings in web server config
   - Check LearnTrac API is running
   - Verify network connectivity

3. **"Permission denied" error**
   - Ensure user has LEARNTRAC_UPLOAD permission
   - Check file system permissions for temp directory

4. **"Internal server error"**
   - Check Trac error log
   - Verify API endpoint configuration
   - Test API connectivity manually

### API Connection Issues

Test API connectivity:
```bash
# Test from Trac server
curl -X GET http://localhost:8000/api/trac/health

# Test with authentication
curl -X GET http://localhost:8000/api/trac/health \
  -H "Authorization: Bearer your-token"
```

### Large File Issues

For files over 50MB:
1. Increase timeouts in web server config
2. Increase `max_upload_size` in trac.ini
3. Consider using background processing
4. Monitor server resources during upload

## Security Considerations

1. **File Validation**
   - The plugin only accepts .pdf files
   - Files are scanned for basic validity
   - Consider adding virus scanning for production

2. **Authentication**
   - Use `require_auth=true` for sensitive environments
   - Implement rate limiting in web server
   - Monitor upload logs for abuse

3. **API Security**
   - Use HTTPS for API connections in production
   - Rotate API tokens regularly
   - Implement IP whitelisting if needed

## Customization

### Styling

Add custom CSS to your Trac theme:
```css
/* Custom PDF upload styling */
.pdf-upload-container {
    max-width: 600px;
    margin: 20px auto;
}

.pdf-upload-submit {
    background-color: #your-brand-color;
}
```

### Adding Fields

To add custom metadata fields, edit `macro.py`:
1. Add form field in HTML generation
2. Add field to FormData in JavaScript
3. Update API to handle new field

### Localization

For multi-language support:
1. Extract strings to translation catalog
2. Use Trac's translation system
3. Add language-specific templates

## Maintenance

### Monitoring

Regular maintenance tasks:
1. Check upload logs for errors
2. Monitor disk usage for temp files
3. Review processing statistics
4. Clean up orphaned uploads

### Updates

To update the plugin:
```bash
cd /path/to/learntrac/plugins/pdfuploadmacro
git pull
python setup.py install
# Restart Trac
```

### Backup

Before updates, backup:
1. Plugin configuration in trac.ini
2. Custom modifications
3. Upload history/logs

## Support

For issues or questions:
1. Check Trac logs first
2. Review this documentation
3. Test API connectivity
4. Contact LearnTrac support team

---

*Version 1.0.0 - Compatible with Trac 1.0+ and Python 2.7*