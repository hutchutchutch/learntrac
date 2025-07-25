/**
 * LearnTrac Display Plugin JavaScript
 * Handles interactions with learning questions in ticket view
 * Integrates with Learning Service API for answer submission
 */

(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Initialize the learning questions panel if it exists
        var $panel = $('#learning-answer-section');
        if ($panel.length === 0) {
            return;
        }
        
        // Handle textarea changes for auto-save
        $('.answer-textarea').on('input', function() {
            validateForm();
            clearTimeout(window.autoSaveTimeout);
            window.autoSaveTimeout = setTimeout(saveDraft, 2000); // Auto-save after 2 seconds
        });
        
        // Initial form validation
        validateForm();
        
        // Initialize keyboard shortcuts
        initKeyboardShortcuts();
        
        // Start time tracking
        startTimeTracking();
    });
    
    /**
     * Global function to submit answer (called from onclick in HTML)
     */
    window.submitAnswer = function(ticketId) {
        var $button = $('#learntrac-submit');
        var answer = $('#answer_' + ticketId).val().trim();
        
        if (!answer) {
            showMessage('Please enter an answer before submitting', 'error');
            return;
        }
        
        // Disable submit button and show loading state
        $button.prop('disabled', true).text('Submitting...');
        
        // Calculate time spent (roughly)
        var timeSpent = Math.max(1, Math.floor((Date.now() - window.learningStartTime) / 60000));
        
        // Prepare data for submission
        var data = {
            ticket_id: ticketId,
            answer: answer,
            time_spent: timeSpent,
            timestamp: new Date().toISOString()
        };
        
        // Submit to Trac API endpoint
        $.ajax({
            url: '/learntrac/submit_answer',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                if (response.success) {
                    // Show evaluation results
                    var scorePercent = Math.round(response.score * 100);
                    var messageHtml = '<strong>Answer evaluated!</strong><br>';
                    messageHtml += 'Score: ' + scorePercent + '%<br>';
                    
                    if (response.mastery_achieved) {
                        messageHtml += '<span style="color: #28a745;">✨ Mastery achieved!</span><br>';
                    }
                    
                    if (response.feedback) {
                        messageHtml += '<div style="margin-top: 10px;">' + response.feedback + '</div>';
                    }
                    
                    showMessage(messageHtml, 'success');
                    
                    // Update UI to show completion
                    $button.text('Answer Evaluated').addClass('disabled');
                    $('#answer_' + ticketId).prop('disabled', true);
                    
                    // Clear draft
                    clearDraft(ticketId);
                    
                    // Refresh page after delay to show updated progress
                    setTimeout(function() {
                        window.location.reload();
                    }, 5000);
                } else {
                    showMessage(response.error || 'Failed to evaluate answer', 'error');
                    $button.prop('disabled', false).text('Submit Answer');
                }
            },
            error: function(xhr, status, error) {
                var errorMsg = 'Failed to submit answer';
                try {
                    var response = JSON.parse(xhr.responseText);
                    errorMsg = response.error || errorMsg;
                } catch (e) {
                    errorMsg = xhr.status === 401 ? 'Please log in to submit answers' : errorMsg;
                }
                
                showMessage(errorMsg, 'error');
                $button.prop('disabled', false).text('Submit Answer');
            }
        });
    };
    
    /**
     * Validate the form and update submit button state
     */
    function validateForm() {
        var $textarea = $('.answer-textarea');
        var $submitBtn = $('#learntrac-submit');
        
        if ($textarea.length > 0 && $textarea.val().trim() !== '') {
            $submitBtn.prop('disabled', false);
        } else {
            $submitBtn.prop('disabled', true);
        }
    }
    
    /**
     * Show a message to the user
     */
    function showMessage(text, type) {
        // Remove any existing messages
        $('.learntrac-message').remove();
        
        // Create and show new message
        var $message = $('<div>')
            .addClass('learntrac-message')
            .addClass('message-' + type)
            .html('<span class="message-icon"></span><span class="message-text">' + text + '</span>');
        
        $('#learning-answer-section').prepend($message);
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(function() {
                $message.fadeOut(function() {
                    $(this).remove();
                });
            }, 5000);
        }
    }
    
    /**
     * Initialize keyboard shortcuts
     */
    function initKeyboardShortcuts() {
        $(document).on('keydown', function(e) {
            // Ctrl+Enter or Cmd+Enter to submit
            if ((e.ctrlKey || e.metaKey) && e.keyCode === 13) {
                var $submitBtn = $('#learntrac-submit');
                if (!$submitBtn.prop('disabled') && $submitBtn.is(':visible')) {
                    var ticketId = $submitBtn.data('ticket-id');
                    if (ticketId) {
                        submitAnswer(ticketId);
                    }
                }
            }
        });
    }
    
    /**
     * Start time tracking for this learning session
     */
    function startTimeTracking() {
        if (!window.learningStartTime) {
            window.learningStartTime = Date.now();
        }
        
        // Update time display every minute
        setInterval(updateTimeDisplay, 60000);
        updateTimeDisplay(); // Initial update
    }
    
    /**
     * Update the time display
     */
    function updateTimeDisplay() {
        if (window.learningStartTime) {
            var timeSpent = Math.floor((Date.now() - window.learningStartTime) / 60000);
            var timeText = timeSpent < 1 ? 'Less than 1 minute' : timeSpent + ' minute' + (timeSpent === 1 ? '' : 's');
            
            // Add or update time display
            var $timeDisplay = $('.time-spent-display');
            if ($timeDisplay.length === 0) {
                $timeDisplay = $('<div class="time-spent-display">Time spent: <span class="time-value">' + timeText + '</span></div>');
                $('.answer-actions').append($timeDisplay);
            } else {
                $timeDisplay.find('.time-value').text(timeText);
            }
        }
    }
    
    /**
     * Save draft answers to localStorage
     */
    function saveDraft() {
        var $textarea = $('.answer-textarea');
        if ($textarea.length > 0) {
            var ticketId = $('#learntrac-submit').data('ticket-id');
            var answer = $textarea.val();
            
            if (ticketId && answer) {
                localStorage.setItem('learntrac_draft_' + ticketId, answer);
                
                // Show brief save indicator
                var $indicator = $('.draft-saved-indicator');
                if ($indicator.length === 0) {
                    $indicator = $('<span class="draft-saved-indicator">Draft saved</span>');
                    $('.answer-actions').append($indicator);
                }
                
                $indicator.fadeIn().delay(1000).fadeOut();
            }
        }
    }
    
    /**
     * Load draft answer from localStorage
     */
    function loadDraft() {
        var ticketId = $('#learntrac-submit').data('ticket-id');
        if (ticketId) {
            var draft = localStorage.getItem('learntrac_draft_' + ticketId);
            if (draft) {
                var $textarea = $('.answer-textarea');
                if ($textarea.length > 0 && !$textarea.val()) {
                    $textarea.val(draft);
                    validateForm();
                }
            }
        }
    }
    
    /**
     * Clear draft from localStorage
     */
    function clearDraft(ticketId) {
        if (ticketId) {
            localStorage.removeItem('learntrac_draft_' + ticketId);
        }
    }
    
    /**
     * Initialize draft loading on page load
     */
    $(document).ready(function() {
        setTimeout(loadDraft, 100); // Small delay to ensure DOM is ready
    });
    
})(jQuery);