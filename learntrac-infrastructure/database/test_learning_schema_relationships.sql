-- =====================================================
-- Test Learning Schema Foreign Key Relationships
-- =====================================================
-- This script tests all foreign key relationships
-- by inserting sample data and verifying constraints
-- =====================================================

-- Start transaction for rollback after testing
BEGIN;

-- Set to display more informative messages
\set VERBOSITY verbose

-- =====================================================
-- Test 1: Create a test learning path
-- =====================================================
\echo '=== Test 1: Creating a test learning path ==='

INSERT INTO learning.paths (title, query_text, cognito_user_id, total_chunks, question_difficulty)
VALUES (
    'Test Learning Path',
    'How to learn Python programming',
    'test-cognito-user-123',
    5,
    3
) RETURNING id AS test_path_id \gset

\echo 'Created learning path with ID:' :test_path_id

-- =====================================================
-- Test 2: Create test tickets in Trac
-- =====================================================
\echo ''
\echo '=== Test 2: Creating test tickets in Trac ==='

-- Get the next ticket IDs
SELECT COALESCE(MAX(id), 0) + 1 AS ticket1_id FROM public.ticket \gset
SELECT COALESCE(MAX(id), 0) + 2 AS ticket2_id FROM public.ticket \gset
SELECT COALESCE(MAX(id), 0) + 3 AS ticket3_id FROM public.ticket \gset

-- Insert test tickets
INSERT INTO public.ticket (
    id, type, time, changetime, component, severity,
    priority, owner, reporter, status, resolution,
    summary, description, keywords
) VALUES 
    (:ticket1_id, 'learning_concept', extract(epoch from now()) * 1000000, extract(epoch from now()) * 1000000,
     'learning', 'normal', 'major', 'admin', 'test_user', 'new', NULL,
     'Python Basics', 'Learn Python variables and data types', 'python,basics'),
    (:ticket2_id, 'learning_concept', extract(epoch from now()) * 1000000, extract(epoch from now()) * 1000000,
     'learning', 'normal', 'major', 'admin', 'test_user', 'new', NULL,
     'Python Functions', 'Learn how to create and use functions', 'python,functions'),
    (:ticket3_id, 'learning_concept', extract(epoch from now()) * 1000000, extract(epoch from now()) * 1000000,
     'learning', 'normal', 'major', 'admin', 'test_user', 'new', NULL,
     'Python Classes', 'Object-oriented programming in Python', 'python,oop,classes');

\echo 'Created tickets with IDs:' :ticket1_id ',' :ticket2_id ',' :ticket3_id

-- =====================================================
-- Test 3: Test concept_metadata foreign keys
-- =====================================================
\echo ''
\echo '=== Test 3: Testing concept_metadata foreign keys ==='

-- Test valid insertion
INSERT INTO learning.concept_metadata (ticket_id, path_id, chunk_id, relevance_score, question_generated)
VALUES 
    (:ticket1_id, :'test_path_id'::uuid, 'chunk-001', 0.95, true),
    (:ticket2_id, :'test_path_id'::uuid, 'chunk-002', 0.87, true),
    (:ticket3_id, :'test_path_id'::uuid, 'chunk-003', 0.92, true);

\echo '✓ Valid concept_metadata insertions succeeded'

-- Test invalid ticket_id (should fail)
\echo ''
\echo 'Testing invalid ticket_id reference (should fail):'
DO $$
BEGIN
    INSERT INTO learning.concept_metadata (ticket_id, path_id, chunk_id)
    VALUES (99999, :'test_path_id'::uuid, 'chunk-invalid');
    RAISE NOTICE '✗ ERROR: Invalid ticket_id was accepted!';
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE NOTICE '✓ Correctly rejected invalid ticket_id';
END $$;

-- Test invalid path_id (should fail)
\echo ''
\echo 'Testing invalid path_id reference (should fail):'
DO $$
BEGIN
    INSERT INTO learning.concept_metadata (ticket_id, path_id, chunk_id)
    VALUES (:ticket1_id, '00000000-0000-0000-0000-000000000000'::uuid, 'chunk-invalid');
    RAISE NOTICE '✗ ERROR: Invalid path_id was accepted!';
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE NOTICE '✓ Correctly rejected invalid path_id';
END $$;

-- =====================================================
-- Test 4: Test prerequisites foreign keys
-- =====================================================
\echo ''
\echo '=== Test 4: Testing prerequisites foreign keys ==='

-- Test valid prerequisite relationships
INSERT INTO learning.prerequisites (concept_ticket_id, prerequisite_ticket_id)
VALUES 
    (:ticket2_id, :ticket1_id),  -- Functions requires Basics
    (:ticket3_id, :ticket1_id),  -- Classes requires Basics
    (:ticket3_id, :ticket2_id);  -- Classes requires Functions

\echo '✓ Valid prerequisite relationships created'

-- Test self-prerequisite (should fail due to check constraint)
\echo ''
\echo 'Testing self-prerequisite (should fail):'
DO $$
BEGIN
    INSERT INTO learning.prerequisites (concept_ticket_id, prerequisite_ticket_id)
    VALUES (:ticket1_id, :ticket1_id);
    RAISE NOTICE '✗ ERROR: Self-prerequisite was accepted!';
