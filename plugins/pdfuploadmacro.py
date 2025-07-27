"""
PDF Upload Macro for LearnTrac
Provides interface for uploading PDFs to the learning system
"""

from trac.core import Component, implements
from trac.wiki.api import IWikiMacroProvider
from trac.web.chrome import add_script, add_stylesheet
from trac.util.html import tag
from trac.config import Option
import json

class PDFUploadMacro(Component):
    """Macro for PDF upload interface in wiki pages"""
    
    implements(IWikiMacroProvider)
    
    # Configuration
    api_endpoint = Option('learntrac', 'api_endpoint',
                         default='http://learning-api:8001/api/trac',
                         doc="""API endpoint for the LearnTrac service""")
    
    api_gateway_url = Option('learntrac', 'api_gateway_url',
                           default='https://j8rhfat0h4.execute-api.us-east-2.amazonaws.com/dev',
                           doc="""AWS API Gateway URL for external access""")
    
    # IWikiMacroProvider methods
    def get_macros(self):
        """Return list of provided macros"""
        yield 'PDFUpload'
        yield 'LearnTrac'
    
    def get_macro_description(self, name):
        """Return macro description"""
        if name == 'PDFUpload':
            return "Display PDF upload interface for LearnTrac"
        elif name == 'LearnTrac':
            return "Display LearnTrac interface with authentication"
        return None
    
    def expand_macro(self, formatter, name, content):
        """Render the PDF upload interface"""
        req = formatter.req
        
        # For development, allow anonymous access
        # In production, uncomment the authentication check below
        # if not req.authname or req.authname == 'anonymous':
        #     return tag.div(
        #         tag.p("Please ", tag.a("login", href=req.href.login()), " to access LearnTrac features."),
        #         class_="system-message"
        #     )
        
        # Get user data from session
        user_data = {}
        auth_data = req.session.get('auth_data')
        if auth_data:
            try:
                user_data = json.loads(auth_data)
            except:
                pass
        
        # Generate upload interface
        upload_id = 'pdf-upload-' + str(id(req))
        
        # Get username for display
        display_name = user_data.get('name', req.authname) if req.authname != 'anonymous' else 'Guest User'
        
        # Create the upload interface
        interface = tag.div(
            tag.h3("LearnTrac - AI-Powered Learning"),
            tag.p("Welcome, ", tag.strong(display_name), "!"),
            tag.div(
                tag.h4("Upload PDF for Learning"),
                tag.div(
                    tag.input(type="file", id=upload_id + "-file", accept=".pdf",
                             style="margin-bottom: 10px;"),
                    tag.br(),
                    tag.button("Upload PDF", id=upload_id + "-button", 
                              class_="trac-button",
                              style="margin-right: 10px;"),
                    tag.span(id=upload_id + "-status", style="margin-left: 10px;"),
                    id=upload_id + "-container",
                    style="padding: 20px; border: 1px solid #ddd; border-radius: 5px; background: #f9f9f9;"
                ),
                tag.div(id=upload_id + "-results", style="margin-top: 20px;"),
                tag.script("""
                //<![CDATA[
                window.addEventListener('DOMContentLoaded', function() {
                    console.log('PDFUpload: Page loaded, initializing upload interface');
                    
                    var fileInput = document.getElementById('%(id)s-file');
                    var uploadButton = document.getElementById('%(id)s-button');
                    var statusSpan = document.getElementById('%(id)s-status');
                    var resultsDiv = document.getElementById('%(id)s-results');
                    
                    console.log('PDFUpload: Elements found:', {
                        fileInput: !!fileInput,
                        uploadButton: !!uploadButton,
                        statusSpan: !!statusSpan,
                        resultsDiv: !!resultsDiv
                    });
                    
                    if (!uploadButton) {
                        console.error('PDFUpload: Upload button not found!');
                        return;
                    }
                    
                    // Add immediate feedback
                    uploadButton.onclick = function(e) {
                        e.preventDefault();
                        console.log('PDFUpload: Upload button clicked');
                        
                        var file = fileInput.files[0];
                        console.log('PDFUpload: Selected file:', file ? file.name : 'none');
                        
                        if (!file) {
                            statusSpan.textContent = 'Please select a PDF file';
                            statusSpan.style.color = 'red';
                            console.log('PDFUpload: No file selected');
                            return;
                        }
                        
                        if (!file.name.toLowerCase().endsWith('.pdf')) {
                            statusSpan.textContent = 'Please select a PDF file';
                            statusSpan.style.color = 'red';
                            console.log('PDFUpload: File is not a PDF:', file.name);
                            return;
                        }
                        
                        console.log('PDFUpload: Starting upload for:', file.name, 'Size:', file.size, 'bytes');
                        
                        // Create form data
                        var formData = new FormData();
                        formData.append('file', file);
                        
                        // Update status
                        statusSpan.textContent = 'Uploading...';
                        statusSpan.style.color = 'blue';
                        uploadButton.disabled = true;
                        
                        // Get session token from cookie
                        var authToken = '';
                        var cookies = document.cookie.split(';');
                        for (var i = 0; i < cookies.length; i++) {
                            var cookie = cookies[i].trim();
                            if (cookie.startsWith('trac_auth=')) {
                                authToken = cookie.substring(10);
                                break;
                            }
                        }
                        
                        // For now, use localhost directly (browser can access both containers on localhost)
                        var uploadUrl = 'http://localhost:8001/api/trac/textbooks/upload-dev';
                        console.log('PDFUpload: Upload URL:', uploadUrl);
                        console.log('PDFUpload: Auth token:', authToken ? 'Present (' + authToken.substring(0, 8) + '...)' : 'Missing');
                        console.log('PDFUpload: Note - using direct localhost access for development');
                        
                        // Add timeout and better error handling
                        var controller = new AbortController();
                        var timeoutId = setTimeout(function() {
                            controller.abort();
                        }, 30000); // 30 second timeout
                        
                        fetch(uploadUrl, {
                            method: 'POST',
                            headers: {
                                'X-Trac-Session': authToken || 'anonymous'
                            },
                            body: formData,
                            signal: controller.signal
                        })
                        .then(function(response) {
                            clearTimeout(timeoutId);
                            console.log('PDFUpload: Response received:', response.status, response.statusText);
                            
                            if (!response.ok) {
                                return response.text().then(function(text) {
                                    console.error('PDFUpload: Error response:', text);
                                    try {
                                        var data = JSON.parse(text);
                                        throw new Error(data.detail || 'Upload failed with status ' + response.status);
                                    } catch (e) {
                                        throw new Error('Upload failed: ' + text);
                                    }
                                });
                            }
                            return response.json();
                        })
                        .then(function(data) {
                            console.log('PDFUpload: Upload successful:', data);
                            statusSpan.textContent = 'Upload successful!';
                            statusSpan.style.color = 'green';
                            
                            // Display results
                            resultsDiv.innerHTML = '<div style="background: #e8f5e9; padding: 15px; border-radius: 5px;">' +
                                '<h4>Upload Complete</h4>' +
                                '<p><strong>Textbook ID:</strong> ' + data.textbook_id + '</p>' +
                                '<p><strong>Title:</strong> ' + (data.title || file.name) + '</p>' +
                                '<p><strong>Pages:</strong> ' + (data.pages || 'Processing...') + '</p>' +
                                '<p><strong>Chunks Created:</strong> ' + (data.chunks_created || 'Processing...') + '</p>' +
                                '<p>The PDF has been uploaded and is being processed for AI-powered learning.</p>' +
                                '</div>';
                            
                            // Reset form
                            fileInput.value = '';
                            uploadButton.disabled = false;
                        })
                        .catch(function(error) {
                            clearTimeout(timeoutId);
                            console.error('PDFUpload: Upload error:', error);
                            
                            var errorMessage = error.message;
                            if (error.name === 'AbortError') {
                                errorMessage = 'Upload timed out after 30 seconds';
                            }
                            
                            statusSpan.textContent = 'Upload failed: ' + errorMessage;
                            statusSpan.style.color = 'red';
                            uploadButton.disabled = false;
                            
                            // Show error details
                            resultsDiv.innerHTML = '<div style="background: #ffebee; padding: 15px; border-radius: 5px;">' +
                                '<h4>Upload Error</h4>' +
                                '<p>' + errorMessage + '</p>' +
                                '<p>Please check the browser console for more details.</p>' +
                                '</div>';
                        });
                    };
                    
                    // Also add file input change handler for feedback
                    fileInput.onchange = function() {
                        var file = this.files[0];
                        if (file) {
                            console.log('PDFUpload: File selected:', file.name, 'Size:', file.size, 'Type:', file.type);
                            statusSpan.textContent = 'File selected: ' + file.name;
                            statusSpan.style.color = 'blue';
                        }
                    };
                    
                    console.log('PDFUpload: Setup complete');
                });
                //]]>
                """ % {'id': upload_id, 'api_gateway_url': self.api_gateway_url}),
                class_="learntrac-interface"
            ),
            tag.div(
                tag.h4("Available Features"),
                tag.ul(
                    tag.li("Upload PDF textbooks for AI processing"),
                    tag.li("Ask questions about uploaded content"),
                    tag.li("Get personalized learning recommendations"),
                    tag.li("Track your learning progress")
                ),
                style="margin-top: 30px; background: #e3f2fd; padding: 15px; border-radius: 5px;"
            ),
            class_="learntrac-container",
            style="padding: 20px;"
        )
        
        return interface