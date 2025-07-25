# -*- coding: utf-8 -*-
"""
Learning Roadmap Enhancement for Trac
Provides progress tracking and visualization in roadmap views
"""

from trac.core import Component, implements
from trac.web.api import IRequestHandler, ITemplateProvider
from trac.web.chrome import ITemplateStreamFilter, add_stylesheet, add_script
from trac.util import get_reporter_id
from trac.util.html import html
from trac.perm import IPermissionRequestor
from trac.db import get_column_names
from genshi.builder import tag
from genshi.filters import Transformer
import json
import logging
import requests
from datetime import datetime, timedelta
import os

log = logging.getLogger(__name__)

class LearningRoadmapEnhancer(Component):
    """Enhanced roadmap view with learning progress tracking"""
    
    implements(IRequestHandler, ITemplateProvider, ITemplateStreamFilter, IPermissionRequestor)
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['LEARNING_ROADMAP_VIEW']
    
    # IRequestHandler methods
    def match_request(self, req):
        """Match requests for learning roadmap"""
        return req.path_info.startswith('/learning/roadmap')
    
    def process_request(self, req):
        """Process learning roadmap requests"""
        req.perm.require('LEARNING_ROADMAP_VIEW')
        
        # Get user ID from Cognito session
        user_id = req.session.get('cognito_sub')
        if not user_id:
            req.redirect(req.href.login())
            return
        
        # Get optional milestone filter
        milestone_filter = req.args.get('milestone', None)
        
        try:
            # Get learning paths from database
            paths = self._get_user_paths(user_id)
            
            # Get all learning milestones
            milestones = self._get_learning_milestones()
            
            # Calculate progress for each milestone
            milestone_progress = {}
            for milestone in milestones:
                if milestone_filter and milestone['name'] != milestone_filter:
                    continue
                stats = self._calculate_milestone_progress(milestone['name'], user_id)
                milestone_progress[milestone['name']] = {
                    'milestone': milestone,
                    'stats': stats
                }
            
            # Calculate overall progress
            overall_progress = self._calculate_overall_progress(user_id)
            
            # Get cohort comparison data
            cohort_data = self._get_cohort_comparison(user_id)
            
            # Prepare template data
            data = {
                'user_id': user_id,
                'paths': paths,
                'milestones': milestone_progress,
                'overall_progress': overall_progress,
                'cohort_data': cohort_data,
                'selected_milestone': milestone_filter,
                'learning_api_url': os.environ.get('LEARNING_API_URL', 'http://learning-service:8001/api/learntrac'),
                'can_export': req.perm.has_permission('LEARNING_ROADMAP_EXPORT')
            }
            
            add_stylesheet(req, 'learntrac/css/learning-roadmap.css')
            add_script(req, 'learntrac/js/learning-roadmap.js')
            
            return 'learning_roadmap.html', data, None
            
        except Exception as e:
            log.error("Error processing learning roadmap: %s", e, exc_info=True)
            req.redirect(req.href.error("Unable to load learning roadmap"))
    
    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        """Return static resource directories"""
        from pkg_resources import resource_filename
        return [('learntrac', resource_filename(__name__, 'htdocs'))]
    
    def get_templates_dirs(self):
        """Return template directories"""
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
    
    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        """Add learning progress to standard roadmap view"""
        if filename == 'roadmap.html' and req.perm.has_permission('LEARNING_ROADMAP_VIEW'):
            # Add link to learning roadmap
            filter = Transformer('//div[@id="content"]')
            stream = stream | filter.prepend(
                tag.div(
                    tag.a(
                        "View Learning Progress",
                        href=req.href.learning.roadmap(),
                        class_="button"
                    ),
                    class_="learning-roadmap-link"
                )
            )
        return stream
    
    # Progress calculation methods
    def _get_user_paths(self, user_id):
        """Get learning paths for a user"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = """
            SELECT 
                lp.id,
                lp.path_name,
                lp.created_at,
                lpp.status,
                lpp.score,
                lpp.first_accessed,
                lpp.last_accessed,
                lp.metadata
            FROM learning.learning_paths lp
            LEFT JOIN learning.learning_path_progress lpp 
                ON lp.id = lpp.path_id AND lpp.cognito_user_id = %s
            ORDER BY lp.created_at DESC
        """
        
        cursor.execute(query, (user_id,))
        columns = get_column_names(cursor)
        
        paths = []
        for row in cursor:
            path_data = dict(zip(columns, row))
            # Parse metadata JSON
            if path_data['metadata']:
                try:
                    path_data['metadata'] = json.loads(path_data['metadata'])
                except:
                    path_data['metadata'] = {}
            paths.append(path_data)
        
        return paths
    
    def _get_learning_milestones(self):
        """Get all milestones that contain learning concepts"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = """
            SELECT DISTINCT 
                m.name,
                m.due,
                m.description,
                COUNT(t.id) as concept_count
            FROM milestone m
            JOIN ticket t ON t.milestone = m.name AND t.type = 'learning_concept'
            GROUP BY m.name, m.due, m.description
            ORDER BY m.due ASC NULLS LAST, m.name
        """
        
        cursor.execute(query)
        columns = get_column_names(cursor)
        
        milestones = []
        for row in cursor:
            milestone = dict(zip(columns, row))
            milestones.append(milestone)
        
        return milestones
    
    def _calculate_milestone_progress(self, milestone, user_id):
        """Calculate progress statistics for a milestone"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        # Use the view we created
        query = """
            SELECT 
                total_concepts,
                completed,
                in_progress,
                not_started,
                avg_score,
                total_time_minutes,
                last_activity,
                completion_percentage
            FROM learning.milestone_progress_summary
            WHERE milestone_name = %s AND user_id = %s
        """
        
        cursor.execute(query, (milestone, user_id))
        row = cursor.fetchone()
        
        if row:
            columns = get_column_names(cursor)
            stats = dict(zip(columns, row))
            
            # Calculate estimated completion
            stats['estimated_completion'] = self._estimate_completion_date(user_id, milestone)
            
            # Generate graph URL
            stats['graph_url'] = '/learning/graphs/{0}/{1}'.format(milestone, user_id)
            
            return stats
        else:
            # Return default stats if no data
            return {
                'total_concepts': 0,
                'completed': 0,
                'in_progress': 0,
                'not_started': 0,
                'avg_score': 0,
                'total_time_minutes': 0,
                'last_activity': None,
                'completion_percentage': 0,
                'estimated_completion': None,
                'graph_url': None
            }
    
    def _calculate_overall_progress(self, user_id):
        """Calculate overall progress across all milestones"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = """
            SELECT 
                total_paths,
                completed_paths,
                active_paths,
                overall_avg_score,
                total_learning_time_minutes,
                learning_started,
                last_learning_activity,
                active_learning_days,
                overall_completion_percentage
            FROM learning.user_progress_overview
            WHERE user_id = %s
        """
        
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        
        if row:
            columns = get_column_names(cursor)
            return dict(zip(columns, row))
        else:
            return {
                'total_paths': 0,
                'completed_paths': 0,
                'active_paths': 0,
                'overall_avg_score': 0,
                'total_learning_time_minutes': 0,
                'learning_started': None,
                'last_learning_activity': None,
                'active_learning_days': 0,
                'overall_completion_percentage': 0
            }
    
    def _get_cohort_comparison(self, user_id):
        """Get cohort comparison data"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = """
            SELECT 
                completed_count,
                cohort_median_completed,
                avg_score,
                cohort_median_score,
                total_time_minutes,
                cohort_median_time,
                percentile_vs_cohort
            FROM learning.cohort_progress_comparison
            WHERE user_id = %s
        """
        
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        
        if row:
            columns = get_column_names(cursor)
            return dict(zip(columns, row))
        else:
            return None
    
    def _estimate_completion_date(self, user_id, milestone):
        """Estimate completion date for a milestone"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = "SELECT learning.estimate_completion_date(%s, %s)"
        cursor.execute(query, (user_id, milestone))
        result = cursor.fetchone()
        
        return result[0] if result else None
    
    def _get_learning_velocity(self, user_id, weeks=12):
        """Get learning velocity data for the user"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = """
            SELECT 
                week,
                concepts_completed,
                avg_score_this_week,
                time_spent_minutes
            FROM learning.learning_velocity
            WHERE user_id = %s
            AND week >= CURRENT_DATE - INTERVAL '%s weeks'
            ORDER BY week DESC
        """
        
        cursor.execute(query, (user_id, weeks))
        columns = get_column_names(cursor)
        
        velocity_data = []
        for row in cursor:
            velocity_data.append(dict(zip(columns, row)))
        
        return velocity_data
    
    def _calculate_streak(self, user_id):
        """Calculate current learning streak in days"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = """
            WITH daily_activity AS (
                SELECT DISTINCT DATE(last_accessed) as activity_date
                FROM learning.learning_path_progress
                WHERE cognito_user_id = %s
                AND last_accessed >= CURRENT_DATE - INTERVAL '90 days'
                ORDER BY activity_date DESC
            ),
            streaks AS (
                SELECT 
                    activity_date,
                    activity_date - (ROW_NUMBER() OVER (ORDER BY activity_date DESC) - 1) * INTERVAL '1 day' as streak_group
                FROM daily_activity
            )
            SELECT 
                COUNT(*) as streak_length,
                MIN(activity_date) as streak_start,
                MAX(activity_date) as streak_end
            FROM streaks
            WHERE streak_group = (
                SELECT streak_group 
                FROM streaks 
                WHERE activity_date = CURRENT_DATE
                LIMIT 1
            )
            GROUP BY streak_group
        """
        
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'length': row[0],
                'start_date': row[1],
                'end_date': row[2],
                'is_active': row[2] == datetime.now().date()
            }
        else:
            return {
                'length': 0,
                'start_date': None,
                'end_date': None,
                'is_active': False
            }
    
    def _get_score_trends(self, user_id, milestone=None):
        """Get score trends over time"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        if milestone:
            query = """
                SELECT 
                    DATE_TRUNC('week', lpp.last_accessed) as week,
                    AVG(lpp.score) as avg_score,
                    COUNT(*) as attempts
                FROM learning.learning_path_progress lpp
                JOIN learning.learning_paths lp ON lpp.path_id = lp.id
                JOIN ticket t ON (lp.metadata->>'ticket_id')::int = t.id
                WHERE lpp.cognito_user_id = %s
                AND t.milestone = %s
                AND lpp.score IS NOT NULL
                GROUP BY week
                ORDER BY week
            """
            cursor.execute(query, (user_id, milestone))
        else:
            query = """
                SELECT 
                    DATE_TRUNC('week', last_accessed) as week,
                    AVG(score) as avg_score,
                    COUNT(*) as attempts
                FROM learning.learning_path_progress
                WHERE cognito_user_id = %s
                AND score IS NOT NULL
                GROUP BY week
                ORDER BY week
            """
            cursor.execute(query, (user_id,))
        
        columns = get_column_names(cursor)
        trends = []
        for row in cursor:
            trends.append(dict(zip(columns, row)))
        
        return trends
    
    def _get_time_distribution(self, user_id):
        """Get time spent distribution by milestone"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = """
            SELECT 
                t.milestone,
                SUM(EXTRACT(EPOCH FROM (lpp.last_accessed - lpp.first_accessed))/60) as time_spent_minutes,
                COUNT(DISTINCT lpp.path_id) as concept_count
            FROM learning.learning_path_progress lpp
            JOIN learning.learning_paths lp ON lpp.path_id = lp.id
            JOIN ticket t ON (lp.metadata->>'ticket_id')::int = t.id
            WHERE lpp.cognito_user_id = %s
            AND t.milestone IS NOT NULL
            GROUP BY t.milestone
            ORDER BY time_spent_minutes DESC
        """
        
        cursor.execute(query, (user_id,))
        columns = get_column_names(cursor)
        
        distribution = []
        for row in cursor:
            distribution.append(dict(zip(columns, row)))
        
        return distribution
    
    def _get_difficulty_analysis(self, user_id, milestone=None):
        """Analyze which concepts are most difficult based on attempts and scores"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        base_query = """
            SELECT 
                t.id as ticket_id,
                t.summary as concept_name,
                t.milestone,
                AVG(lpp.score) as avg_score,
                COUNT(DISTINCT lpp.id) as attempt_count,
                MIN(lpp.score) as min_score,
                MAX(lpp.score) as max_score,
                STDDEV(lpp.score) as score_variance
            FROM learning.learning_path_progress lpp
            JOIN learning.learning_paths lp ON lpp.path_id = lp.id
            JOIN ticket t ON (lp.metadata->>'ticket_id')::int = t.id
            WHERE lpp.cognito_user_id = %s
            AND lpp.score IS NOT NULL
        """
        
        if milestone:
            query = base_query + " AND t.milestone = %s"
            params = (user_id, milestone)
        else:
            query = base_query
            params = (user_id,)
        
        query += """
            GROUP BY t.id, t.summary, t.milestone
            HAVING COUNT(DISTINCT lpp.id) > 1
            ORDER BY avg_score ASC, attempt_count DESC
            LIMIT 10
        """
        
        cursor.execute(query, params)
        columns = get_column_names(cursor)
        
        difficult_concepts = []
        for row in cursor:
            difficult_concepts.append(dict(zip(columns, row)))
        
        return difficult_concepts
    
    def _calculate_mastery_level(self, score, attempts):
        """Calculate mastery level based on score and attempts"""
        if score >= 90 and attempts <= 2:
            return 'expert'
        elif score >= 80:
            return 'proficient'
        elif score >= 70:
            return 'competent'
        elif score >= 60:
            return 'developing'
        else:
            return 'beginner'
    
    def _get_recommended_next_concepts(self, user_id, limit=5):
        """Get recommended next concepts based on prerequisites and current progress"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        query = """
            WITH completed_concepts AS (
                SELECT DISTINCT (lp.metadata->>'ticket_id')::int as ticket_id
                FROM learning.learning_path_progress lpp
                JOIN learning.learning_paths lp ON lpp.path_id = lp.id
                WHERE lpp.cognito_user_id = %s
                AND lpp.status = 'completed'
            ),
            available_concepts AS (
                SELECT 
                    t.id,
                    t.summary,
                    t.milestone,
                    t.priority,
                    COALESCE(
                        (SELECT COUNT(*) 
                         FROM ticket_custom tc 
                         WHERE tc.ticket = t.id 
                         AND tc.name = 'prerequisites'
                         AND tc.value IN (SELECT ticket_id::text FROM completed_concepts)
                        ), 0
                    ) as met_prerequisites
                FROM ticket t
                WHERE t.type = 'learning_concept'
                AND t.status != 'closed'
                AND t.id NOT IN (SELECT ticket_id FROM completed_concepts)
            )
            SELECT 
                id,
                summary,
                milestone,
                priority,
                met_prerequisites
            FROM available_concepts
            WHERE met_prerequisites >= 0
            ORDER BY met_prerequisites DESC, priority DESC
            LIMIT %s
        """
        
        cursor.execute(query, (user_id, limit))
        columns = get_column_names(cursor)
        
        recommendations = []
        for row in cursor:
            recommendations.append(dict(zip(columns, row)))
        
        return recommendations
    
    def _render_progress_bar(self, stats, bar_type='milestone'):
        """Render a progress bar visualization using Genshi tag builder"""
        total = stats.get('total_concepts', 0) if bar_type == 'milestone' else stats.get('total_paths', 0)
        
        if total == 0:
            return tag.div(
                tag.div(class_='progress-bar empty'),
                tag.span('No data available', class_='progress-text'),
                class_='progress-container'
            )
        
        if bar_type == 'milestone':
            completed = stats.get('completed', 0)
            in_progress = stats.get('in_progress', 0)
            not_started = stats.get('not_started', 0)
            completion_pct = stats.get('completion_percentage', 0)
        else:
            completed = stats.get('completed_paths', 0)
            in_progress = stats.get('active_paths', 0)
            not_started = total - completed - in_progress
            completion_pct = stats.get('overall_completion_percentage', 0)
        
        # Calculate percentages
        completed_pct = (completed / total * 100) if total > 0 else 0
        in_progress_pct = (in_progress / total * 100) if total > 0 else 0
        
        # Build progress bar
        progress_bar = tag.div(
            tag.div(
                style='width: {0}%'.format(completed_pct),
                class_='progress-fill completed',
                title='{0} completed'.format(completed)
            ),
            tag.div(
                style='width: {0}%'.format(in_progress_pct),
                class_='progress-fill in-progress',
                title='{0} in progress'.format(in_progress)
            ),
            class_='progress-bar',
            **{'data-completed': completed, 'data-in-progress': in_progress, 'data-total': total}
        )
        
        # Add progress text
        progress_text = tag.div(
            tag.span('{0}%'.format(int(completion_pct)), class_='percentage'),
            tag.span(' Complete', class_='label'),
            class_='progress-text'
        )
        
        # Add detailed tooltip
        tooltip_text = '{0} completed, {1} in progress, {2} not started'.format(
            completed, in_progress, not_started
        )
        
        return tag.div(
            progress_bar,
            progress_text,
            class_='progress-container',
            title=tooltip_text
        )
    
    def _render_mini_progress_bar(self, percentage, color='green'):
        """Render a mini progress bar for inline use"""
        color_map = {
            'green': '#27ae60',
            'yellow': '#f39c12',
            'red': '#e74c3c',
            'blue': '#3498db'
        }
        
        bar_color = color_map.get(color, color_map['green'])
        
        return tag.span(
            tag.span(
                style='width: {0}%'.format(percentage),
                class_='mini-progress-fill',
                **{'style': 'background-color: {0}; width: {1}%'.format(bar_color, percentage)}
            ),
            class_='mini-progress-bar',
            title='{0}%'.format(int(percentage))
        )
    
    def _render_circular_progress(self, percentage, size='medium'):
        """Render a circular progress indicator"""
        sizes = {
            'small': 40,
            'medium': 80,
            'large': 120
        }
        
        radius = sizes.get(size, sizes['medium']) / 2
        circumference = 2 * 3.14159 * radius
        stroke_dashoffset = circumference - (percentage / 100 * circumference)
        
        svg = tag.svg(
            tag.circle(
                cx=str(radius + 5),
                cy=str(radius + 5),
                r=str(radius),
                fill='none',
                stroke='#e9ecef',
                **{'stroke-width': '8'}
            ),
            tag.circle(
                cx=str(radius + 5),
                cy=str(radius + 5),
                r=str(radius),
                fill='none',
                stroke='#27ae60',
                **{
                    'stroke-width': '8',
                    'stroke-dasharray': str(circumference),
                    'stroke-dashoffset': str(stroke_dashoffset),
                    'stroke-linecap': 'round',
                    'transform': 'rotate(-90 {0} {1})'.format(radius + 5, radius + 5)
                }
            ),
            tag.text(
                '{0}%'.format(int(percentage)),
                x=str(radius + 5),
                y=str(radius + 5),
                **{
                    'text-anchor': 'middle',
                    'dominant-baseline': 'middle',
                    'font-size': str(radius / 2),
                    'font-weight': 'bold',
                    'fill': '#2e5266'
                }
            ),
            width=str(radius * 2 + 10),
            height=str(radius * 2 + 10),
            class_='circular-progress'
        )
        
        return svg
    
    def _render_mastery_badge(self, level, score=None):
        """Render a mastery level badge"""
        badges = {
            'expert': {
                'class': 'badge-expert',
                'icon': '★',
                'label': 'Expert',
                'color': '#9b59b6'
            },
            'proficient': {
                'class': 'badge-proficient',
                'icon': '◆',
                'label': 'Proficient',
                'color': '#3498db'
            },
            'competent': {
                'class': 'badge-competent',
                'icon': '●',
                'label': 'Competent',
                'color': '#27ae60'
            },
            'developing': {
                'class': 'badge-developing',
                'icon': '▲',
                'label': 'Developing',
                'color': '#f39c12'
            },
            'beginner': {
                'class': 'badge-beginner',
                'icon': '■',
                'label': 'Beginner',
                'color': '#95a5a6'
            }
        }
        
        badge_info = badges.get(level, badges['beginner'])
        
        badge = tag.span(
            tag.span(badge_info['icon'], class_='badge-icon'),
            tag.span(badge_info['label'], class_='badge-label'),
            class_='mastery-badge ' + badge_info['class'],
            style='background-color: {0}'.format(badge_info['color'])
        )
        
        if score is not None:
            badge.append(tag.span(' ({0}%)'.format(int(score)), class_='badge-score'))
        
        return badge
    
    def _render_streak_indicator(self, streak_data):
        """Render a learning streak indicator"""
        if not streak_data or not streak_data.get('is_active'):
            return tag.span('No active streak', class_='streak-indicator inactive')
        
        streak_length = streak_data.get('length', 0)
        
        # Determine streak level
        if streak_length >= 30:
            streak_class = 'streak-fire'
            icon = '🔥'
        elif streak_length >= 7:
            streak_class = 'streak-hot'
            icon = '🌟'
        elif streak_length >= 3:
            streak_class = 'streak-warm'
            icon = '✨'
        else:
            streak_class = 'streak-start'
            icon = '⚡'
        
        return tag.span(
            tag.span(icon, class_='streak-icon'),
            tag.span('{0} day streak!'.format(streak_length), class_='streak-text'),
            class_='streak-indicator active ' + streak_class,
            title='Learning streak started {0}'.format(streak_data.get('start_date'))
        )
    
    def _render_time_chart(self, time_distribution):
        """Render a time distribution chart"""
        if not time_distribution:
            return tag.div('No time data available', class_='no-data')
        
        max_time = max(item['time_spent_minutes'] for item in time_distribution)
        
        chart = tag.div(class_='time-distribution-chart')
        
        for item in time_distribution[:10]:  # Top 10 milestones
            percentage = (item['time_spent_minutes'] / max_time * 100) if max_time > 0 else 0
            
            bar = tag.div(
                tag.div(
                    tag.span(item['milestone'], class_='milestone-label'),
                    tag.span(self._format_time(item['time_spent_minutes']), class_='time-label'),
                    class_='chart-labels'
                ),
                tag.div(
                    tag.div(
                        style='width: {0}%'.format(percentage),
                        class_='time-bar'
                    ),
                    class_='time-bar-container'
                ),
                class_='chart-row'
            )
            
            chart.append(bar)
        
        return chart
    
    def _format_time(self, minutes):
        """Format minutes into readable time"""
        if minutes < 60:
            return '{0}m'.format(int(minutes))
        
        hours = int(minutes / 60)
        mins = int(minutes % 60)
        
        if hours < 24:
            return '{0}h {1}m'.format(hours, mins)
        
        days = int(hours / 24)
        hours = int(hours % 24)
        
        return '{0}d {1}h'.format(days, hours)