"""
Textbook List Wiki Macro for Trac

Displays available textbooks from Neo4j as cards.
Compatible with Python 2.7 Trac environment.

Usage in wiki:
    [[TextbookList]]
    
or with parameters:
    [[TextbookList(subject=Computer Science,limit=10)]]
"""

from trac.core import Component, implements
from trac.wiki.api import IWikiMacroProvider
from trac.wiki.macros import WikiMacroBase
from trac.util.html import tag, Markup
from trac.util.text import to_unicode
import json
try:
    # Python 2
    import urllib2
    import urllib
    quote = urllib.quote
except ImportError:
    # Python 3
    import urllib.parse
    quote = urllib.parse.quote

class TextbookListMacro(WikiMacroBase):
    """
    Displays available textbooks as cards from the LearnTrac system.
    
    This macro fetches textbooks stored in Neo4j and displays them
    as attractive cards with metadata and action links.
    
    Examples:
    {{{
    [[TextbookList]]
    }}}
    
    {{{
    [[TextbookList(subject=Mathematics,limit=10)]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        """Render the textbook list"""
        
        # Parse arguments
        args = {}
        if content:
            for arg in content.split(','):
                if '=' in arg:
                    key, value = arg.split('=', 1)
                    args[key.strip()] = value.strip()
        
        # Get configuration
        subject = args.get('subject', None)
        limit = int(args.get('limit', '20'))
        api_endpoint = self.env.config.get('learntrac', 'api_endpoint', 
                                         'http://localhost:8000/api/trac')
        
        # JavaScript for fetching and displaying textbooks
        script = """
        (function() {
            var loading = document.getElementById('textbook-loading');
            var grid = document.getElementById('textbook-grid');
            var errorDiv = document.getElementById('textbook-error');
            
            // Build query parameters
            var params = [];
            %(subject_param)s
            params.push('limit=%(limit)d');
            
            var queryString = params.length > 0 ? '?' + params.join('&') : '';
            
            // Fetch textbooks
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '%(api_endpoint)s/textbooks' + queryString);
            
            xhr.onload = function() {
                loading.style.display = 'none';
                
                if (xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        displayTextbooks(data.textbooks || data);
                    } catch (e) {
                        showError('Failed to parse textbook data');
                    }
                } else {
                    showError('Failed to load textbooks: ' + xhr.statusText);
                }
            };
            
            xhr.onerror = function() {
                loading.style.display = 'none';
                showError('Network error while loading textbooks');
            };
            
            xhr.send();
            
            function displayTextbooks(textbooks) {
                if (!textbooks || textbooks.length === 0) {
                    grid.innerHTML = '<p class="no-textbooks">No textbooks available.</p>';
                    grid.style.display = 'block';
                    return;
                }
                
                grid.style.display = 'grid';
                
                textbooks.forEach(function(textbook) {
                    var card = createTextbookCard(textbook);
                    grid.appendChild(card);
                });
            }
            
            function createTextbookCard(textbook) {
                var card = document.createElement('div');
                card.className = 'textbook-card';
                
                // Card header with subject
                var header = document.createElement('div');
                header.className = 'textbook-header';
                header.innerHTML = '<span class="textbook-subject">' + 
                    (textbook.subject || 'General') + '</span>';
                card.appendChild(header);
                
                // Title
                var title = document.createElement('h3');
                title.className = 'textbook-title';
                title.textContent = textbook.title || 'Untitled';
                card.appendChild(title);
                
                // Authors
                if (textbook.authors && textbook.authors.length > 0) {
                    var authors = document.createElement('p');
                    authors.className = 'textbook-authors';
                    authors.textContent = 'By ' + textbook.authors.join(', ');
                    card.appendChild(authors);
                }
                
                // Metadata
                var meta = document.createElement('div');
                meta.className = 'textbook-meta';
                
                if (textbook.pages_processed) {
                    meta.innerHTML += '<span class="meta-item">Pages: ' + 
                        textbook.pages_processed + ' pages</span>';
                }
                
                if (textbook.chunks_created) {
                    meta.innerHTML += '<span class="meta-item">Chunks: ' + 
                        textbook.chunks_created + '</span>';
                }
                
                if (textbook.created_at) {
                    var date = new Date(textbook.created_at);
                    meta.innerHTML += '<span class="meta-item">Added: ' + 
                        date.toLocaleDateString() + '</span>';
                }
                
                card.appendChild(meta);
                
                // Action buttons
                var actions = document.createElement('div');
                actions.className = 'textbook-actions';
                
                var searchBtn = document.createElement('a');
                searchBtn.href = '/wiki/LearningSearch?textbook=' + textbook.textbook_id;
                searchBtn.className = 'textbook-btn search-btn';
                searchBtn.textContent = 'Search';
                actions.appendChild(searchBtn);
                
                var exploreBtn = document.createElement('a');
                exploreBtn.href = '/wiki/ConceptExplorer?textbook=' + textbook.textbook_id;
                exploreBtn.className = 'textbook-btn explore-btn';
                exploreBtn.textContent = 'Explore';
                actions.appendChild(exploreBtn);
                
                var pathsBtn = document.createElement('a');
                pathsBtn.href = '/wiki/LearningPaths?textbook=' + textbook.textbook_id;
                pathsBtn.className = 'textbook-btn paths-btn';
                pathsBtn.textContent = 'Learning Paths';
                actions.appendChild(pathsBtn);
                
                card.appendChild(actions);
                
                return card;
            }
            
            function showError(message) {
                errorDiv.textContent = 'Error: ' + message;
                errorDiv.style.display = 'block';
            }
        })();
        """ % {
            'api_endpoint': api_endpoint,
            'limit': limit,
            'subject_param': 'params.push("subject=%s");' % quote(subject) if subject else ''
        }
        
        # CSS styling
        style = """
        <style>
        .textbook-list-container {
            margin: 20px 0;
        }
        
        .textbook-list-container h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }
        
        .textbook-loading {
            text-align: center;
            color: #666;
            padding: 40px;
            font-style: italic;
        }
        
        .textbook-error {
            background-color: #f2dede;
            border: 1px solid #ebccd1;
            color: #a94442;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
        
        .textbook-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .no-textbooks {
            text-align: center;
            color: #666;
            font-style: italic;
            grid-column: 1 / -1;
            padding: 40px;
        }
        
        .textbook-card {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .textbook-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-color: #3498db;
        }
        
        .textbook-header {
            margin-bottom: 10px;
        }
        
        .textbook-subject {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .textbook-title {
            color: #2c3e50;
            margin: 10px 0;
            font-size: 1.2em;
            line-height: 1.4;
        }
        
        .textbook-authors {
            color: #666;
            font-size: 0.9em;
            margin: 10px 0;
            font-style: italic;
        }
        
        .textbook-meta {
            margin: 15px 0;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        
        .meta-item {
            display: inline-block;
            color: #666;
            font-size: 0.85em;
            margin-right: 15px;
        }
        
        .textbook-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        
        .textbook-btn {
            flex: 1;
            text-align: center;
            padding: 8px 12px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 0.9em;
            transition: all 0.2s ease;
            border: 1px solid;
        }
        
        .search-btn {
            background: #3498db;
            color: white;
            border-color: #3498db;
        }
        
        .search-btn:hover {
            background: #2980b9;
            border-color: #2980b9;
        }
        
        .explore-btn {
            background: #27ae60;
            color: white;
            border-color: #27ae60;
        }
        
        .explore-btn:hover {
            background: #229954;
            border-color: #229954;
        }
        
        .paths-btn {
            background: #e74c3c;
            color: white;
            border-color: #e74c3c;
        }
        
        .paths-btn:hover {
            background: #c0392b;
            border-color: #c0392b;
        }
        
        @media (max-width: 768px) {
            .textbook-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """
        
        # Build the complete HTML using tag
        return tag.div(
            tag.style(Markup(style)),
            tag.div(
                tag.h2('Available Textbooks'),
                tag.div('Loading textbooks...', class_='textbook-loading', id='textbook-loading'),
                tag.div(class_='textbook-grid', id='textbook-grid', style='display:none;'),
                tag.div(class_='textbook-error', id='textbook-error', style='display:none;'),
                class_='textbook-list-container'
            ),
            tag.script(Markup(script), type='text/javascript')
        )