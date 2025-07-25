-- Progress Tracking Schema Extensions for LearnTrac
-- This extends the existing learning schema with views and indexes for efficient progress tracking

-- Create indexes for better performance on progress queries
CREATE INDEX IF NOT EXISTS idx_learning_progress_user_status 
ON learning.learning_path_progress(cognito_user_id, status);

CREATE INDEX IF NOT EXISTS idx_learning_progress_milestone 
ON ticket(milestone) WHERE type = 'learning_concept';

CREATE INDEX IF NOT EXISTS idx_learning_progress_last_accessed 
ON learning.learning_path_progress(last_accessed DESC);

-- View for milestone-based progress summary
CREATE OR REPLACE VIEW learning.milestone_progress_summary AS
SELECT 
    m.name as milestone_name,
    m.due as milestone_due,
    u.cognito_user_id as user_id,
    COUNT(DISTINCT t.id) as total_concepts,
    COUNT(DISTINCT CASE WHEN lpp.status = 'completed' THEN t.id END) as completed,
    COUNT(DISTINCT CASE WHEN lpp.status = 'in_progress' THEN t.id END) as in_progress,
    COUNT(DISTINCT CASE WHEN lpp.status IS NULL OR lpp.status = 'not_started' THEN t.id END) as not_started,
    ROUND(AVG(lpp.score)::numeric, 2) as avg_score,
    SUM(EXTRACT(EPOCH FROM (lpp.last_accessed - lpp.first_accessed))/60) as total_time_minutes,
    MAX(lpp.last_accessed) as last_activity,
    CASE 
        WHEN COUNT(DISTINCT t.id) > 0 
        THEN ROUND((COUNT(DISTINCT CASE WHEN lpp.status = 'completed' THEN t.id END)::numeric / COUNT(DISTINCT t.id)::numeric) * 100, 2)
        ELSE 0 
    END as completion_percentage
FROM milestone m
CROSS JOIN (SELECT DISTINCT cognito_user_id FROM learning.learning_path_progress) u
LEFT JOIN ticket t ON t.milestone = m.name AND t.type = 'learning_concept'
LEFT JOIN learning.learning_path_progress lpp 
    ON EXISTS (
        SELECT 1 FROM learning.learning_paths lp 
        WHERE lp.id = lpp.path_id 
        AND lp.metadata->>'ticket_id' = t.id::text
    ) AND lpp.cognito_user_id = u.cognito_user_id
WHERE m.name IS NOT NULL
GROUP BY m.name, m.due, u.cognito_user_id;

-- View for overall user progress across all learning paths
CREATE OR REPLACE VIEW learning.user_progress_overview AS
SELECT 
    lpp.cognito_user_id as user_id,
    COUNT(DISTINCT lp.id) as total_paths,
    COUNT(DISTINCT CASE WHEN lpp.status = 'completed' THEN lp.id END) as completed_paths,
    COUNT(DISTINCT CASE WHEN lpp.status = 'in_progress' THEN lp.id END) as active_paths,
    ROUND(AVG(lpp.score)::numeric, 2) as overall_avg_score,
    SUM(EXTRACT(EPOCH FROM (lpp.last_accessed - lpp.first_accessed))/60) as total_learning_time_minutes,
    MIN(lpp.first_accessed) as learning_started,
    MAX(lpp.last_accessed) as last_learning_activity,
    COUNT(DISTINCT DATE(lpp.last_accessed)) as active_learning_days,
    CASE 
        WHEN COUNT(DISTINCT lp.id) > 0 
        THEN ROUND((COUNT(DISTINCT CASE WHEN lpp.status = 'completed' THEN lp.id END)::numeric / COUNT(DISTINCT lp.id)::numeric) * 100, 2)
        ELSE 0 
    END as overall_completion_percentage
FROM learning.learning_path_progress lpp
JOIN learning.learning_paths lp ON lpp.path_id = lp.id
GROUP BY lpp.cognito_user_id;

-- View for learning velocity (concepts learned per time period)
CREATE OR REPLACE VIEW learning.learning_velocity AS
SELECT 
    lpp.cognito_user_id as user_id,
    DATE_TRUNC('week', lpp.last_accessed) as week,
    COUNT(DISTINCT CASE WHEN lpp.status = 'completed' THEN lp.id END) as concepts_completed,
    ROUND(AVG(lpp.score)::numeric, 2) as avg_score_this_week,
    SUM(EXTRACT(EPOCH FROM (lpp.last_accessed - lpp.first_accessed))/60) as time_spent_minutes
