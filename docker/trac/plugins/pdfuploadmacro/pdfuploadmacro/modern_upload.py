# -*- coding: utf-8 -*-
"""
Modern PDF Upload Macro with drag-and-drop support
"""

from trac.core import *
from trac.wiki.macros import WikiMacroBase
from trac.util.html import tag
from trac.config import Option


class ModernPDFUploadMacro(WikiMacroBase):
    """Modern PDF upload interface with drag-and-drop.
    
    Usage:
    {{{
    [[ModernPDFUpload]]
    }}}
    """
    
    api_endpoint = Option('learntrac', 'api_endpoint', 
                         default='http://learning-api:8001/api/trac',
                         doc='API endpoint for the LearnTrac service')
    
    def expand_macro(self, formatter, name, content, args=None):
        """Generate the modern upload interface"""
        
        import hashlib
        import time
        instance_id = hashlib.md5(str(time.time())).hexdigest()[:8]
        
        upload_html = tag.div(
            tag.style("""
                .modern-upload-container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.08);
                    margin: 20px 0;
                }
                
                .upload-zone {
                    border: 3px dashed #e2e8f0;
                    border-radius: 20px;
                    padding: 60px 20px;
                    text-align: center;
                    background: #f8fafc;
                    transition: all 0.3s;
                    cursor: pointer;
                    position: relative;
                }
                
                .upload-zone.drag-over {
                    border-color: #667eea;
                    background: #ebf4ff;
                    transform: scale(1.02);
                }
                
                .upload-zone:hover {
                    border-color: #cbd5e0;
                    background: #f7fafc;
                }
                
                .upload-icon {
                    font-size: 72px;
                    color: #667eea;
                    margin-bottom: 20px;
                }
                
                .upload-text {
                    font-size: 24px;
                    color: #2d3748;
                    margin-bottom: 10px;
                    font-weight: 600;
                }
                
                .upload-subtext {
                    font-size: 16px;
                    color: #718096;
                    margin-bottom: 30px;
                }
                
                .browse-button {
                    display: inline-block;
                    padding: 15px 40px;
                    background: #667eea;
                    color: white;
                    border-radius: 50px;
                    font-weight: 600;
                    transition: all 0.3s;
                }
                
                .browse-button:hover {
                    background: #5a67d8;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                }
                
                .file-input-hidden {
                    display: none;
                }
                
                .metadata-form {
                    display: none;
                    margin-top: 30px;
                }
                
                .form-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 20px;
                }
                
                .form-field {
                    display: flex;
                    flex-direction: column;
                }
                
                .form-field.full-width {
                    grid-column: 1 / -1;
                }
                
                .form-label {
                    font-size: 14px;
                    font-weight: 600;
                    color: #4a5568;
                    margin-bottom: 8px;
                }
                
                .form-input {
                    padding: 12px 16px;
                    border: 2px solid #e2e8f0;
                    border-radius: 10px;
                    font-size: 16px;
                    transition: all 0.3s;
                    outline: none;
                }
                
                .form-input:focus {
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }
                
                .form-select {
                    padding: 12px 16px;
                    border: 2px solid #e2e8f0;
                    border-radius: 10px;
                    font-size: 16px;
                    background: white;
                    cursor: pointer;
                    outline: none;
                }
                
                .selected-file {
                    background: #f0f9ff;
                    border: 2px solid #90cdf4;
                    border-radius: 15px;
                    padding: 20px;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                }
                
                .file-icon {
                    font-size: 48px;
                    color: #3182ce;
                }
                
                .file-info {
                    flex: 1;
                    text-align: left;
                }
                
                .file-name {
                    font-weight: 600;
                    color: #2d3748;
                    font-size: 18px;
                }
                
                .file-size {
                    color: #718096;
                    font-size: 14px;
                }
                
                .remove-file {
                    color: #e53e3e;
                    cursor: pointer;
                    font-size: 24px;
                    transition: all 0.3s;
                }
                
                .remove-file:hover {
                    transform: scale(1.2);
                }
                
                .upload-actions {
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                }
                
                .upload-button {
                    padding: 15px 40px;
                    background: #48bb78;
                    color: white;
                    border: none;
                    border-radius: 50px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                
                .upload-button:hover:not(:disabled) {
                    background: #38a169;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(72, 187, 120, 0.4);
                }
                
                .upload-button:disabled {
                    background: #cbd5e0;
                    cursor: not-allowed;
                }
                
                .cancel-button {
                    padding: 15px 40px;
                    background: #e2e8f0;
                    color: #4a5568;
                    border: none;
                    border-radius: 50px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                
                .cancel-button:hover {
                    background: #cbd5e0;
                }
                
                .progress-container {
                    display: none;
                    margin-top: 30px;
                }
                
                .progress-bar {
                    height: 8px;
                    background: #e2e8f0;
                    border-radius: 10px;
                    overflow: hidden;
                    margin-bottom: 15px;
                }
                
                .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                    width: 0%;
                    transition: width 0.3s;
                }
                
                .progress-text {
                    text-align: center;
                    color: #4a5568;
                    font-size: 14px;
                }
                
                .success-result {
                    background: #f0fdf4;
                    border: 2px solid #86efac;
                    border-radius: 15px;
                    padding: 30px;
                    margin-top: 20px;
                    text-align: center;
                }
                
                .success-icon {
                    font-size: 64px;
                    color: #22c55e;
                    margin-bottom: 15px;
                }
                
                .success-title {
                    font-size: 24px;
                    font-weight: 600;
                    color: #15803d;
                    margin-bottom: 10px;
                }
                
                .success-message {
                    color: #166534;
                    margin-bottom: 20px;
                }
                
                .error-result {
                    background: #fef2f2;
                    border: 2px solid #fca5a5;
                    border-radius: 15px;
                    padding: 30px;
                    margin-top: 20px;
                    text-align: center;
                }
            """),
            tag.div(
                tag.div(
                    tag.input(
                        type="file",
                        id="file-input-%s" % instance_id,
                        accept=".pdf",
                        class_="file-input-hidden"
                    ),
                    tag.div(
                        tag.div("PDF", class_="upload-icon"),
                        tag.div("Drop your PDF here", class_="upload-text"),
                        tag.div("or click to browse", class_="upload-subtext"),
                        tag.div("Browse Files", class_="browse-button"),
                        id="drop-zone-%s" % instance_id,
                        class_="upload-zone"
                    ),
                    tag.div(
                        tag.div(
                            tag.div("PDF", class_="file-icon"),
                            tag.div(
                                tag.div("", class_="file-name", id="file-name-%s" % instance_id),
                                tag.div("", class_="file-size", id="file-size-%s" % instance_id),
                                class_="file-info"
                            ),
                            tag.div("X", class_="remove-file", id="remove-file-%s" % instance_id),
                            class_="selected-file",
                            id="selected-file-%s" % instance_id,
                            style="display: none;"
                        ),
                        tag.div(
                            tag.div(
                                tag.div(
                                    tag.label("Title *", class_="form-label"),
                                    tag.input(
                                        type="text",
                                        id="title-%s" % instance_id,
                                        placeholder="e.g., Introduction to Machine Learning",
                                        class_="form-input",
                                        required=True
                                    ),
                                    class_="form-field full-width"
                                ),
                                tag.div(
                                    tag.label("Subject", class_="form-label"),
                                    tag.select(
                                        tag.option("Computer Science", value="Computer Science"),
                                        tag.option("Mathematics", value="Mathematics"),
                                        tag.option("Physics", value="Physics"),
                                        tag.option("Chemistry", value="Chemistry"),
                                        tag.option("Biology", value="Biology"),
                                        tag.option("Engineering", value="Engineering"),
                                        tag.option("Other", value="Other"),
                                        id="subject-%s" % instance_id,
                                        class_="form-select"
                                    ),
                                    class_="form-field"
                                ),
                                tag.div(
                                    tag.label("Authors", class_="form-label"),
                                    tag.input(
                                        type="text",
                                        id="authors-%s" % instance_id,
                                        placeholder="e.g., John Doe, Jane Smith",
                                        class_="form-input"
                                    ),
                                    class_="form-field"
                                ),
                                class_="form-grid"
                            ),
                            tag.div(
                                tag.button(
                                    "Upload & Process",
                                    type="button",
                                    id="upload-btn-%s" % instance_id,
                                    class_="upload-button"
                                ),
                                tag.button(
                                    "Cancel",
                                    type="button",
                                    id="cancel-btn-%s" % instance_id,
                                    class_="cancel-button"
                                ),
                                class_="upload-actions"
                            ),
                            class_="metadata-form",
                            id="metadata-form-%s" % instance_id
                        ),
                        class_="form-container"
                    ),
                    tag.div(
                        tag.div(class_="progress-bar")(
                            tag.div(class_="progress-fill", id="progress-fill-%s" % instance_id)
                        ),
                        tag.div("Uploading...", class_="progress-text", id="progress-text-%s" % instance_id),
                        class_="progress-container",
                        id="progress-%s" % instance_id
                    ),
                    tag.div(id="result-%s" % instance_id),
                    class_="modern-upload-container"
                ),
                tag.script("""
                    (function() {{
                        const dropZone = document.getElementById('drop-zone-%s');" % instance_id + "
                        const fileInput = document.getElementById('file-input-%s');" % instance_id + "
                        const selectedFile = document.getElementById('selected-file-%s');" % instance_id + "
                        const metadataForm = document.getElementById('metadata-form-%s');" % instance_id + "
                        const uploadBtn = document.getElementById('upload-btn-%s');" % instance_id + "
                        const cancelBtn = document.getElementById('cancel-btn-%s');" % instance_id + "
                        const removeFile = document.getElementById('remove-file-%s');" % instance_id + "
                        const progress = document.getElementById('progress-%s');" % instance_id + "
                        const progressFill = document.getElementById('progress-fill-%s');" % instance_id + "
                        const progressText = document.getElementById('progress-text-%s');" % instance_id + "
                        const result = document.getElementById('result-%s');" % instance_id + "
                        
                        let selectedPDF = null;
                        
                        // Drag and drop handlers
                        dropZone.addEventListener('dragover', (e) => {{
                            e.preventDefault();
                            dropZone.classList.add('drag-over');
                        }});
                        
                        dropZone.addEventListener('dragleave', () => {{
                            dropZone.classList.remove('drag-over');
                        }});
                        
                        dropZone.addEventListener('drop', (e) => {{
                            e.preventDefault();
                            dropZone.classList.remove('drag-over');
                            handleFiles(e.dataTransfer.files);
                        }});
                        
                        dropZone.addEventListener('click', () => {{
                            fileInput.click();
                        }});
                        
                        fileInput.addEventListener('change', (e) => {{
                            handleFiles(e.target.files);
                        }});
                        
                        removeFile.addEventListener('click', () => {{
                            resetUpload();
                        }});
                        
                        cancelBtn.addEventListener('click', () => {{
                            resetUpload();
                        }});
                        
                        uploadBtn.addEventListener('click', () => {{
                            uploadFile();
                        }});
                        
                        function handleFiles(files) {{
                            if (files.length > 0 && files[0].type === 'application/pdf') {{
                                selectedPDF = files[0];
                                showFileInfo();
                            }} else {{
                                alert('Please select a PDF file');
                            }}
                        }}
                        
                        function showFileInfo() {{
                            dropZone.style.display = 'none';
                            selectedFile.style.display = 'flex';
                            metadataForm.style.display = 'block';
                            
                            document.getElementById('file-name-{instance_id}').textContent = selectedPDF.name;
                            document.getElementById('file-size-{instance_id}').textContent = 
                                (selectedPDF.size / 1024 / 1024).toFixed(2) + ' MB';
                        }}
                        
                        function resetUpload() {{
                            selectedPDF = null;
                            fileInput.value = '';
                            dropZone.style.display = 'block';
                            selectedFile.style.display = 'none';
                            metadataForm.style.display = 'none';
                            progress.style.display = 'none';
                            result.innerHTML = '';
                        }}
                        
                        function uploadFile() {{
                            if (!selectedPDF) return;
                            
                            const title = document.getElementById('title-{instance_id}').value;
                            if (!title) {{
                                alert('Please enter a title');
                                return;
                            }}
                            
                            const formData = new FormData();
                            formData.append('file', selectedPDF);
                            formData.append('title', title);
                            formData.append('subject', document.getElementById('subject-{instance_id}').value);
                            formData.append('authors', document.getElementById('authors-{instance_id}').value);
                            
                            // Show progress
                            metadataForm.style.display = 'none';
                            progress.style.display = 'block';
                            uploadBtn.disabled = true;
                            
                            const xhr = new XMLHttpRequest();
                            
                            xhr.upload.onprogress = (e) => {{
                                if (e.lengthComputable) {{
                                    const percent = (e.loaded / e.total) * 100;
                                    progressFill.style.width = percent + '%';
                                    
                                    if (percent >= 100) {{
                                        progressText.textContent = 'Processing PDF...';
                                    }} else {{
                                        progressText.textContent = 'Uploading... ' + Math.round(percent) + '%';
                                    }}
                                }}
                            }};
                            
                            xhr.onload = function() {{
                                uploadBtn.disabled = false;
                                progress.style.display = 'none';
                                
                                if (xhr.status === 200) {{
                                    showSuccess(JSON.parse(xhr.responseText));
                                }} else {{
                                    showError(xhr.responseText);
                                }}
                            }};
                            
                            xhr.onerror = function() {{
                                uploadBtn.disabled = false;
                                progress.style.display = 'none';
                                showError('Network error occurred');
                            }};
                            
                            xhr.open('POST', '{self.api_endpoint}/textbooks/upload');
                            xhr.send(formData);
                        }}
                        
                        function showSuccess(data) {{
                            result.innerHTML = `
                                <div class="success-result">
                                    <div class="success-icon">SUCCESS</div>
                                    <div class="success-title">Upload Successful!</div>
                                    <div class="success-message">
                                        ${{data.title}} has been processed successfully.<br>
                                        Created ${{data.chunks_created}} chunks and extracted ${{data.concepts_extracted}} concepts.
                                    </div>
                                    <button class="browse-button" onclick="location.reload()">Upload Another</button>
                                </div>
                            `;
                        }}
                        
                        function showError(message) {{
                            result.innerHTML = `
                                <div class="error-result">
                                    <div class="success-icon">ERROR</div>
                                    <div class="success-title">Upload Failed</div>
                                    <div class="success-message">${{message}}</div>
                                    <button class="browse-button" onclick="location.reload()">Try Again</button>
                                </div>
                            `;
                        }}
                    }})();
                """)
            )
        )
        
        return upload_html