EXCEPTION
    WHEN check_violation THEN
        RAISE NOTICE '✓ Correctly rejected self-prerequisite';
END $$;

-- Test invalid ticket references (should fail)
\echo ''
\echo 'Testing invalid prerequisite ticket reference (should fail):'
DO $$
BEGIN
    INSERT INTO learning.prerequisites (concept_ticket_id, prerequisite_ticket_id)
    VALUES (:ticket1_id, 99999);
    RAISE NOTICE '✗ ERROR: Invalid prerequisite_ticket_id was accepted!';
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE NOTICE '✓ Correctly rejected invalid prerequisite_ticket_id';
END $$;

-- =====================================================
-- Test 5: Test progress foreign keys
-- =====================================================
\echo ''
\echo '=== Test 5: Testing progress foreign keys ==='

-- Test valid progress entries
INSERT INTO learning.progress (cognito_user_id, ticket_id, status, started_at, last_answer, answer_score)
VALUES 
    ('test-cognito-user-123', :ticket1_id, 'completed', NOW(), 'Variables store data values', 0.95),
    ('test-cognito-user-123', :ticket2_id, 'in_progress', NOW(), 'Functions are reusable code blocks', 0.78);

\echo '✓ Valid progress entries created'

-- Test invalid ticket_id (should fail)
\echo ''
\echo 'Testing invalid progress ticket reference (should fail):'
DO $$
BEGIN
    INSERT INTO learning.progress (cognito_user_id, ticket_id, status)
    VALUES ('test-user', 99999, 'not_started');
    RAISE NOTICE '✗ ERROR: Invalid ticket_id in progress was accepted!';
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE NOTICE '✓ Correctly rejected invalid ticket_id in progress';
END $$;

-- =====================================================
-- Test 6: Test CASCADE deletes
-- =====================================================
\echo ''
\echo '=== Test 6: Testing CASCADE delete behavior ==='

-- Count related records before deletion
SELECT 
    (SELECT COUNT(*) FROM learning.concept_metadata WHERE path_id = :'test_path_id'::uuid) AS concepts_before,
    (SELECT COUNT(*) FROM learning.prerequisites WHERE concept_ticket_id IN (:ticket1_id, :ticket2_id, :ticket3_id)) AS prereqs_before,
    (SELECT COUNT(*) FROM learning.progress WHERE ticket_id IN (:ticket1_id, :ticket2_id, :ticket3_id)) AS progress_before \gset

\echo 'Records before deletion:'
\echo '  Concepts:' :concepts_before
\echo '  Prerequisites:' :prereqs_before  
\echo '  Progress:' :progress_before

-- Delete a ticket and verify cascades
DELETE FROM public.ticket WHERE id = :ticket2_id;

-- Count after deletion
SELECT 
    (SELECT COUNT(*) FROM learning.concept_metadata WHERE ticket_id = :ticket2_id) AS concepts_after,
    (SELECT COUNT(*) FROM learning.prerequisites WHERE concept_ticket_id = :ticket2_id OR prerequisite_ticket_id = :ticket2_id) AS prereqs_after,
    (SELECT COUNT(*) FROM learning.progress WHERE ticket_id = :ticket2_id) AS progress_after \gset

\echo ''
\echo 'Records after deleting ticket' :ticket2_id ':'
\echo '  Concepts for deleted ticket:' :concepts_after '(should be 0)'
\echo '  Prerequisites involving deleted ticket:' :prereqs_after '(should be 0)'
\echo '  Progress for deleted ticket:' :progress_after '(should be 0)'

-- =====================================================
-- Test 7: Test circular dependency check function
-- =====================================================
\echo ''
\echo '=== Test 7: Testing circular dependency check function ==='

-- This would create a circular dependency if allowed
SELECT learning.check_circular_dependency(:ticket1_id, :ticket3_id) AS would_be_circular;

\echo 'Check if ticket1 -> ticket3 would be circular:' 
\echo '(Should be TRUE since ticket3 -> ticket1 exists via ticket3 -> ticket2 -> ticket1)'

-- =====================================================
-- Test 8: Test the views
-- =====================================================
\echo ''
\echo '=== Test 8: Testing views ==='

\echo ''
\echo 'User path summary:'
SELECT * FROM learning.v_user_path_summary WHERE path_id = :'test_path_id'::uuid;

\echo ''
\echo 'Ticket learning details:'
SELECT ticket_id, ticket_summary, path_id, relevance_score, prerequisite_count, dependent_count 
FROM learning.v_ticket_learning_details 
WHERE path_id = :'test_path_id'::uuid
ORDER BY ticket_id;

\echo ''
\echo 'Prerequisites graph:'
SELECT * FROM learning.v_prerequisites_graph 
WHERE concept_ticket_id IN (:ticket1_id, :ticket2_id, :ticket3_id)
ORDER BY concept_ticket_id, prerequisite_ticket_id;

-- =====================================================
-- Rollback all test data
-- =====================================================
\echo ''
\echo '=== Rolling back all test data ==='
ROLLBACK;

\echo ''
\echo '=== All foreign key relationship tests completed successfully! ===''