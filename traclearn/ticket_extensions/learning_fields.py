# -*- coding: utf-8 -*-
"""
TracLearn Custom Ticket Fields Provider
Implements ITicketCustomFieldProvider for learning-related fields
"""

from __future__ import absolute_import, print_function, unicode_literals

from trac.core import Component, implements
from trac.ticket.api import ITicketCustomFieldProvider, ITicketActionController
from trac.util.translation import _
from trac.util.datefmt import format_datetime, to_utimestamp, from_utimestamp
from datetime import datetime

class LearningFieldsProvider(Component):
    """Provides custom ticket fields for learning activities"""
    
    implements(ITicketCustomFieldProvider, ITicketActionController)
    
    # ITicketCustomFieldProvider methods
    def get_custom_fields(self):
        """Return custom field definitions for learning"""
        return [
            {
                'name': 'learning_course',
                'type': 'select',
                'label': _('Learning Course'),
                'value': '',
                'options': self._get_course_options(),
                'order': 100,
                'custom': True,
                'format': 'plain',
                'description': _('Associated learning course')
            },
            {
                'name': 'learning_type',
                'type': 'select',
                'label': _('Learning Activity Type'),
                'value': '',
                'options': ['', 'assignment', 'project', 'quiz', 'exam', 
                           'discussion', 'lab', 'reading', 'video', 'resource'],
                'order': 101,
                'custom': True,
                'format': 'plain',
                'description': _('Type of learning activity')
            },
            {
                'name': 'learning_points',
                'type': 'text',
                'label': _('Points/Credits'),
                'value': '0',
                'order': 102,
                'custom': True,
                'format': 'plain',
                'max_size': 10,
                'description': _('Points or credits for this activity')
            },
            {
                'name': 'learning_due_date',
                'type': 'time',
                'label': _('Due Date'),
                'value': '',
                'order': 103,
                'custom': True,
                'format': 'datetime',
                'description': _('Due date for learning activity')
            },
            {
                'name': 'learning_difficulty',
                'type': 'select',
                'label': _('Difficulty Level'),
                'value': 'medium',
                'options': ['', 'beginner', 'easy', 'medium', 'hard', 'expert'],
                'order': 104,
                'custom': True,
                'format': 'plain',
                'description': _('Difficulty level of the activity')
            },
            {
                'name': 'learning_estimated_hours',
                'type': 'text',
                'label': _('Estimated Hours'),
                'value': '1',
                'order': 105,
                'custom': True,
                'format': 'plain',
                'max_size': 10,
                'description': _('Estimated hours to complete')
            },
            {
                'name': 'learning_prerequisites',
                'type': 'textarea',
                'label': _('Prerequisites'),
                'value': '',
                'order': 106,
                'custom': True,
                'format': 'wiki',
                'rows': 3,
                'description': _('Prerequisites for this activity')
            },
            {
                'name': 'learning_objectives',
                'type': 'textarea',
                'label': _('Learning Objectives'),
                'value': '',
                'order': 107,
                'custom': True,
                'format': 'wiki',
                'rows': 5,
                'description': _('Learning objectives to be achieved')
            },
            {
                'name': 'learning_resources',
                'type': 'textarea',
                'label': _('Learning Resources'),
                'value': '',
                'order': 108,
                'custom': True,
                'format': 'wiki',
                'rows': 3,
                'description': _('Additional learning resources and references')
            },
            {
                'name': 'learning_submission_type',
                'type': 'select',
                'label': _('Submission Type'),
                'value': 'online',
                'options': ['', 'online', 'file_upload', 'in_person', 'external', 'none'],
                'order': 109,
                'custom': True,
                'format': 'plain',
                'description': _('How the activity should be submitted')
            },
            {
                'name': 'learning_grading_rubric',
                'type': 'textarea',
                'label': _('Grading Rubric'),
                'value': '',
                'order': 110,
                'custom': True,
                'format': 'wiki',
                'rows': 5,
                'description': _('Grading rubric or criteria')
            },
            {
                'name': 'learning_completion_status',
                'type': 'select',
                'label': _('Completion Status'),
                'value': 'not_started',
                'options': ['not_started', 'in_progress', 'submitted', 
                           'graded', 'completed', 'exempted'],
                'order': 111,
                'custom': True,
                'format': 'plain',
                'description': _('Current completion status')
            },
            {
                'name': 'learning_score',
                'type': 'text',
                'label': _('Score Achieved'),
                'value': '',
                'order': 112,
                'custom': True,
                'format': 'plain',
                'max_size': 10,
                'description': _('Score achieved (if graded)')
            },
            {
                'name': 'learning_feedback',
                'type': 'textarea',
                'label': _('Instructor Feedback'),
                'value': '',
                'order': 113,
                'custom': True,
                'format': 'wiki',
                'rows': 5,
                'description': _('Feedback from instructor')
            },
            {
                'name': 'learning_peer_review',
                'type': 'checkbox',
                'label': _('Requires Peer Review'),
                'value': '0',
                'order': 114,
                'custom': True,
                'description': _('Whether this activity requires peer review')
            },
            {
                'name': 'learning_group_work',
                'type': 'checkbox',
                'label': _('Group Activity'),
                'value': '0',
                'order': 115,
                'custom': True,
                'description': _('Whether this is a group activity')
            },
            {
                'name': 'learning_tags',
                'type': 'text',
                'label': _('Learning Tags'),
                'value': '',
                'order': 116,
                'custom': True,
                'format': 'list',
                'description': _('Tags for categorizing learning content')
            }
        ]
    
    # ITicketActionController methods
    def get_ticket_actions(self, req, ticket):
        """Add learning-specific actions"""
        actions = []
        
        if ticket and ticket.get_value('learning_course'):
            # Add learning-specific workflow actions
            if 'TRACLEARN_STUDENT' in req.perm:
                if ticket.get_value('learning_completion_status') == 'not_started':
                    actions.append(('start_learning', _('Start Activity')))
                elif ticket.get_value('learning_completion_status') == 'in_progress':
                    actions.append(('submit_learning', _('Submit Activity')))
            
            if 'TRACLEARN_INSTRUCTOR' in req.perm:
                if ticket.get_value('learning_completion_status') == 'submitted':
                    actions.append(('grade_learning', _('Grade Activity')))
                    actions.append(('request_revision', _('Request Revision')))
        
        return actions
    
    def apply_action_side_effects(self, req, ticket, action):
        """Apply side effects of learning actions"""
        if action == 'start_learning':
            ticket['learning_completion_status'] = 'in_progress'
            self._record_learning_event(ticket, 'started', req.authname)
            
        elif action == 'submit_learning':
            ticket['learning_completion_status'] = 'submitted'
            ticket['status'] = 'pending'
            self._record_learning_event(ticket, 'submitted', req.authname)
            
        elif action == 'grade_learning':
            ticket['learning_completion_status'] = 'graded'
            if ticket.get_value('learning_score'):
                score = float(ticket.get_value('learning_score'))
                max_score = float(ticket.get_value('learning_points') or 100)
                if score >= max_score * 0.7:  # 70% passing grade
                    ticket['status'] = 'closed'
                    ticket['resolution'] = 'completed'
            self._record_learning_event(ticket, 'graded', req.authname)
            
        elif action == 'request_revision':
            ticket['learning_completion_status'] = 'in_progress'
            ticket['status'] = 'reopened'
            self._record_learning_event(ticket, 'revision_requested', req.authname)
    
    def get_action_control(self, req, ticket, action):
        """Get control specification for learning actions"""
        controls = {
            'start_learning': (_('Start Activity'), 'Start working on this learning activity'),
            'submit_learning': (_('Submit Activity'), 'Submit your completed work'),
            'grade_learning': (_('Grade Activity'), 'Grade and provide feedback'),
            'request_revision': (_('Request Revision'), 'Ask student to revise and resubmit'),
        }
        
        if action in controls:
            label, hint = controls[action]
            return label, None, hint
        
        return None, None, None
    
    # Helper methods
    def _get_course_options(self):
        """Get list of available courses"""
        options = ['']
        try:
            with self.env.db_query as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT course_code, title 
                    FROM traclearn_courses 
                    WHERE status = 'active'
                    ORDER BY course_code
                """)
                for code, title in cursor:
                    options.append('%s - %s' % (code, title[:50]))
        except:
            # Table might not exist yet during setup
            pass
        return options
    
    def _record_learning_event(self, ticket, event_type, user):
        """Record a learning event in the database"""
        try:
            course_code = ticket.get_value('learning_course').split(' - ')[0]
            
            with self.env.db_transaction as db:
                cursor = db.cursor()
                
                # Get enrollment ID
                cursor.execute("""
                    SELECT e.id 
                    FROM traclearn_enrollments e
                    JOIN traclearn_courses c ON e.course_id = c.id
                    WHERE c.course_code = %s AND e.student_username = %s
                """, (course_code, ticket['reporter']))
                
                result = cursor.fetchone()
                if result:
                    enrollment_id = result[0]
                    
                    # Record progress event
                    progress_value = {
                        'started': 10,
                        'submitted': 50,
                        'graded': 100,
                        'revision_requested': 30
                    }.get(event_type, 0)
                    
                    cursor.execute("""
                        INSERT INTO traclearn_progress 
                        (enrollment_id, ticket_id, progress_type, progress_value, details)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (enrollment_id, ticket.id, event_type, progress_value,
                          '{"event": "%s", "user": "%s", "timestamp": "%s"}' % 
                          (event_type, user, format_datetime(datetime.now(), utc))))
        except Exception as e:
            self.log.warning("Failed to record learning event: %s", e)

class LearningFieldsFormatter(Component):
    """Format and validate learning field values"""
    
    def format_learning_date(self, value):
        """Format learning date fields"""
        if value:
            try:
                timestamp = int(value)
                return format_datetime(from_utimestamp(timestamp))
            except:
                return value
        return ''
    
    def validate_points(self, value):
        """Validate points field"""
        if value:
            try:
                points = float(value)
                if points < 0:
                    return None, _("Points must be non-negative")
                return points, None
            except ValueError:
                return None, _("Points must be a number")
        return 0, None
    
    def validate_hours(self, value):
        """Validate estimated hours field"""
        if value:
            try:
                hours = float(value)
                if hours < 0:
                    return None, _("Hours must be non-negative")
                if hours > 1000:
                    return None, _("Hours seems unreasonably high")
                return hours, None
            except ValueError:
                return None, _("Hours must be a number")
        return 1, None