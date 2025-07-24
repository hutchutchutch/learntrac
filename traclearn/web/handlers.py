# -*- coding: utf-8 -*-
"""
TracLearn Web Request Handlers
Additional handlers for TracLearn-specific functionality
"""

from __future__ import absolute_import, print_function, unicode_literals

import json
from datetime import datetime

from trac.core import Component, implements
from trac.web.api import IRequestHandler, IRequestFilter, HTTPBadRequest, HTTPForbidden
from trac.web.chrome import INavigationContributor, add_ctxtnav, add_stylesheet, add_script
from trac.util.translation import _
from trac.perm import IPermissionRequestor
from trac.util.datefmt import format_datetime, to_utimestamp

class TracLearnHandler(Component):
    """Handles additional TracLearn web requests"""
    
    implements(IRequestHandler, IRequestFilter, INavigationContributor, IPermissionRequestor)
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        """Return TracLearn permissions"""
        return ['TRACLEARN_API_ACCESS']
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        """Return active navigation item"""
        if req.path_info.startswith('/traclearn'):
            return 'traclearn'
        return None
    
    def get_navigation_items(self, req):
        """Add TracLearn to main navigation"""
        if 'TRACLEARN_VIEW' in req.perm:
            yield ('mainnav', 'traclearn',
                   tag.a(_('Learning'), href=req.href.traclearn()))
    
    # IRequestHandler methods
    def match_request(self, req):
        """Match TracLearn AJAX/API requests"""
        return req.path_info.startswith('/traclearn/ajax') or \
               req.path_info.startswith('/traclearn/data')
    
    def process_request(self, req):
        """Process AJAX and data requests"""
        req.perm.require('TRACLEARN_VIEW')
        
        if req.path_info.startswith('/traclearn/ajax'):
            return self._handle_ajax(req)
        elif req.path_info.startswith('/traclearn/data'):
            return self._handle_data(req)
    
    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        """Pre-process requests to add TracLearn context"""
        # Add TracLearn CSS/JS to relevant pages
        if req.path_info.startswith('/ticket') or \
           req.path_info.startswith('/newticket') or \
           req.path_info.startswith('/traclearn'):
            add_stylesheet(req, 'traclearn/css/traclearn.css')
            add_script(req, 'traclearn/js/learning.js')
        
        return handler
    
    def post_process_request(self, req, template, data, content_type):
        """Post-process to add TracLearn navigation items"""
        if template and data and 'TRACLEARN_VIEW' in req.perm:
            # Add context navigation for TracLearn pages
            if req.path_info.startswith('/traclearn'):
                if 'TRACLEARN_STUDENT' in req.perm:
                    add_ctxtnav(req, _('My Courses'), 
                               href=req.href.traclearn('my-courses'))
                    add_ctxtnav(req, _('My Progress'), 
                               href=req.href.traclearn('progress'))
                
                if 'TRACLEARN_INSTRUCTOR' in req.perm:
                    add_ctxtnav(req, _('Manage Courses'), 
                               href=req.href.traclearn('courses'))
                    add_ctxtnav(req, _('Analytics'), 
                               href=req.href.traclearn('analytics'))
                    add_ctxtnav(req, _('Grade Submissions'), 
                               href=req.href.traclearn('grading'))
                
                if 'TRACLEARN_ADMIN' in req.perm:
                    add_ctxtnav(req, _('Settings'), 
                               href=req.href.traclearn('admin'))
        
        return template, data, content_type
    
    # AJAX handlers
    def _handle_ajax(self, req):
        """Handle AJAX requests"""
        if req.method != 'POST':
            raise HTTPBadRequest('Method not allowed')
        
        action = req.args.get('action')
        
        if action == 'enroll':
            return self._ajax_enroll(req)
        elif action == 'unenroll':
            return self._ajax_unenroll(req)
        elif action == 'update_progress':
            return self._ajax_update_progress(req)
        elif action == 'get_recommendations':
            return self._ajax_get_recommendations(req)
        else:
            raise HTTPBadRequest('Unknown action')
    
    def _ajax_enroll(self, req):
        """Handle course enrollment via AJAX"""
        req.perm.require('TRACLEARN_STUDENT')
        
        course_id = req.args.get('course_id')
        if not course_id:
            raise HTTPBadRequest('Missing course_id')
        
        try:
            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO traclearn_enrollments 
                    (course_id, student_username, status)
                    VALUES (%s, %s, 'enrolled')
                """, (int(course_id), req.authname))
            
            response = {'success': True, 'message': _('Successfully enrolled')}
        except Exception as e:
            response = {'success': False, 'message': str(e)}
        
        req.send_response(200)
        req.send_header('Content-Type', 'application/json')
        req.write(json.dumps(response))
    
    def _ajax_unenroll(self, req):
        """Handle course unenrollment via AJAX"""
        req.perm.require('TRACLEARN_STUDENT')
        
        course_id = req.args.get('course_id')
        if not course_id:
            raise HTTPBadRequest('Missing course_id')
        
        try:
            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE traclearn_enrollments 
                    SET status = 'dropped'
                    WHERE course_id = %s AND student_username = %s
                """, (int(course_id), req.authname))
            
            response = {'success': True, 'message': _('Successfully unenrolled')}
        except Exception as e:
            response = {'success': False, 'message': str(e)}
        
        req.send_response(200)
        req.send_header('Content-Type', 'application/json')
        req.write(json.dumps(response))
    
    def _ajax_update_progress(self, req):
        """Update learning progress via AJAX"""
        enrollment_id = req.args.get('enrollment_id')
        progress_type = req.args.get('progress_type')
        progress_value = req.args.get('progress_value')
        
        if not all([enrollment_id, progress_type, progress_value]):
            raise HTTPBadRequest('Missing required parameters')
        
        try:
            # Verify enrollment belongs to user
            with self.env.db_query as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT student_username FROM traclearn_enrollments
                    WHERE id = %s
                """, (int(enrollment_id),))
                result = cursor.fetchone()
                
                if not result or result[0] != req.authname:
                    raise HTTPForbidden('Access denied')
            
            # Update progress
            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO traclearn_progress
                    (enrollment_id, ticket_id, progress_type, progress_value, recorded_at)
                    VALUES (%s, 0, %s, %s, %s)
                """, (int(enrollment_id), progress_type, float(progress_value),
                      to_utimestamp(datetime.now())))
            
            response = {'success': True, 'message': _('Progress updated')}
        except Exception as e:
            response = {'success': False, 'message': str(e)}
        
        req.send_response(200)
        req.send_header('Content-Type', 'application/json')
        req.write(json.dumps(response))
    
    def _ajax_get_recommendations(self, req):
        """Get AI-powered learning recommendations"""
        from traclearn.web.api_proxy import proxy_to_api
        
        # Proxy to Python 3.11 AI service
        return proxy_to_api(self.env, req, '/api/v1/ai/recommendations')
    
    # Data export handlers
    def _handle_data(self, req):
        """Handle data export requests"""
        req.perm.require('TRACLEARN_VIEW')
        
        data_type = req.args.get('type', 'progress')
        format = req.args.get('format', 'json')
        
        if data_type == 'progress':
            data = self._get_progress_data(req)
        elif data_type == 'grades':
            data = self._get_grades_data(req)
        elif data_type == 'analytics':
            req.perm.require('TRACLEARN_INSTRUCTOR')
            data = self._get_analytics_data(req)
        else:
            raise HTTPBadRequest('Unknown data type')
        
        if format == 'json':
            req.send_response(200)
            req.send_header('Content-Type', 'application/json')
            req.write(json.dumps(data, default=str))
        elif format == 'csv':
            req.send_response(200)
            req.send_header('Content-Type', 'text/csv')
            req.send_header('Content-Disposition', 
                          'attachment; filename="traclearn_%s.csv"' % data_type)
            req.write(self._convert_to_csv(data))
        else:
            raise HTTPBadRequest('Unknown format')
    
    def _get_progress_data(self, req):
        """Get user's progress data"""
        with self.env.db_query as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT c.course_code, c.title, p.progress_type, 
                       p.progress_value, p.recorded_at
                FROM traclearn_progress p
                JOIN traclearn_enrollments e ON p.enrollment_id = e.id
                JOIN traclearn_courses c ON e.course_id = c.id
                WHERE e.student_username = %s
                ORDER BY p.recorded_at DESC
            """, (req.authname,))
            
            return [{'course_code': row[0], 'course_title': row[1],
                    'progress_type': row[2], 'progress_value': row[3],
                    'recorded_at': format_datetime(row[4])}
                   for row in cursor]
    
    def _get_grades_data(self, req):
        """Get user's grades data"""
        with self.env.db_query as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT c.course_code, c.title, a.title, s.score, 
                       a.max_score, s.submitted_at, s.graded_at
                FROM traclearn_submissions s
                JOIN traclearn_assessments a ON s.assessment_id = a.id
                JOIN traclearn_enrollments e ON s.enrollment_id = e.id
                JOIN traclearn_courses c ON e.course_id = c.id
                WHERE e.student_username = %s AND s.score IS NOT NULL
                ORDER BY s.graded_at DESC
            """, (req.authname,))
            
            return [{'course_code': row[0], 'course_title': row[1],
                    'assessment': row[2], 'score': row[3], 'max_score': row[4],
                    'submitted_at': format_datetime(row[5]),
                    'graded_at': format_datetime(row[6])}
                   for row in cursor]
    
    def _get_analytics_data(self, req):
        """Get analytics data for instructors"""
        course_id = req.args.get('course_id')
        
        with self.env.db_query as db:
            cursor = db.cursor()
            
            if course_id:
                cursor.execute("""
                    SELECT analytics_type, metric_name, metric_value, 
                           calculated_at, metadata
                    FROM traclearn_analytics
                    WHERE entity_type = 'course' AND entity_id = %s
                    ORDER BY calculated_at DESC
                    LIMIT 100
                """, (int(course_id),))
            else:
                cursor.execute("""
                    SELECT c.course_code, a.analytics_type, a.metric_name, 
                           a.metric_value, a.calculated_at
                    FROM traclearn_analytics a
                    JOIN traclearn_courses c ON a.entity_id = c.id
                    WHERE a.entity_type = 'course'
                    ORDER BY a.calculated_at DESC
                    LIMIT 100
                """)
            
            return [dict(zip([col[0] for col in cursor.description], row))
                   for row in cursor]
    
    def _convert_to_csv(self, data):
        """Convert data to CSV format"""
        import csv
        from io import StringIO
        
        if not data:
            return ''
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue().encode('utf-8')