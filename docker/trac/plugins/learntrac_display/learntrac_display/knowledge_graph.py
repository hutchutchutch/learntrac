# -*- coding: utf-8 -*-
"""
Knowledge Graph Generator for LearnTrac

Generates visual knowledge graphs using GraphViz to show learning concepts,
prerequisites, and user progress.
"""

import subprocess
import hashlib
import os
import json
import tempfile
import logging
from datetime import datetime
from trac.core import Component, implements
from trac.web.api import IRequestHandler
from trac.web.chrome import ITemplateProvider, add_stylesheet
from trac.util.html import tag, Markup
from trac.util.datefmt import to_datetime
from genshi.builder import tag as builder_tag

class KnowledgeGraphGenerator(Component):
    """Component for generating visual knowledge graphs of learning paths"""
    
    implements(IRequestHandler, ITemplateProvider)
    
    def __init__(self):
        super(KnowledgeGraphGenerator, self).__init__()
        self.log = logging.getLogger(__name__)
        
        # Create graph directory
        self.graph_dir = os.path.join(self.env.htdocs_dir, 'graphs')
        if not os.path.exists(self.graph_dir):
            try:
                os.makedirs(self.graph_dir)
            except OSError as e:
                self.log.error("Failed to create graph directory: %s", e)
    
    # IRequestHandler methods
    
    def match_request(self, req):
        """Match requests for knowledge graph endpoints"""
        return req.path_info.startswith('/learning/graph')
    
    def process_request(self, req):
        """Process knowledge graph requests"""
        if req.path_info.startswith('/learning/graph/'):
            # Extract milestone from path
            parts = req.path_info.split('/')
            if len(parts) >= 4:
                milestone = parts[3]
                return self._render_graph_page(req, milestone)
        
        # Default: list available milestones
        return self._list_milestones(req)
    
    # ITemplateProvider methods
    
    def get_htdocs_dirs(self):
        """Return static resource directories"""
        return [('learntrac_graphs', self.graph_dir)]
    
    def get_templates_dirs(self):
        """Return template directories"""
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
    
    # Graph generation methods
    
    def generate_graph(self, milestone, user_id):
        """Generate knowledge graph for a milestone and user"""
        try:
            # Generate cache key
            cache_key = hashlib.md5('{0}:{1}'.format(milestone, user_id).encode()).hexdigest()
            png_path = os.path.join(self.graph_dir, '{0}.png'.format(cache_key))
            map_path = os.path.join(self.graph_dir, '{0}.map'.format(cache_key))
            
            # Check cache (regenerate if older than 1 hour)
            if os.path.exists(png_path) and os.path.exists(map_path):
                mtime = os.path.getmtime(png_path)
                if (datetime.now().timestamp() - mtime) < 3600:  # 1 hour cache
                    return self._read_cached_graph(png_path, map_path, cache_key)
            
            # Query data from database
            concepts = self._get_concepts(milestone, user_id)
            if not concepts:
                return None, None, None
            
            prerequisites = self._get_prerequisites([c['id'] for c in concepts])
            
            # Build DOT file
            dot_content = self._build_dot(concepts, prerequisites, milestone)
            
            # Generate with GraphViz
            with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as dot_file:
                dot_file.write(dot_content)
                dot_file_path = dot_file.name
            
            try:
                # Generate PNG
                result = subprocess.run([
                    'dot', '-Tpng', dot_file_path, '-o', png_path
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    self.log.error("GraphViz PNG generation failed: %s", result.stderr)
                    return None, None, None
                
                # Generate clickable map
                result = subprocess.run([
                    'dot', '-Tcmapx', dot_file_path, '-o', map_path
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    self.log.error("GraphViz map generation failed: %s", result.stderr)
                    # Continue even if map fails
                
            finally:
                # Clean up temp file
                if os.path.exists(dot_file_path):
                    os.unlink(dot_file_path)
            
            return self._read_cached_graph(png_path, map_path, cache_key)
            
        except subprocess.TimeoutExpired:
            self.log.error("GraphViz generation timed out")
            return None, None, None
        except Exception as e:
            self.log.error("Error generating graph: %s", e)
            return None, None, None
    
    def _build_dot(self, concepts, prerequisites, milestone):
        """Build DOT file content"""
        dot = ['digraph LearningPath {']
        dot.append('  rankdir=TB;')
        dot.append('  node [shape=box, style=filled, fontname="Arial"];')
        dot.append('  edge [color="#666666"];')
        dot.append('  ')
        dot.append('  // Title')
        dot.append('  graph [label="Learning Path: {0}", fontsize=16, fontname="Arial Bold"];'.format(
            milestone.replace('"', '\\"')
        ))
        dot.append('  ')
        
        # Group nodes by status for better layout
        status_groups = {
            'completed': [],
            'in_progress': [],
            'not_started': []
        }
        
        # Add nodes with colors based on status
        for concept in concepts:
            status = concept.get('status', 'not_started')
            if status not in status_groups:
                status = 'not_started'
            status_groups[status].append(concept)
            
            color = self._get_node_color(status)
            label = self._format_node_label(concept)
            
            # Escape special characters
            node_id = str(concept['id'])
            dot.append('  "{0}" [label="{1}", fillcolor="{2}", URL="/ticket/{3}", target="_top"];'.format(
                node_id, label, color, concept['id']
            ))
        
        # Add edges for prerequisites
        dot.append('  ')
        dot.append('  // Prerequisites')
        for prereq in prerequisites:
            dot.append('  "{0}" -> "{1}";'.format(
                prereq['prerequisite_id'], prereq['concept_id']
            ))
        
        # Add invisible ranks to group nodes by status
        if status_groups['completed']:
            dot.append('  ')
            dot.append('  // Completed concepts rank')
            dot.append('  { rank=same; ' + ' '.join('"{0}";'.format(c['id']) for c in status_groups['completed']) + ' }')
        
        dot.append('}')
        return '\n'.join(dot)
    
    def _get_node_color(self, status):
        """Get color for node based on status"""
        # Map learning_path_progress status values
        colors = {
            'completed': '#90EE90',     # Light green
            'in_progress': '#FFB84D',   # Orange
            'not_started': '#D3D3D3'    # Light gray
        }
        return colors.get(status, '#D3D3D3')
    
    def _format_node_label(self, concept):
        """Format node label with line breaks for readability"""
        summary = concept.get('summary', 'Concept {0}'.format(concept['id']))
        # Escape quotes
        summary = summary.replace('"', '\\"')
        
        # Add score if available
        score = concept.get('score')
        if score is not None:
            summary += '\\n(Score: {0:.0%})'.format(score)
        
        # Wrap long text
        words = summary.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            if len(' '.join(current_line)) > 30:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\\n'.join(lines)
    
    def _get_concepts(self, milestone, user_id):
        """Get learning concepts for a milestone with user progress"""
        with self.env.db_query as db:
            cursor = db.cursor()
            
            # Query concepts with progress
            # Using learning_path_progress table for progress tracking
            cursor.execute("""
                SELECT t.id, t.summary, 
                       COALESCE(p.status, 'not_started') as status,
                       COALESCE(p.progress, 0) as score,
                       t.description
                FROM ticket t
                LEFT JOIN learning_path_progress p 
                    ON CAST(t.id AS text) = p.path_id AND p.username = %s
                WHERE t.type = 'learning_concept' 
                    AND t.milestone = %s
                    AND t.status != 'closed'
                ORDER BY t.id
            """, (user_id, milestone))
            
            concepts = []
            for row in cursor:
                concepts.append({
                    'id': row[0],
                    'summary': row[1],
                    'status': row[2],
                    'score': row[3] / 100.0 if row[3] else None,  # Convert to 0-1 range
                    'description': row[4]
                })
            
            return concepts
    
    def _get_prerequisites(self, concept_ids):
        """Get prerequisite relationships for concepts"""
        if not concept_ids:
            return []
        
        with self.env.db_query as db:
            cursor = db.cursor()
            
            # Build query with proper parameter substitution
            # Using learning_path_prerequisites table
            placeholders = ','.join(['%s'] * len(concept_ids))
            cursor.execute("""
                SELECT path_id, prerequisite_id
                FROM learning_path_prerequisites
                WHERE path_id IN ({0})
                ORDER BY path_id, prerequisite_id
            """.format(placeholders), concept_ids)
            
            prerequisites = []
            for row in cursor:
                prerequisites.append({
                    'concept_id': row[0],
                    'prerequisite_id': row[1]
                })
            
            return prerequisites
    
    def _read_cached_graph(self, png_path, map_path, cache_key):
        """Read cached graph files"""
        try:
            # Read map file if it exists
            map_content = None
            if os.path.exists(map_path):
                with open(map_path, 'r') as f:
                    map_content = f.read()
            
            # Return paths and map content
            return '/chrome/learntrac_graphs/{0}.png'.format(cache_key), map_content, cache_key
            
        except Exception as e:
            self.log.error("Error reading cached graph: %s", e)
            return None, None, None
    
    def _render_graph_page(self, req, milestone):
        """Render page with knowledge graph"""
        user_id = req.authname
        
        # Generate graph
        png_url, map_content, cache_key = self.generate_graph(milestone, user_id)
        
        if not png_url:
            req.send_error(500, "Failed to generate knowledge graph")
            return
        
        # Get statistics
        stats = self._get_milestone_statistics(milestone, user_id)
        
        # Build page content
        content = tag.div(
            tag.h1('Knowledge Graph: {0}'.format(milestone)),
            self._render_legend(),
            self._render_statistics(stats),
            tag.div(
                tag.img(src=png_url, usemap='#knowledge_map', alt='Knowledge Graph'),
                Markup(map_content) if map_content else '',
                class_='knowledge-graph-container'
            ),
            class_='knowledge-graph-page'
        )
        
        # Add CSS
        add_stylesheet(req, 'learntrac_display/css/knowledge-graph.css')
        
        data = {
            'content': content,
            'title': 'Knowledge Graph: {0}'.format(milestone)
        }
        
        return 'knowledge_graph.html', data, None
    
    def _render_legend(self):
        """Render color legend"""
        return tag.div(
            tag.h3('Legend'),
            tag.ul(
                tag.li(tag.span(style='background-color: #90EE90; padding: 2px 8px;'), ' Completed'),
                tag.li(tag.span(style='background-color: #FFB84D; padding: 2px 8px;'), ' In Progress'),
                tag.li(tag.span(style='background-color: #D3D3D3; padding: 2px 8px;'), ' Not Started')
            ),
            class_='graph-legend'
        )
    
    def _render_statistics(self, stats):
        """Render milestone statistics"""
        total = stats['total']
        if total == 0:
            percentage = 0
        else:
            percentage = (stats['mastered'] / total) * 100
        
        return tag.div(
            tag.h3('Progress'),
            tag.p(
                'Mastered: {0}/{1} ({2:.0f}%)'.format(stats['mastered'], total, percentage),
                tag.br(),
                'Completed: {0}'.format(stats['completed']),
                tag.br(),
                'In Progress: {0}'.format(stats['in_progress']),
                tag.br(),
                'Not Started: {0}'.format(stats['not_started'])
            ),
            class_='graph-statistics'
        )
    
    def _get_milestone_statistics(self, milestone, user_id):
        """Get progress statistics for a milestone"""
        with self.env.db_query as db:
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT t.id) as total,
                    COUNT(DISTINCT CASE WHEN p.status = 'completed' AND p.progress >= 80 THEN t.id END) as mastered,
                    COUNT(DISTINCT CASE WHEN p.status = 'completed' THEN t.id END) as completed,
                    COUNT(DISTINCT CASE WHEN p.status = 'in_progress' THEN t.id END) as in_progress
                FROM ticket t
                LEFT JOIN learning_path_progress p 
                    ON CAST(t.id AS text) = p.path_id AND p.username = %s
                WHERE t.type = 'learning_concept' 
                    AND t.milestone = %s
                    AND t.status != 'closed'
            """, (user_id, milestone))
            
            row = cursor.fetchone()
            if row:
                total, mastered, completed, in_progress = row
                return {
                    'total': total,
                    'mastered': mastered or 0,
                    'completed': completed or 0,
                    'in_progress': in_progress or 0,
                    'not_started': total - (mastered or 0) - (completed or 0) - (in_progress or 0)
                }
            
            return {'total': 0, 'mastered': 0, 'completed': 0, 'in_progress': 0, 'not_started': 0}
    
    def _list_milestones(self, req):
        """List available milestones with learning concepts"""
        with self.env.db_query as db:
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT milestone, COUNT(*) as concept_count
                FROM ticket
                WHERE type = 'learning_concept'
                    AND status != 'closed'
                    AND milestone IS NOT NULL
                    AND milestone != ''
                GROUP BY milestone
                ORDER BY milestone
            """)
            
            milestones = []
            for row in cursor:
                milestones.append({
                    'name': row[0],
                    'count': row[1],
                    'url': req.href.learning('graph', row[0])
                })
        
        content = tag.div(
            tag.h1('Learning Path Milestones'),
            tag.ul(
                [tag.li(
                    tag.a(m['name'], href=m['url']),
                    ' ({0} concepts)'.format(m['count'])
                ) for m in milestones]
            ) if milestones else tag.p('No learning milestones found.'),
            class_='milestone-list'
        )
        
        data = {
            'content': content,
            'title': 'Learning Path Milestones'
        }
        
        return 'milestone_list.html', data, None