FROM learning.learning_path_progress lpp
JOIN learning.learning_paths lp ON lpp.path_id = lp.id
WHERE lpp.last_accessed >= CURRENT_DATE - INTERVAL '12 weeks'
GROUP BY lpp.cognito_user_id, DATE_TRUNC('week', lpp.last_accessed);

-- View for cohort comparison
CREATE OR REPLACE VIEW learning.cohort_progress_comparison AS
WITH user_stats AS (
    SELECT 
        lpp.cognito_user_id,
        COUNT(DISTINCT CASE WHEN lpp.status = 'completed' THEN lp.id END) as completed_count,
        ROUND(AVG(lpp.score)::numeric, 2) as avg_score,
        SUM(EXTRACT(EPOCH FROM (lpp.last_accessed - lpp.first_accessed))/60) as total_time_minutes
    FROM learning.learning_path_progress lpp
    JOIN learning.learning_paths lp ON lpp.path_id = lp.id
    GROUP BY lpp.cognito_user_id
),
cohort_stats AS (
    SELECT 
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY completed_count) as median_completed,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_score) as median_score,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_time_minutes) as median_time,
        AVG(completed_count) as avg_completed,
        AVG(avg_score) as avg_cohort_score,
        AVG(total_time_minutes) as avg_time
    FROM user_stats
)
SELECT 
    us.cognito_user_id as user_id,
    us.completed_count,
    cs.median_completed as cohort_median_completed,
    us.avg_score,
    cs.median_score as cohort_median_score,
    us.total_time_minutes,
    cs.median_time as cohort_median_time,
    CASE 
        WHEN cs.median_completed > 0 
        THEN ROUND((us.completed_count::numeric / cs.median_completed::numeric) * 100, 2)
        ELSE 0 
    END as percentile_vs_cohort
FROM user_stats us
CROSS JOIN cohort_stats cs;

-- Function to calculate estimated completion date based on velocity
CREATE OR REPLACE FUNCTION learning.estimate_completion_date(
    p_user_id TEXT,
    p_milestone_name TEXT
) RETURNS DATE AS $$
DECLARE
    v_velocity NUMERIC;
    v_remaining INTEGER;
    v_estimated_days INTEGER;
BEGIN
    -- Calculate average concepts completed per week over last 4 weeks
    SELECT 
        AVG(concepts_completed) INTO v_velocity
    FROM learning.learning_velocity
    WHERE user_id = p_user_id
    AND week >= CURRENT_DATE - INTERVAL '4 weeks';
    
    -- Get remaining concepts
    SELECT 
        COUNT(DISTINCT t.id) INTO v_remaining
    FROM ticket t
    LEFT JOIN learning.learning_path_progress lpp 
        ON EXISTS (
            SELECT 1 FROM learning.learning_paths lp 
            WHERE lp.id = lpp.path_id 
            AND lp.metadata->>'ticket_id' = t.id::text
            AND lpp.cognito_user_id = p_user_id
        )
    WHERE t.milestone = p_milestone_name 
    AND t.type = 'learning_concept'
    AND (lpp.status IS NULL OR lpp.status != 'completed');
    
    -- Calculate estimated days
    IF v_velocity > 0 AND v_remaining > 0 THEN
        v_estimated_days := CEIL(v_remaining / (v_velocity / 7.0));
        RETURN CURRENT_DATE + v_estimated_days;
    ELSE
        RETURN NULL;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for performance on dashboard
CREATE MATERIALIZED VIEW IF NOT EXISTS learning.dashboard_progress_cache AS
SELECT 
    mps.user_id,
    mps.milestone_name,
    mps.total_concepts,
    mps.completed,
    mps.completion_percentage,
    mps.avg_score,
    mps.last_activity,
    learning.estimate_completion_date(mps.user_id, mps.milestone_name) as estimated_completion,
    cpc.percentile_vs_cohort
FROM learning.milestone_progress_summary mps
LEFT JOIN learning.cohort_progress_comparison cpc ON mps.user_id = cpc.user_id
WHERE mps.last_activity >= CURRENT_DATE - INTERVAL '6 months';

-- Create index on materialized view
CREATE INDEX idx_dashboard_cache_user_milestone 
ON learning.dashboard_progress_cache(user_id, milestone_name);

-- Function to refresh progress cache
CREATE OR REPLACE FUNCTION learning.refresh_progress_cache() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY learning.dashboard_progress_cache;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA learning TO learntrac_api;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA learning TO learntrac_api;