/**
 * Learning Roadmap Interactive Features
 */

(function($) {
    'use strict';
    
    var LearningRoadmap = {
        
        init: function() {
            this.bindEvents();
            this.initProgressAnimations();
            this.loadDynamicData();
        },
        
        bindEvents: function() {
            // Milestone card interactions
            $('.milestone-card').on('click', '.view-details', this.showMilestoneDetails);
            
            // Export functionality
            $('.export-buttons .button').on('click', this.handleExport);
            
            // Filter changes
            $('#milestone').on('change', this.filterMilestones);
            
            // Refresh button
            $('.refresh-progress').on('click', this.refreshProgress);
        },
        
        initProgressAnimations: function() {
            // Animate progress bars on page load
            $('.progress-fill').each(function() {
                var $this = $(this);
                var width = $this.css('width');
                $this.css('width', '0');
                
                // Delay animation for visual effect
                setTimeout(function() {
                    $this.animate({width: width}, 1000, 'easeOutQuart');
                }, 100);
            });
            
            // Animate numbers
            $('.big-number').each(function() {
                var $this = $(this);
                var value = parseFloat($this.text());
                
                $({value: 0}).animate({value: value}, {
                    duration: 1500,
                    easing: 'easeOutQuart',
                    step: function() {
                        $this.text(this.value.toFixed(0) + '%');
                    }
                });
            });
        },
        
        loadDynamicData: function() {
            // Load learning velocity chart if container exists
            if ($('#velocity-chart').length) {
                this.loadVelocityChart();
            }
            
            // Load score trends if container exists
            if ($('#score-trends').length) {
                this.loadScoreTrends();
            }
        },
        
        showMilestoneDetails: function(e) {
            e.preventDefault();
            var milestoneId = $(this).data('milestone');
            
            // Create modal or expand section
            var $modal = $('<div class="milestone-modal">').appendTo('body');
            
            $.ajax({
                url: '/learning/api/milestone-details',
                data: { milestone: milestoneId },
                success: function(data) {
                    $modal.html(data);
                    $modal.show();
                }
            });
        },
        
        handleExport: function(e) {
            e.preventDefault();
            var format = $(this).attr('href').split('/').pop();
            var $button = $(this);
            
            // Show loading state
            $button.addClass('loading').text('Generating...');
            
            // Trigger download
            window.location.href = $(this).attr('href');
            
            // Reset button after delay
            setTimeout(function() {
                $button.removeClass('loading').text('Export as ' + format.toUpperCase());
            }, 2000);
        },
        
        filterMilestones: function() {
            var selectedMilestone = $(this).val();
            
            if (selectedMilestone) {
                $('.milestone-card').hide();
                $('.milestone-card[data-milestone="' + selectedMilestone + '"]').show();
            } else {
                $('.milestone-card').show();
            }
        },
        
        refreshProgress: function(e) {
            e.preventDefault();
            var $button = $(this);
            
            $button.addClass('spinning');
            
            $.ajax({
                url: '/learning/api/refresh-progress',
                method: 'POST',
                success: function() {
                    location.reload();
                },
                error: function() {
                    alert('Failed to refresh progress. Please try again.');
                },
                complete: function() {
                    $button.removeClass('spinning');
                }
            });
        },
        
        loadVelocityChart: function() {
            $.ajax({
                url: '/learning/api/velocity-data',
                success: function(data) {
                    // Render chart using Chart.js or similar
                    LearningRoadmap.renderVelocityChart(data);
                }
            });
        },
        
        loadScoreTrends: function() {
            $.ajax({
                url: '/learning/api/score-trends',
                success: function(data) {
                    LearningRoadmap.renderScoreTrends(data);
                }
            });
        },
        
        renderVelocityChart: function(data) {
            // Implementation would use a charting library
            console.log('Velocity data:', data);
        },
        
        renderScoreTrends: function(data) {
            // Implementation would use a charting library
            console.log('Score trends:', data);
        },
        
        // Utility function to format time
        formatTime: function(minutes) {
            var hours = Math.floor(minutes / 60);
            var mins = minutes % 60;
            return hours + 'h ' + mins + 'm';
        }
    };
    
    // Initialize on document ready
    $(document).ready(function() {
        LearningRoadmap.init();
    });
    
})(jQuery);