"""
Simple PDF Upload Macro for testing
"""

from trac.core import Component, implements
from trac.wiki.api import IWikiMacroProvider
from trac.util.html import tag

class SimplePDFUploadMacro(Component):
    """Simple macro for PDF upload testing"""
    
    implements(IWikiMacroProvider)
    
    def get_macros(self):
        """Return list of provided macros"""
        yield 'SimplePDFUpload'
    
    def get_macro_description(self, name):
        """Return macro description"""
        return "Simple PDF upload test"
    
    def expand_macro(self, formatter, name, content):
        """Render simple upload interface"""
        
        # Generate simple HTML with inline JavaScript
        html = tag.div(
            tag.h3("Simple PDF Upload Test"),
            tag.input(type="file", id="simple-file", accept=".pdf"),
            tag.button("Upload", id="simple-upload", onclick="uploadFile()"),
            tag.div(id="simple-status"),
            tag.script("""
            function uploadFile() {
                alert('Upload button clicked!');
                var status = document.getElementById('simple-status');
                var fileInput = document.getElementById('simple-file');
                
                if (!fileInput.files[0]) {
                    status.innerHTML = 'Please select a file';
                    return;
                }
                
                var file = fileInput.files[0];
                status.innerHTML = 'Selected: ' + file.name;
                
                var formData = new FormData();
                formData.append('file', file);
                
                fetch('http://localhost:8001/api/trac/textbooks/upload-dev', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    status.innerHTML = 'Success: ' + JSON.stringify(data);
                })
                .catch(error => {
                    status.innerHTML = 'Error: ' + error;
                });
            }
            """)
        )
        
        return html