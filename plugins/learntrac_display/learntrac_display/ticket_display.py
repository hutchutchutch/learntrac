# -*- coding: utf-8 -*-
"""
LearnTrac Ticket Display Component

Implements ITicketManipulator and ITemplateProvider to display
learning questions in the ticket view with full integration to Learning Service API.
"""

import pkg_resources
import requests
import json
import logging
from datetime import datetime, timedelta
from trac.core import Component, implements, TracError
from trac.ticket.api import ITicketManipulator
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_script
from trac.util.html import tag
from trac.cache import cached
from genshi.filters.transform import Transformer

class LearningTicketDisplay(Component):
    """Main component for displaying learning questions in ticket view"""
    
    implements(ITicketManipulator, ITemplateProvider, ITemplateStreamFilter, IRequestHandler)
    
    # Configuration
    LEARNING_API_URL = 'http://learntrac-api:8001/api/learntrac'
    CACHE_TIMEOUT = 300  # 5 minutes
    
    def __init__(self):
        super().__init__()
        self.log = logging.getLogger(__name__)
    
    # ITicketManipulator methods
    
    def prepare_ticket(self, req, ticket, fields, actions):
        """Called when ticket page is prepared for display"""
        # Only process learning_concept tickets
        if ticket.get('type') != 'learning_concept':
            return
            
        try:
            # Load learning data for this ticket
            learning_data = self._get_learning_data(req, ticket)
            if learning_data:
                req.data['learning_question'] = learning_data.get('question', '')
                req.data['question_difficulty'] = learning_data.get('difficulty', '3')
                req.data['question_context'] = learning_data.get('context', '')
                req.data['expected_answer'] = learning_data.get('expected_answer', '')
                req.data['user_progress'] = self._get_user_progress(req, ticket.id)
                req.data['show_answer_form'] = True
                req.data['is_learning_ticket'] = True
        except Exception as e:
            self.log.error("Error preparing learning ticket %s: %s", ticket.id, e)
    
    def validate_ticket(self, req, ticket):
        """Validate ticket fields (not used for display)"""
        return []
    
    # ITemplateProvider methods
    
    def get_htdocs_dirs(self):
        """Return static resource directories"""
        return [('learntrac_display', pkg_resources.resource_filename(__name__, 'htdocs'))]
    
    def get_templates_dirs(self):
        """Return template directories"""
        return [pkg_resources.resource_filename(__name__, 'templates')]
    
    # IRequestHandler methods
    
    def match_request(self, req):
        """Handle AJAX requests for answer submission"""
        return req.path_info.startswith('/learntrac/submit_answer')
    
    def process_request(self, req):
        """Process answer submission requests"""
        if req.method == 'POST' and req.path_info.startswith('/learntrac/submit_answer'):
            return self._handle_answer_submission(req)
        return None, None, None
    
    # ITemplateStreamFilter methods
    
    def filter_stream(self, req, method, filename, stream, data):
        """Filter the template stream to inject learning questions"""
        
        # Only process ticket view pages
        if filename != 'ticket.html':
            return stream
            
        # Check if we have a learning ticket
        ticket = data.get('ticket')
        if not ticket or ticket.get('type') != 'learning_concept':
            return stream
            
        # Add CSS and JavaScript resources
        add_stylesheet(req, 'learntrac_display/css/learntrac.css')
        add_script(req, 'learntrac_display/js/learntrac.js')
        
        # Only inject if we have learning data
        if data.get('is_learning_ticket'):
            # Create the learning questions panel
            panel = self._create_learning_panel(req, ticket, data)
            
            # Inject the panel after the ticket description
            stream = stream | Transformer('//div[@id="ticket"]//div[@class="description"]').after(panel)
        
        return stream
    
    def _get_learning_data(self, req, ticket):
        """Retrieve learning question data from custom fields"""
        try:
            # Get custom fields from database
            with self.env.db_query as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT name, value 
                    FROM ticket_custom 
                    WHERE ticket = %s AND name IN ('question', 'expected_answer', 'question_difficulty', 'question_context')
                """, (ticket.id,))
                
                custom_fields = dict(cursor.fetchall())
                
                if custom_fields.get('question'):
                    return {
                        'question': custom_fields.get('question', ''),
                        'expected_answer': custom_fields.get('expected_answer', ''),
                        'difficulty': custom_fields.get('question_difficulty', '3'),
                        'context': custom_fields.get('question_context', '')
                    }
                
        except Exception as e:
            self.log.error("Error getting learning data for ticket %s: %s", ticket.id, e)
        
        return None
    
    @cached('learntrac_progress', lambda self, req, ticket_id: "{}_{}".format(ticket_id, req.session.get('cognito_sub', 'anonymous')))
    def _get_user_progress(self, req, ticket_id):
        """Get user progress from Learning Service API with caching"""
        try:
            user_id = self._get_user_id(req)
            if not user_id:
                return None
                
            # Call Learning Service API
            headers = self._get_auth_headers(req)
            response = requests.get(
                "{}/tickets/{}/details".format(self.LEARNING_API_URL, ticket_id),
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': data.get('progress_status', 'not_started'),
                    'mastery_score': data.get('mastery_score'),
                    'time_spent_minutes': data.get('time_spent_minutes'),
                    'last_accessed': data.get('last_accessed'),
                    'notes': data.get('progress_notes'),
                    'attempt_count': data.get('attempt_count', 0)
                }
            else:
                self.log.warning("Learning API returned %s for ticket %s", response.status_code, ticket_id)
                
        except requests.RequestException as e:
            self.log.error("Error calling Learning Service API: %s", e)
        except Exception as e:
            self.log.error("Error getting user progress: %s", e)
        
        return None
    
    def _get_user_id(self, req):
        """Extract user ID from session (Cognito sub)"""
        return req.session.get('cognito_sub') or req.authname
    
    def _get_auth_headers(self, req):
        """Get authentication headers for API calls"""
        headers = {'Content-Type': 'application/json'}
        
        # Try to get JWT token from session
        jwt_token = req.session.get('jwt_token')
        if jwt_token:
            headers['Authorization'] = 'Bearer {}'.format(jwt_token)
        
        return headers
    
    def _create_learning_panel(self, req, ticket, data):
        """Create the HTML panel for displaying learning questions"""
        
        question = data.get('learning_question', '')
        difficulty = data.get('question_difficulty', '3')
        context = data.get('question_context', '')
        progress = data.get('user_progress', {})
        
        # Main panel container
        panel = tag.div(
            tag.div(
                tag.h3('Learning Question', class_='learning-header'),
                tag.div(
                    tag.div(
                        tag.p(question, class_='question-text'),
                        tag.div(
                            tag.span("Difficulty: {}/5".format(difficulty), class_='difficulty-badge'),
                            tag.span("Context: {}".format(context), class_='context-info') if context else '',
                            class_='question-meta'
                        ),
                        class_='question-content'
                    ),
                    self._render_answer_section(req, ticket, progress),
                    self._render_previous_attempts(progress) if progress else tag.div(),
                    class_='learning-content'
                ),
                class_='learning-question-panel'
            ),
            id='learning-answer-section',
            class_='learntrac-panel'
        )
        
        return panel
    
    def _render_answer_section(self, req, ticket, progress):
        """Render the answer input section"""
        
        last_answer = ''
        if progress and progress.get('notes'):
            # Extract last answer from notes if available
            notes = progress.get('notes', '')
            if 'Last Answer:' in notes:
                last_answer = notes.split('Last Answer:')[-1].strip()
        
        status = progress.get('status', 'not_started') if progress else 'not_started'
        is_completed = status in ['completed', 'mastered']
        
        section = tag.div(
            tag.h4('Your Answer'),
            tag.div(
                tag.textarea(
                    last_answer,
                    name='student_answer',
                    id='answer_{}'.format(ticket.id),
                    rows='6',
                    cols='80',
                    placeholder='Type your answer here...',
                    class_='answer-textarea',
                    disabled='disabled' if is_completed else None
                ),
                tag.div(
                    tag.button(
                        'Submit Answer' if not is_completed else 'Answer Submitted',
                        id='learntrac-submit',
                        class_='learntrac-submit-btn' + (' disabled' if is_completed else ''),
                        onclick='submitAnswer({})'.format(ticket.id) if not is_completed else None,
                        disabled='disabled' if is_completed else None,
                        **{'data-ticket-id': str(ticket.id)}
                    ),
                    tag.div(id='submission-status', class_='submission-status'),
                    class_='answer-actions'
                ),
                class_='answer-form'
            ),
            class_='answer-section'
        )
        
        return section
    
    def _render_previous_attempts(self, progress):
        """Render previous attempt information"""
        if not progress:
            return tag.div()
        
        attempt_count = progress.get('attempt_count', 0)
        last_accessed = progress.get('last_accessed')
        mastery_score = progress.get('mastery_score')
        time_spent = progress.get('time_spent_minutes', 0)
        
        attempts_section = tag.div(
            tag.h4('Progress Information'),
            tag.div(
                tag.div(
                    tag.strong('Status: '),
                    tag.span(progress.get('status', 'not_started').title(), class_='status-value'),
                    class_='progress-item'
                ),
                tag.div(
                    tag.strong('Attempts: '),
                    tag.span(str(attempt_count), class_='attempts-value'),
                    class_='progress-item'
                ) if attempt_count > 0 else '',
                tag.div(
                    tag.strong('Time Spent: '),
                    tag.span("{} minutes".format(time_spent), class_='time-value'),
                    class_='progress-item'
                ) if time_spent > 0 else '',
                tag.div(
                    tag.strong('Mastery Score: '),
                    tag.span("{:.2f}".format(mastery_score) if mastery_score else "Not scored", class_='score-value'),
                    class_='progress-item'
                ) if mastery_score is not None else '',
                tag.div(
                    tag.strong('Last Accessed: '),
                    tag.span(self._format_datetime(last_accessed), class_='date-value'),
                    class_='progress-item'
                ) if last_accessed else '',
                class_='progress-info'
            ),
            class_='previous-attempts'
        )
        
        return attempts_section
    
    def _handle_answer_submission(self, req):
        """Handle AJAX answer submission"""
        try:
            # Parse request data
            data = json.loads(req.read().decode('utf-8'))
            ticket_id = int(data.get('ticket_id'))
            answer = data.get('answer', '').strip()
            
            if not answer:
                return self._json_response({'error': 'Answer cannot be empty'}, 400)
            
            user_id = self._get_user_id(req)
            if not user_id:
                return self._json_response({'error': 'User not authenticated'}, 401)
            
            # Submit to Learning Service API
            headers = self._get_auth_headers(req)
            payload = {
                'status': 'completed',
                'notes': 'Answer submitted on {}: {}'.format(datetime.now().isoformat(), answer),
                'time_spent_minutes': data.get('time_spent', 30)  # Default 30 minutes
            }
            
            # Use evaluation endpoint for answer submission
            eval_payload = {
                'ticket_id': ticket_id,
                'answer': answer,
                'time_spent_minutes': data.get('time_spent', 30)
            }
            
            response = requests.post(
                "{}/evaluation/evaluate".format(self.LEARNING_API_URL),
                json=eval_payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                # Clear cache for this user/ticket
                cache_key = "learntrac_progress:{}_{}".format(ticket_id, user_id)
                self.env.cache.invalidate(cache_key)
                
                # Parse evaluation response
                eval_result = response.json()
                
                return self._json_response({
                    'success': True,
                    'message': 'Answer evaluated successfully',
                    'score': eval_result.get('score', 0.0),
                    'feedback': eval_result.get('feedback', ''),
                    'status': eval_result.get('status', 'completed'),
                    'mastery_achieved': eval_result.get('mastery_achieved', False)
                })
            else:
                self.log.error("Learning API error %s: %s", response.status_code, response.text)
                return self._json_response({'error': 'Failed to submit answer'}, 500)
                
        except Exception as e:
            self.log.error("Error submitting answer: %s", e)
            return self._json_response({'error': 'Internal server error'}, 500)
    
    def _json_response(self, data, status=200):
        """Return JSON response"""
        content = json.dumps(data)
        return content, 'application/json', None
    
    def _format_datetime(self, dt_str):
        """Format datetime string for display"""
        if not dt_str:
            return 'Never'
        
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return str(dt_str)