"""
Learning Path Wiki Macro for Trac

Provides the [[LearningPath]] macro to display structured learning paths.
"""

from trac.core import Component, implements
from trac.wiki.macros import WikiMacroBase
from trac.wiki.api import IWikiMacroProvider, parse_args
from trac.web.chrome import Chrome, add_stylesheet, add_script
from trac.util.html import html, tag
from trac.util.text import to_unicode
from trac.perm import IPermissionRequestor
import json
import re


class LearningPathMacro(WikiMacroBase):
    """Display a structured learning path.
    
    This macro displays learning paths for educational content with support
    for hierarchical topics, prerequisites, and progress tracking.
    
    == Usage ==
    
    Basic usage:
    {{{
    [[LearningPath(topic=mathematics)]]
    }}}
    
    With options:
    {{{
    [[LearningPath(topic=mathematics, view=tree, show_progress=true)]]
    }}}
    
    == Parameters ==
    
     * `topic` - The main topic of the learning path (required)
     * `view` - Display style: 'tree' (default), 'list', 'graph', or 'timeline'
     * `show_progress` - Show progress indicators (true/false, default: true)
     * `depth` - Maximum depth of subtopics to display (default: 3)
     * `expand` - Auto-expand to specified level (default: 1)
     * `filter` - Filter by difficulty: 'beginner', 'intermediate', 'advanced'
     * `show_prerequisites` - Show prerequisite connections (true/false, default: false)
     * `interactive` - Enable interactive features (true/false, default: true)
     * `style` - Custom CSS class for styling
    
    == Examples ==
    
    Show a mathematics learning path as a tree:
    {{{
    [[LearningPath(topic=mathematics, view=tree)]]
    }}}
    
    Show a programming path with prerequisites:
    {{{
    [[LearningPath(topic=python-programming, show_prerequisites=true, view=graph)]]
    }}}
    
    Filtered view for beginners:
    {{{
    [[LearningPath(topic=web-development, filter=beginner, depth=2)]]
    }}}
    """
    
    implements(IWikiMacroProvider, IPermissionRequestor)
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        """Return permission actions provided by this component."""
        return ['LEARNING_PATH_VIEW', 'LEARNING_PATH_ADMIN']
    
    def expand_macro(self, formatter, name, content):
        """Render the learning path macro."""
        
        # Check Cognito authentication first
        if not self._is_authenticated(formatter.req):
            return self._render_auth_required(formatter.req)
        
        # Parse arguments
        args, kwargs = parse_args(content)
        
        # Extract parameters
        topic = kwargs.get('topic', args[0] if args else None)
        view = kwargs.get('view', 'tree')
        show_progress = kwargs.get('show_progress', 'true').lower() == 'true'
        depth = int(kwargs.get('depth', '3'))
        expand_level = int(kwargs.get('expand', '1'))
        difficulty_filter = kwargs.get('filter', None)
        show_prerequisites = kwargs.get('show_prerequisites', 'false').lower() == 'true'
        interactive = kwargs.get('interactive', 'true').lower() == 'true'
        css_class = kwargs.get('style', '')
        
        # Validate required parameters
        if not topic:
            return tag.div(
                tag.p("Error: 'topic' parameter is required for LearningPath macro"),
                class_='system-message'
            )
        
        # Check permissions
        if 'LEARNING_PATH_VIEW' not in formatter.req.perm:
            return tag.div(
                tag.p("You don't have permission to view learning paths"),
                class_='system-message'
            )
        
        # Add CSS and JavaScript resources
        if interactive:
            add_stylesheet(formatter.req, 'learningpath/css/learningpath.css')
            add_script(formatter.req, 'learningpath/js/learningpath.js')
        
        # Build the learning path display based on view type
        if view == 'tree':
            content = self._render_tree_view(
                formatter, topic, depth, expand_level, 
                show_progress, difficulty_filter, show_prerequisites
            )
        elif view == 'list':
            content = self._render_list_view(
                formatter, topic, depth, 
                show_progress, difficulty_filter
            )
        elif view == 'graph':
            content = self._render_graph_view(
                formatter, topic, depth,
                show_progress, show_prerequisites
            )
        elif view == 'timeline':
            content = self._render_timeline_view(
                formatter, topic, depth,
                show_progress, difficulty_filter
            )
        else:
            return tag.div(
                tag.p(f"Error: Unknown view type '{view}'"),
                class_='system-message'
            )
        
        # Wrap in container div
        container_classes = ['learningpath-container', f'learningpath-{view}']
        if css_class:
            container_classes.append(css_class)
        if interactive:
            container_classes.append('learningpath-interactive')
            
        return tag.div(
            content,
            class_=' '.join(container_classes),
            data_topic=topic,
            data_view=view,
            data_depth=str(depth)
        )
    
    def _render_tree_view(self, formatter, topic, depth, expand_level, 
                         show_progress, difficulty_filter, show_prerequisites):
        """Render tree view of learning path."""
        
        # Get user info for personalization
        user_info = self._get_user_info(formatter.req)
        
        # For now, return a placeholder structure
        # This will be replaced with actual data from the database
        
        tree = tag.div(
            tag.div(
                tag.span(f"Welcome, {user_info['name'] or user_info['username']}! ", 
                        class_='learningpath-welcome'),
                class_='learningpath-user-info'
            ),
            tag.h3(f"Learning Path: {topic.replace('-', ' ').title()}", 
                  class_='learningpath-title'),
            tag.ul(
                tag.li(
                    tag.span("📚 ", class_='learningpath-icon'),
                    tag.a("Introduction to " + topic.replace('-', ' ').title(), 
                         href=formatter.href.wiki(f'LearningPath/{topic}/intro')),
                    tag.span(" (Beginner)", class_='learningpath-level'),
                    self._render_progress_bar(formatter, 75) if show_progress else '',
                    tag.ul(
                        tag.li(
                            tag.span("📖 ", class_='learningpath-icon'),
                            tag.a("Basic Concepts", 
                                 href=formatter.href.wiki(f'LearningPath/{topic}/basics')),
                            self._render_progress_bar(formatter, 100) if show_progress else ''
                        ),
                        tag.li(
                            tag.span("🔨 ", class_='learningpath-icon'),
                            tag.a("First Exercise", 
                                 href=formatter.href.wiki(f'LearningPath/{topic}/exercise1')),
                            self._render_progress_bar(formatter, 50) if show_progress else ''
                        ),
                        class_='learningpath-subtree'
                    ),
                    class_='learningpath-item expanded' if expand_level > 0 else 'learningpath-item'
                ),
                tag.li(
                    tag.span("🎯 ", class_='learningpath-icon'),
                    tag.a("Advanced Topics", 
                         href=formatter.href.wiki(f'LearningPath/{topic}/advanced')),
                    tag.span(" (Advanced)", class_='learningpath-level'),
                    self._render_progress_bar(formatter, 25) if show_progress else '',
                    class_='learningpath-item'
                ),
                class_='learningpath-tree'
            ),
            class_='learningpath-tree-view'
        )
        
        return tree
    
    def _render_list_view(self, formatter, topic, depth, 
                         show_progress, difficulty_filter):
        """Render list view of learning path."""
        
        items = [
            {'title': 'Introduction', 'level': 'Beginner', 'progress': 75},
            {'title': 'Basic Concepts', 'level': 'Beginner', 'progress': 100},
            {'title': 'Intermediate Topics', 'level': 'Intermediate', 'progress': 50},
            {'title': 'Advanced Concepts', 'level': 'Advanced', 'progress': 0},
        ]
        
        # Filter by difficulty if specified
        if difficulty_filter:
            items = [item for item in items 
                    if item['level'].lower() == difficulty_filter.lower()]
        
        list_items = []
        for item in items:
            list_item = tag.div(
                tag.h4(item['title']),
                tag.span(f"Level: {item['level']}", class_='learningpath-meta'),
                self._render_progress_bar(formatter, item['progress']) if show_progress else '',
                class_='learningpath-list-item'
            )
            list_items.append(list_item)
        
        return tag.div(
            tag.h3(f"Learning Path: {topic.replace('-', ' ').title()}"),
            tag.div(*list_items, class_='learningpath-list'),
            class_='learningpath-list-view'
        )
    
    def _render_graph_view(self, formatter, topic, depth,
                          show_progress, show_prerequisites):
        """Render graph/network view of learning path."""
        
        # This would typically render an interactive graph using D3.js or similar
        # For now, return a placeholder
        
        return tag.div(
            tag.h3(f"Learning Path Graph: {topic.replace('-', ' ').title()}"),
            tag.div(
                tag.p("Interactive graph view coming soon..."),
                tag.p("This will show topics as nodes with prerequisite connections."),
                class_='learningpath-graph-placeholder'
            ),
            tag.div(id='learningpath-graph-canvas', class_='learningpath-graph-canvas'),
            class_='learningpath-graph-view'
        )
    
    def _render_timeline_view(self, formatter, topic, depth,
                             show_progress, difficulty_filter):
        """Render timeline view of learning path."""
        
        timeline_items = [
            {'week': 1, 'title': 'Introduction and Setup', 'status': 'completed'},
            {'week': 2, 'title': 'Basic Concepts', 'status': 'completed'},
            {'week': 3, 'title': 'First Project', 'status': 'in-progress'},
            {'week': 4, 'title': 'Intermediate Topics', 'status': 'upcoming'},
            {'week': 5, 'title': 'Advanced Concepts', 'status': 'upcoming'},
        ]
        
        timeline = tag.div(class_='learningpath-timeline')
        
        for item in timeline_items:
            timeline.append(
                tag.div(
                    tag.div(f"Week {item['week']}", class_='timeline-marker'),
                    tag.div(
                        tag.h4(item['title']),
                        tag.span(item['status'].replace('-', ' ').title(), 
                                class_=f'timeline-status status-{item["status"]}'),
                        class_='timeline-content'
                    ),
                    class_='timeline-item'
                )
            )
        
        return tag.div(
            tag.h3(f"Learning Timeline: {topic.replace('-', ' ').title()}"),
            timeline,
            class_='learningpath-timeline-view'
        )
    
    def _render_progress_bar(self, formatter, progress):
        """Render a progress bar."""
        return tag.div(
            tag.div(
                tag.span(f"{progress}%", class_='progress-text'),
                style=f"width: {progress}%",
                class_='progress-fill'
            ),
            class_='learningpath-progress',
            title=f"Progress: {progress}%"
        )
    
    def _is_authenticated(self, req):
        """Check if user is authenticated via Cognito."""
        # Check for Cognito session data
        cognito_username = req.session.get('cognito_username')
        authenticated = req.session.get('authenticated', False)
        
        # Also check standard Trac authname
        has_authname = req.authname and req.authname != 'anonymous'
        
        return authenticated and cognito_username and has_authname
    
    def _render_auth_required(self, req):
        """Render authentication required message."""
        login_url = req.href('/auth/login')
        
        return tag.div(
            tag.div(
                tag.h3("Authentication Required", class_='auth-required-title'),
                tag.p(
                    "You must be logged in to access learning paths. ",
                    tag.a("Click here to login", href=login_url, class_='auth-login-link'),
                    " with your Cognito account.",
                    class_='auth-required-message'
                ),
                tag.div(
                    tag.p("Why authentication is required:"),
                    tag.ul(
                        tag.li("Track your personal learning progress"),
                        tag.li("Save your learning preferences"),
                        tag.li("Access personalized content"),
                        tag.li("Participate in interactive exercises"),
                        class_='auth-benefits-list'
                    ),
                    class_='auth-benefits'
                ),
                class_='auth-required-content'
            ),
            class_='learningpath-auth-required system-message'
        )
    
    def _get_user_info(self, req):
        """Get authenticated user information from session."""
        return {
            'username': req.session.get('cognito_username', 'Unknown'),
            'email': req.session.get('cognito_email', ''),
            'name': req.session.get('cognito_name', ''),
            'groups': req.session.get('cognito_groups', [])
        }