/**
 * Learning Path Macro JavaScript
 * 
 * Provides interactive features for learning path displays
 */

(function($) {
    'use strict';
    
    // Initialize learning path interactive features
    function initLearningPath() {
        // Tree view expand/collapse
        $('.learningpath-interactive .learningpath-item').on('click', function(e) {
            if ($(e.target).is('a')) {
                return; // Don't toggle when clicking links
            }
            
            e.stopPropagation();
            $(this).toggleClass('expanded');
            
            // Animate subtree
            var subtree = $(this).find('> .learningpath-subtree');
            if (subtree.length) {
                subtree.slideToggle(200);
            }
            
            // Update progress if needed
            updateProgress($(this));
        });
        
        // Progress bar animations
        animateProgressBars();
        
        // Initialize graph view if present
        if ($('#learningpath-graph-canvas').length) {
            initGraphView();
        }
        
        // Handle view switching if multiple views are available
        initViewSwitcher();
        
        // Track learning path interactions
        trackInteractions();
    }
    
    // Animate progress bars on page load
    function animateProgressBars() {
        $('.learningpath-progress').each(function() {
            var $progress = $(this);
            var $fill = $progress.find('.progress-fill');
            var targetWidth = $fill.css('width');
            
            // Start from 0 and animate to target
            $fill.css('width', '0');
            setTimeout(function() {
                $fill.css('width', targetWidth);
            }, 100);
        });
    }
    
    // Initialize graph view using D3.js or similar
    function initGraphView() {
        var canvas = document.getElementById('learningpath-graph-canvas');
        if (!canvas) return;
        
        // This is a placeholder for graph visualization
        // In a real implementation, you would use D3.js or similar
        var ctx = canvas.getContext ? canvas.getContext('2d') : null;
        if (ctx) {
            // Draw a simple placeholder graph
            ctx.fillStyle = '#f0f0f0';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#333';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Interactive graph visualization would appear here', 
                        canvas.width / 2, canvas.height / 2);
        }
    }
    
    // Initialize view switcher if multiple views are enabled
    function initViewSwitcher() {
        var $container = $('.learningpath-container');
        var views = ['tree', 'list', 'graph', 'timeline'];
        var currentView = $container.data('view') || 'tree';
        
        // Add view switcher buttons if not present
        if (!$container.find('.view-switcher').length && views.length > 1) {
            var $switcher = $('<div class="view-switcher"></div>');
            
            views.forEach(function(view) {
                var $btn = $('<button></button>')
                    .text(view.charAt(0).toUpperCase() + view.slice(1))
                    .addClass('view-btn')
                    .data('view', view);
                
                if (view === currentView) {
                    $btn.addClass('active');
                }
                
                $switcher.append($btn);
            });
            
            $container.prepend($switcher);
            
            // Handle view switching
            $switcher.on('click', '.view-btn', function() {
                var newView = $(this).data('view');
                switchView(newView);
            });
        }
    }
    
    // Switch between different views
    function switchView(newView) {
        // This would typically make an AJAX request to get the new view
        // For now, we'll just update the UI
        $('.view-btn').removeClass('active');
        $('.view-btn[data-view="' + newView + '"]').addClass('active');
        
        // In a real implementation, you would load the new view via AJAX
        console.log('Switching to view:', newView);
    }
    
    // Update progress via AJAX
    function updateProgress($element) {
        var pathId = $element.data('path-id');
        if (!pathId) return;
        
        // Check if this action should update progress
        var shouldUpdate = $element.hasClass('mark-complete') || 
                          $element.find('input[type="checkbox"]:checked').length;
        
        if (shouldUpdate) {
            $.ajax({
                url: Trac.env.href + '/learningpath/progress',
                type: 'POST',
                data: {
                    path_id: pathId,
                    action: 'update',
                    progress: 100,
                    __FORM_TOKEN: Trac.form_token
                },
                success: function(response) {
                    // Update UI
                    $element.addClass('completed');
                    showNotification('Progress updated!');
                },
                error: function() {
                    showNotification('Failed to update progress', 'error');
                }
            });
        }
    }
    
    // Track user interactions for analytics
    function trackInteractions() {
        $('.learningpath-container').on('click', 'a', function() {
            var $link = $(this);
            var pathName = $link.closest('[data-topic]').data('topic');
            var linkText = $link.text();
            
            // Send tracking data
            if (window.ga) {
                ga('send', 'event', 'LearningPath', 'click', pathName + ' - ' + linkText);
            }
        });
    }
    
    // Show notification messages
    function showNotification(message, type) {
        type = type || 'success';
        
        var $notification = $('<div class="learningpath-notification"></div>')
            .addClass('notification-' + type)
            .text(message);
        
        $('body').append($notification);
        
        setTimeout(function() {
            $notification.fadeIn(200);
        }, 10);
        
        setTimeout(function() {
            $notification.fadeOut(200, function() {
                $(this).remove();
            });
        }, 3000);
    }
    
    // Keyboard navigation support
    function initKeyboardNav() {
        var $items = $('.learningpath-item');
        var currentIndex = -1;
        
        $(document).on('keydown', function(e) {
            if (!$('.learningpath-container').is(':visible')) return;
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    currentIndex = Math.min(currentIndex + 1, $items.length - 1);
                    highlightItem(currentIndex);
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    currentIndex = Math.max(currentIndex - 1, 0);
                    highlightItem(currentIndex);
                    break;
                    
                case 'Enter':
                case ' ':
                    if (currentIndex >= 0) {
                        e.preventDefault();
                        $items.eq(currentIndex).click();
                    }
                    break;
                    
                case 'Escape':
                    currentIndex = -1;
                    $items.removeClass('keyboard-focus');
                    break;
            }
        });
        
        function highlightItem(index) {
            $items.removeClass('keyboard-focus');
            if (index >= 0) {
                $items.eq(index).addClass('keyboard-focus').focus();
            }
        }
    }
    
    // Initialize on document ready
    $(document).ready(function() {
        initLearningPath();
        initKeyboardNav();
        
        // Reinitialize after AJAX content loads
        $(document).on('ajaxComplete', function() {
            initLearningPath();
        });
    });
    
})(jQuery);

// Additional styles for JavaScript features
(function() {
    var style = document.createElement('style');
    style.textContent = `
        .view-switcher {
            margin-bottom: 1em;
            display: flex;
            gap: 0.5em;
        }
        
        .view-btn {
            padding: 0.5em 1em;
            border: 1px solid #dee2e6;
            background: white;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s;
        }
        
        .view-btn:hover {
            background: #f8f9fa;
        }
        
        .view-btn.active {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }
        
        .learningpath-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1em 1.5em;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 1000;
            display: none;
        }
        
        .notification-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .notification-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .keyboard-focus {
            outline: 3px solid #007bff;
            outline-offset: 2px;
        }
        
        .learningpath-item.completed {
            background: #d4edda;
            border-color: #c3e6cb;
        }
    `;
    document.head.appendChild(style);
})();