# -*- coding: utf-8 -*-
"""
TracLearn Learning Manager Component
Implements IRequestHandler and ITicketManipulator for learning management
"""

from __future__ import absolute_import, print_function, unicode_literals

import re
import json
from datetime import datetime

from trac.core import Component, implements
from trac.web.api import IRequestHandler, ITemplateStreamFilter
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_script, add_notice, add_warning
from trac.ticket.api import ITicketManipulator, ITicketChangeListener
from trac.util.datefmt import format_datetime, utc
from trac.util.translation import _
from trac.perm import IPermissionRequestor
from trac.resource import Resource
from genshi.builder import tag
from genshi.filters.transform import Transformer

class LearningManager(Component):
    """Main component for TracLearn learning management features"""
    
    implements(IRequestHandler, ITemplateProvider, ITemplateStreamFilter,
               ITicketManipulator, ITicketChangeListener, IPermissionRequestor)
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        """Define TracLearn permissions"""
        actions = [
            'TRACLEARN_VIEW',        # View learning content
            'TRACLEARN_STUDENT',     # Student permissions
            'TRACLEARN_INSTRUCTOR',  # Instructor permissions
            'TRACLEARN_ADMIN',       # Admin permissions
        ]
        return actions + [('TRACLEARN_ADMIN', actions)]
    
    # IRequestHandler methods
    def match_request(self, req):
        """Match TracLearn URLs"""
        match = re.match(r'/traclearn(?:/(\w+))?(?:/(.*))?$', req.path_info)
        if match:
            req.args['action'] = match.group(1) or 'dashboard'
            req.args['path'] = match.group(2) or ''
            return True
        return False
    
    def process_request(self, req):
        """Process TracLearn requests"""
        req.perm.require('TRACLEARN_VIEW')
        
        action = req.args.get('action', 'dashboard')
        data = {
            'traclearn_version': '0.1.0',
            'user': req.authname,
            'is_instructor': 'TRACLEARN_INSTRUCTOR' in req.perm,
            'is_admin': 'TRACLEARN_ADMIN' in req.perm,
        }
        
        # Route to appropriate handler
        if action == 'dashboard':
            return self._handle_dashboard(req, data)
        elif action == 'courses':
            return self._handle_courses(req, data)
        elif action == 'analytics':
            return self._handle_analytics(req, data)
        elif action == 'api':
            return self._handle_api_proxy(req, data)
        else:
            add_warning(req, _('Unknown TracLearn action: %(action)s', action=action))
            req.redirect(req.href.traclearn())
    
    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        """Return static resource directories"""
        from pkg_resources import resource_filename
        return [('traclearn', resource_filename('traclearn', 'htdocs'))]
    
    def get_templates_dirs(self):
        """Return template directories"""
        from pkg_resources import resource_filename
        return [resource_filename('traclearn', 'templates')]
    
    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        """Add TracLearn elements to Trac pages"""
        if 'ticket' in filename and 'TRACLEARN_VIEW' in req.perm:
            # Add learning fields to ticket pages
            stream = self._add_learning_fields(stream, req, data)
        return stream
    
    # ITicketManipulator methods
    def prepare_ticket(self, req, ticket, fields, actions):
        """Prepare ticket with learning fields"""
        if 'TRACLEARN_VIEW' in req.perm:
            # Add custom learning fields
            fields.append({
                'name': 'learning_course',
                'type': 'select',
                'label': _('Course'),
                'optional': True,
                'options': self._get_course_options(),
            })
            fields.append({
                'name': 'learning_type',
                'type': 'select',
                'label': _('Learning Type'),
                'optional': True,
                'options': ['', 'assignment', 'project', 'quiz', 'discussion', 'resource'],
            })
            fields.append({
                'name': 'learning_points',
                'type': 'text',
                'label': _('Points'),
                'optional': True,
                'format': 'plain',
            })
    
    def validate_ticket(self, req, ticket):
        """Validate learning-related ticket fields"""
        warnings = []
        
        # Validate learning fields if present
        if ticket.get_value('learning_course'):
            if not ticket.get_value('learning_type'):
                warnings.append((_('Learning Type'), 
                               _('Learning type is required when course is selected')))
            
            # Validate points
            points = ticket.get_value('learning_points')
            if points:
                try:
                    points_val = float(points)
                    if points_val < 0:
                        warnings.append((_('Points'), _('Points must be non-negative')))
                except ValueError:
                    warnings.append((_('Points'), _('Points must be a number')))
        
        return warnings
    
    # ITicketChangeListener methods
    def ticket_created(self, ticket):
        """Handle ticket creation for learning activities"""
        if ticket.get_value('learning_course'):
            self._create_learning_activity(ticket)
    
    def ticket_changed(self, ticket, comment, author, old_values):
        """Handle ticket changes for learning progress"""
        if ticket.get_value('learning_course'):
            self._update_learning_progress(ticket, old_values)
    
    def ticket_deleted(self, ticket):
        """Handle ticket deletion"""
        if ticket.get_value('learning_course'):
            self._remove_learning_activity(ticket)
    
    # Private handler methods
    def _handle_dashboard(self, req, data):
        """Handle dashboard view"""
        with self.env.db_query as db:
            # Get user's enrollments
            cursor = db.cursor()
            cursor.execute("""
                SELECT c.id, c.course_code, c.title, e.status, e.grade
                FROM traclearn_courses c
                JOIN traclearn_enrollments e ON c.id = e.course_id
                WHERE e.student_username = %s
                ORDER BY c.start_date DESC
            """, (req.authname,))
            data['enrollments'] = cursor.fetchall()
            
            # Get recent activities
            cursor.execute("""
                SELECT p.progress_type, p.progress_value, p.details, 
                       p.recorded_at, c.course_code
                FROM traclearn_progress p
                JOIN traclearn_enrollments e ON p.enrollment_id = e.id
                JOIN traclearn_courses c ON e.course_id = c.id
                WHERE e.student_username = %s
                ORDER BY p.recorded_at DESC
                LIMIT 10
            """, (req.authname,))
            data['recent_activities'] = cursor.fetchall()
        
        add_stylesheet(req, 'traclearn/css/traclearn.css')
        add_script(req, 'traclearn/js/learning.js')
        return 'learning_dashboard.html', data, None
    
    def _handle_courses(self, req, data):
        """Handle courses view"""
        if req.method == 'POST' and 'TRACLEARN_INSTRUCTOR' in req.perm:
            # Handle course creation/update
            self._save_course(req)
        
        with self.env.db_query as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT id, course_code, title, instructor, start_date, 
                       end_date, max_students, status
                FROM traclearn_courses
                WHERE status = 'active'
                ORDER BY start_date DESC
            """)
            data['courses'] = cursor.fetchall()
        
        add_stylesheet(req, 'traclearn/css/traclearn.css')
        return 'courses_list.html', data, None
    
    def _handle_analytics(self, req, data):
        """Handle analytics view"""
        req.perm.require('TRACLEARN_INSTRUCTOR')
        
        # Get analytics data
        course_id = req.args.get('course_id')
        if course_id:
            data['analytics'] = self._get_course_analytics(course_id)
        
        add_stylesheet(req, 'traclearn/css/traclearn.css')
        add_script(req, 'traclearn/js/analytics.js')
        return 'analytics_dashboard.html', data, None
    
    def _handle_api_proxy(self, req, data):
        """Proxy requests to Python 3.11 API service"""
        from traclearn.web.api_proxy import proxy_request
        return proxy_request(self.env, req)
    
    # Helper methods
    def _get_course_options(self):
        """Get list of active courses for select field"""
        options = ['']
        with self.env.db_query as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT course_code, title 
                FROM traclearn_courses 
                WHERE status = 'active'
                ORDER BY course_code
            """)
            for code, title in cursor:
                options.append('%s - %s' % (code, title))
        return options
    
    def _create_learning_activity(self, ticket):
        """Create learning activity from ticket"""
        course_code = ticket.get_value('learning_course').split(' - ')[0]
        
        with self.env.db_transaction as db:
            cursor = db.cursor()
            # Get course and enrollment IDs
            cursor.execute("""
                SELECT c.id, e.id
                FROM traclearn_courses c
                JOIN traclearn_enrollments e ON c.id = e.course_id
                WHERE c.course_code = %s AND e.student_username = %s
            """, (course_code, ticket['reporter']))
            
            result = cursor.fetchone()
            if result:
                course_id, enrollment_id = result
                # Record activity
                cursor.execute("""
                    INSERT INTO traclearn_progress 
                    (enrollment_id, ticket_id, progress_type, progress_value, details)
                    VALUES (%s, %s, %s, %s, %s)
                """, (enrollment_id, ticket.id, ticket.get_value('learning_type'),
                      0, json.dumps({'title': ticket['summary']})))
    
    def _update_learning_progress(self, ticket, old_values):
        """Update learning progress based on ticket changes"""
        if 'status' in old_values and ticket['status'] == 'closed':
            # Mark activity as completed
            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE traclearn_progress
                    SET progress_value = 100
                    WHERE ticket_id = %s
                """, (ticket.id,))
    
    def _remove_learning_activity(self, ticket):
        """Remove learning activity when ticket is deleted"""
        with self.env.db_transaction as db:
            cursor = db.cursor()
            cursor.execute("""
                DELETE FROM traclearn_progress
                WHERE ticket_id = %s
            """, (ticket.id,))
    
    def _add_learning_fields(self, stream, req, data):
        """Add learning fields to ticket view"""
        if data.get('ticket'):
            ticket = data['ticket']
            course = ticket.get_value('learning_course')
            if course:
                # Add learning info box
                learning_info = tag.div(
                    tag.h3(_('Learning Activity')),
                    tag.dl(
                        tag.dt(_('Course:')), tag.dd(course),
                        tag.dt(_('Type:')), tag.dd(ticket.get_value('learning_type')),
                        tag.dt(_('Points:')), tag.dd(ticket.get_value('learning_points') or '0'),
                    ),
                    class_='traclearn-info'
                )
                
                stream |= Transformer('//div[@id="ticket"]').after(learning_info)
        
        return stream
    
    def _get_course_analytics(self, course_id):
        """Get analytics data for a course"""
        analytics = {}
        with self.env.db_query as db:
            cursor = db.cursor()
            
            # Get enrollment stats
            cursor.execute("""
                SELECT COUNT(*), 
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)
                FROM traclearn_enrollments
                WHERE course_id = %s
            """, (course_id,))
            total, completed = cursor.fetchone()
            analytics['enrollment_stats'] = {
                'total': total,
                'completed': completed,
                'active': total - completed
            }
            
            # Get average progress
            cursor.execute("""
                SELECT AVG(p.progress_value)
                FROM traclearn_progress p
                JOIN traclearn_enrollments e ON p.enrollment_id = e.id
                WHERE e.course_id = %s
            """, (course_id,))
            analytics['avg_progress'] = cursor.fetchone()[0] or 0
        
        return analytics
    
    def _save_course(self, req):
        """Save course from form data"""
        course_data = {
            'course_code': req.args.get('course_code'),
            'title': req.args.get('title'),
            'description': req.args.get('description'),
            'instructor': req.args.get('instructor', req.authname),
            'start_date': req.args.get('start_date'),
            'end_date': req.args.get('end_date'),
            'max_students': int(req.args.get('max_students', 50)),
        }
        
        with self.env.db_transaction as db:
            cursor = db.cursor()
            if req.args.get('course_id'):
                # Update existing
                cursor.execute("""
                    UPDATE traclearn_courses
                    SET title=%s, description=%s, instructor=%s,
                        start_date=%s, end_date=%s, max_students=%s
                    WHERE id=%s
                """, (course_data['title'], course_data['description'],
                      course_data['instructor'], course_data['start_date'],
                      course_data['end_date'], course_data['max_students'],
                      req.args.get('course_id')))
            else:
                # Create new
                cursor.execute("""
                    INSERT INTO traclearn_courses
                    (course_code, title, description, instructor,
                     start_date, end_date, max_students)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, tuple(course_data.values()))
        
        add_notice(req, _('Course saved successfully'))
        req.redirect(req.href.traclearn('courses'))