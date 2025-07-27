# -*- coding: utf-8 -*-
"""
LearnTrac Search Macro - Allows users to search and ask questions about learning content
"""

from trac.core import *
from trac.wiki.macros import WikiMacroBase
from trac.util.html import tag
from trac.config import Option
import json

try:
    # Python 2
    from urllib2 import urlopen, Request, HTTPError
    from urllib import urlencode
except ImportError:
    # Python 3
    from urllib.request import urlopen, Request, HTTPError
    from urllib.parse import urlencode


class LearningSearchMacro(WikiMacroBase):
    """Displays a search interface for learning content queries.
    
    Usage:
    {{{
    [[LearningSearch]]
    }}}
    """
    
    api_endpoint = Option('learntrac', 'api_endpoint', 
                         default='http://learning-api:8001/api/trac',
                         doc='API endpoint for the LearnTrac service')
    
    def expand_macro(self, formatter, name, content, args=None):
        """Generate the search interface HTML"""
        
        # Create search form with modern styling
        search_html = tag.div(
            tag.style("""
                .learning-search-container {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 20px;
                    padding: 40px;
                    margin: 30px 0;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                }
                .search-title {
                    color: white;
                    font-size: 32px;
                    font-weight: bold;
                    margin-bottom: 10px;
                    text-align: center;
                }
                .search-subtitle {
                    color: rgba(255,255,255,0.9);
                    font-size: 18px;
                    margin-bottom: 30px;
                    text-align: center;
                }
                .search-form {
                    display: flex;
                    gap: 15px;
                    max-width: 800px;
                    margin: 0 auto;
                }
                .search-input {
                    flex: 1;
                    padding: 18px 25px;
                    font-size: 16px;
                    border: none;
                    border-radius: 50px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    outline: none;
                    transition: all 0.3s;
                }
                .search-input:focus {
                    box-shadow: 0 5px 20px rgba(0,0,0,0.2);
                    transform: translateY(-2px);
                }
                .search-button {
                    padding: 18px 35px;
                    background: white;
                    color: #667eea;
                    border: none;
                    border-radius: 50px;
                    font-size: 16px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: all 0.3s;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .search-button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 7px 20px rgba(0,0,0,0.2);
                }
                .search-suggestions {
                    margin-top: 20px;
                    text-align: center;
                }
                .suggestion-label {
                    color: rgba(255,255,255,0.8);
                    font-size: 14px;
                    margin-right: 10px;
                }
                .suggestion-chip {
                    display: inline-block;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    margin: 0 5px;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .suggestion-chip:hover {
                    background: rgba(255,255,255,0.3);
                    transform: translateY(-1px);
                }
                .search-results {
                    margin-top: 30px;
                    display: none;
                }
                .result-item {
                    background: white;
                    padding: 20px;
                    margin: 10px 0;
                    border-radius: 10px;
                    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                }
            """),
            tag.div(
                tag.h2("What would you like to learn today?", class_="search-title"),
                tag.p("Search through textbooks, concepts, or ask any question", class_="search-subtitle"),
                tag.form(
                    tag.input(
                        type="text",
                        name="query",
                        placeholder="e.g., 'Explain quantum computing' or 'Find calculus textbooks'",
                        class_="search-input",
                        id="learning-search-input"
                    ),
                    tag.button(
                        "Search",
                        type="submit",
                        class_="search-button",
                        onclick="searchLearningContent(event); return false;"
                    ),
                    class_="search-form"
                ),
                tag.div(
                    tag.span("Try searching for:", class_="suggestion-label"),
                    tag.span("Machine Learning", class_="suggestion-chip", onclick="setSearchQuery('Machine Learning')"),
                    tag.span("Python Programming", class_="suggestion-chip", onclick="setSearchQuery('Python Programming')"),
                    tag.span("Data Structures", class_="suggestion-chip", onclick="setSearchQuery('Data Structures')"),
                    class_="search-suggestions"
                ),
                tag.div(id="search-results", class_="search-results"),
                class_="learning-search-container"
            ),
            tag.script("""
                function setSearchQuery(query) {
                    document.getElementById('learning-search-input').value = query;
                    searchLearningContent(event);
                }
                
                function searchLearningContent(event) {
                    event.preventDefault();
                    const query = document.getElementById('learning-search-input').value;
                    const resultsDiv = document.getElementById('search-results');
                    
                    if (!query.trim()) {
                        return;
                    }
                    
                    resultsDiv.style.display = 'block';
                    resultsDiv.innerHTML = '<div class="result-item">Searching for: <strong>' + query + '</strong><br><em>Search functionality will be connected to the Learning API...</em></div>';
                    
                    // TODO: Make actual API call to search endpoint
                    // fetch('/api/search?q=' + encodeURIComponent(query))
                    //     .then(response => response.json())
                    //     .then(data => displayResults(data));
                }
            """)
        )
        
        return search_html