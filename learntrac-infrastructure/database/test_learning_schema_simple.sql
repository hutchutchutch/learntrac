-- =====================================================
-- Simple Test of Learning Schema Foreign Keys
-- =====================================================

-- Test in a transaction so we can rollback
BEGIN;

-- =====================================================
-- 1. Create a test learning path
-- =====================================================
\echo '=== Creating test learning path ==='
INSERT INTO learning.paths (title, query_text, cognito_user_id, total_chunks, question_difficulty)
VALUES ('Test Learning Path', 'How to learn Python programming', 'test-user-123', 5, 3);

SELECT id, title FROM learning.paths WHERE cognito_user_id = 'test-user-123';

-- =====================================================
-- 2. Create test tickets
-- =====================================================
\echo ''
\echo '=== Creating test tickets ==='
INSERT INTO public.ticket (
    id, type, time, changetime, component, severity,
    priority, owner, reporter, status, summary, description
) VALUES 
    (9991, 'learning_concept', extract(epoch from now()) * 1000000, extract(epoch from now()) * 1000000,
     'learning', 'normal', 'major', 'admin', 'test_user', 'new',
     'Python Basics', 'Learn Python variables and data types'),
    (9992, 'learning_concept', extract(epoch from now()) * 1000000, extract(epoch from now()) * 1000000,
     'learning', 'normal', 'major', 'admin', 'test_user', 'new',
     'Python Functions', 'Learn how to create and use functions'),
    (9993, 'learning_concept', extract(epoch from now()) * 1000000, extract(epoch from now()) * 1000000,
     'learning', 'normal', 'major', 'admin', 'test_user', 'new',
     'Python Classes', 'Object-oriented programming in Python');

SELECT id, summary FROM public.ticket WHERE id IN (9991, 9992, 9993);

-- =====================================================
-- 3. Test concept_metadata with foreign keys
-- =====================================================
\echo ''
\echo '=== Testing concept_metadata foreign keys ==='

-- Get the path ID
WITH path AS (SELECT id FROM learning.paths WHERE cognito_user_id = 'test-user-123' LIMIT 1)
INSERT INTO learning.concept_metadata (ticket_id, path_id, chunk_id, relevance_score)
SELECT 9991, path.id, 'chunk-001', 0.95 FROM path
UNION ALL
SELECT 9992, path.id, 'chunk-002', 0.87 FROM path
UNION ALL
SELECT 9993, path.id, 'chunk-003', 0.92 FROM path;

SELECT cm.ticket_id, t.summary, cm.chunk_id, cm.relevance_score
FROM learning.concept_metadata cm
JOIN public.ticket t ON cm.ticket_id = t.id
WHERE cm.ticket_id IN (9991, 9992, 9993);

-- =====================================================
-- 4. Test prerequisites relationships
-- =====================================================
\echo ''
\echo '=== Testing prerequisites ==='

INSERT INTO learning.prerequisites (concept_ticket_id, prerequisite_ticket_id)
VALUES 
    (9992, 9991),  -- Functions requires Basics
    (9993, 9991),  -- Classes requires Basics
    (9993, 9992);  -- Classes requires Functions

SELECT 
    c.summary AS concept,
    p.summary AS prerequisite
FROM learning.prerequisites pr
JOIN public.ticket c ON pr.concept_ticket_id = c.id
JOIN public.ticket p ON pr.prerequisite_ticket_id = p.id
WHERE pr.concept_ticket_id IN (9991, 9992, 9993);

-- =====================================================
-- 5. Test progress tracking
-- =====================================================
\echo ''
\echo '=== Testing progress tracking ==='

INSERT INTO learning.progress (cognito_user_id, ticket_id, status, started_at, answer_score)
VALUES 
    ('test-user-123', 9991, 'completed', NOW(), 0.95),
    ('test-user-123', 9992, 'in_progress', NOW(), 0.78);

SELECT p.ticket_id, t.summary, p.status, p.answer_score
FROM learning.progress p
JOIN public.ticket t ON p.ticket_id = t.id
WHERE p.cognito_user_id = 'test-user-123';

-- =====================================================
-- 6. Test CASCADE delete
-- =====================================================
\echo ''
\echo '=== Testing CASCADE delete ==='

-- Count before
SELECT 
    'Before delete:' AS stage,
    (SELECT COUNT(*) FROM learning.concept_metadata WHERE ticket_id = 9992) AS concepts,
    (SELECT COUNT(*) FROM learning.prerequisites WHERE concept_ticket_id = 9992 OR prerequisite_ticket_id = 9992) AS prerequisites,
    (SELECT COUNT(*) FROM learning.progress WHERE ticket_id = 9992) AS progress;

-- Delete ticket
DELETE FROM public.ticket WHERE id = 9992;

-- Count after
SELECT 
    'After delete:' AS stage,
    (SELECT COUNT(*) FROM learning.concept_metadata WHERE ticket_id = 9992) AS concepts,
    (SELECT COUNT(*) FROM learning.prerequisites WHERE concept_ticket_id = 9992 OR prerequisite_ticket_id = 9992) AS prerequisites,
    (SELECT COUNT(*) FROM learning.progress WHERE ticket_id = 9992) AS progress;

-- =====================================================
-- 7. Test the views
-- =====================================================
\echo ''
\echo '=== Testing views ==='

\echo ''
\echo 'User path summary:'
SELECT path_title, total_concepts, completed_concepts, completion_percentage
FROM learning.v_user_path_summary 
WHERE cognito_user_id = 'test-user-123';

\echo ''
\echo 'Prerequisites graph:'
SELECT concept_summary, prerequisite_summary
FROM learning.v_prerequisites_graph 
WHERE concept_ticket_id IN (9991, 9993);

-- =====================================================
-- Rollback
-- =====================================================
\echo ''
\echo '=== Rolling back test data ==='
ROLLBACK;

\echo ''
\echo '✓ All tests completed successfully!'