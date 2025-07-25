-- Trac 1.4.4 Database Schema Initialization Script
-- This script creates all necessary tables for a fresh Trac installation
-- Target: PostgreSQL

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS trac;
SET search_path TO trac, public;

-- System table to track schema version
CREATE TABLE IF NOT EXISTS system (
    name TEXT NOT NULL PRIMARY KEY,
    value TEXT
);

-- Insert schema version
INSERT INTO system (name, value) VALUES ('database_version', '45')
ON CONFLICT (name) DO UPDATE SET value = EXCLUDED.value;

-- Component table
CREATE TABLE IF NOT EXISTS component (
    name TEXT NOT NULL PRIMARY KEY,
    owner TEXT,
    description TEXT
);

-- Enum table for ticket priorities, severities, etc.
CREATE TABLE IF NOT EXISTS enum (
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (type, name)
);

-- Milestone table
CREATE TABLE IF NOT EXISTS milestone (
    name TEXT NOT NULL PRIMARY KEY,
    due BIGINT,
    completed BIGINT,
    description TEXT,
    started BIGINT
);

-- Version table
CREATE TABLE IF NOT EXISTS version (
    name TEXT NOT NULL PRIMARY KEY,
    time BIGINT,
    description TEXT
);

-- Ticket table
CREATE TABLE IF NOT EXISTS ticket (
    id SERIAL PRIMARY KEY,
    type TEXT,
    time BIGINT,
    changetime BIGINT,
    component TEXT,
    severity TEXT,
    priority TEXT,
    owner TEXT,
    reporter TEXT,
    cc TEXT,
    version TEXT,
    milestone TEXT,
    status TEXT,
    resolution TEXT,
    summary TEXT,
    description TEXT,
    keywords TEXT
);

-- Ticket changes table
CREATE TABLE IF NOT EXISTS ticket_change (
    ticket INTEGER NOT NULL,
    time BIGINT NOT NULL,
    author TEXT,
    field TEXT NOT NULL,
    oldvalue TEXT,
    newvalue TEXT,
    PRIMARY KEY (ticket, time, field),
    FOREIGN KEY (ticket) REFERENCES ticket(id) ON DELETE CASCADE
);

-- Ticket custom fields
CREATE TABLE IF NOT EXISTS ticket_custom (
    ticket INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (ticket, name),
    FOREIGN KEY (ticket) REFERENCES ticket(id) ON DELETE CASCADE
);

-- Attachment table
CREATE TABLE IF NOT EXISTS attachment (
    type TEXT NOT NULL,
    id TEXT NOT NULL,
    filename TEXT NOT NULL,
    size INTEGER,
    time BIGINT,
    description TEXT,
    author TEXT,
    ipnr TEXT,
    PRIMARY KEY (type, id, filename)
);

-- Wiki table
CREATE TABLE IF NOT EXISTS wiki (
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    time BIGINT,
    author TEXT,
    ipnr TEXT,
    text TEXT,
    comment TEXT,
    readonly INTEGER,
    PRIMARY KEY (name, version)
);

-- Permission table
CREATE TABLE IF NOT EXISTS permission (
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    PRIMARY KEY (username, action)
);

-- Auth cookie table
CREATE TABLE IF NOT EXISTS auth_cookie (
    cookie TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    ipnr TEXT NOT NULL,
    time INTEGER
);

-- Session table
CREATE TABLE IF NOT EXISTS session (
    sid TEXT NOT NULL,
    authenticated INTEGER NOT NULL,
    last_visit INTEGER,
    PRIMARY KEY (sid, authenticated)
);

-- Session attributes table
CREATE TABLE IF NOT EXISTS session_attribute (
    sid TEXT NOT NULL,
    authenticated INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (sid, authenticated, name),
    FOREIGN KEY (sid, authenticated) REFERENCES session(sid, authenticated) ON DELETE CASCADE
);

-- Cache table
CREATE TABLE IF NOT EXISTS cache (
    id TEXT NOT NULL PRIMARY KEY,
    generation INTEGER
);

-- Node change table
CREATE TABLE IF NOT EXISTS node_change (
    id SERIAL PRIMARY KEY,
    repos INTEGER,
    rev TEXT,
    path TEXT,
    node_type TEXT,
    change_type TEXT,
    base_path TEXT,
    base_rev TEXT
);

-- Repository table
CREATE TABLE IF NOT EXISTS repository (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    value TEXT
);

-- Revision table
CREATE TABLE IF NOT EXISTS revision (
    repos INTEGER NOT NULL,
    rev TEXT NOT NULL,
    time BIGINT,
    author TEXT,
    message TEXT,
    PRIMARY KEY (repos, rev),
    FOREIGN KEY (repos) REFERENCES repository(id) ON DELETE CASCADE
);

-- Report table
CREATE TABLE IF NOT EXISTS report (
    id SERIAL PRIMARY KEY,
    author TEXT,
    title TEXT,
    query TEXT,
    description TEXT
);

-- Notify subscription table
CREATE TABLE IF NOT EXISTS notify_subscription (
    id SERIAL PRIMARY KEY,
    time BIGINT,
    changetime BIGINT,
    class TEXT,
    sid TEXT,
    authenticated INTEGER,
    distributor TEXT,
    format TEXT,
    priority INTEGER DEFAULT 1,
    adverb TEXT
);

-- Notify watch table
CREATE TABLE IF NOT EXISTS notify_watch (
    id SERIAL PRIMARY KEY,
    sid TEXT,
    authenticated INTEGER,
    class TEXT,
    realm TEXT,
    target TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS ticket_time_idx ON ticket(time);
CREATE INDEX IF NOT EXISTS ticket_changetime_idx ON ticket(changetime);
CREATE INDEX IF NOT EXISTS ticket_status_idx ON ticket(status);
CREATE INDEX IF NOT EXISTS ticket_owner_idx ON ticket(owner);
CREATE INDEX IF NOT EXISTS ticket_reporter_idx ON ticket(reporter);
CREATE INDEX IF NOT EXISTS ticket_milestone_idx ON ticket(milestone);
CREATE INDEX IF NOT EXISTS ticket_change_ticket_idx ON ticket_change(ticket);
CREATE INDEX IF NOT EXISTS ticket_change_time_idx ON ticket_change(time);
CREATE INDEX IF NOT EXISTS wiki_time_idx ON wiki(time);
CREATE INDEX IF NOT EXISTS session_last_visit_idx ON session(last_visit);
CREATE INDEX IF NOT EXISTS revision_repos_time_idx ON revision(repos, time);
CREATE INDEX IF NOT EXISTS node_change_repos_idx ON node_change(repos);
CREATE INDEX IF NOT EXISTS node_change_repos_rev_idx ON node_change(repos, rev);

-- Insert default enumerations
INSERT INTO enum (type, name, value) VALUES 
    ('priority', 'blocker', '1'),
    ('priority', 'critical', '2'),
    ('priority', 'major', '3'),
    ('priority', 'minor', '4'),
    ('priority', 'trivial', '5');

INSERT INTO enum (type, name, value) VALUES 
    ('resolution', 'fixed', '1'),
    ('resolution', 'invalid', '2'),
    ('resolution', 'wontfix', '3'),
    ('resolution', 'duplicate', '4'),
    ('resolution', 'worksforme', '5');

INSERT INTO enum (type, name, value) VALUES 
    ('severity', 'blocker', '1'),
    ('severity', 'critical', '2'),
    ('severity', 'major', '3'),
    ('severity', 'normal', '4'),
    ('severity', 'minor', '5'),
    ('severity', 'trivial', '6'),
    ('severity', 'enhancement', '7');

INSERT INTO enum (type, name, value) VALUES 
    ('ticket_type', 'defect', '1'),
    ('ticket_type', 'enhancement', '2'),
    ('ticket_type', 'task', '3');

-- Insert default milestone
INSERT INTO milestone (name, due, completed, description) VALUES 
    ('milestone1', NULL, NULL, 'Default milestone')
ON CONFLICT (name) DO NOTHING;

-- Insert default component
INSERT INTO component (name, owner, description) VALUES 
    ('component1', NULL, 'Default component')
ON CONFLICT (name) DO NOTHING;

-- Insert default version
INSERT INTO version (name, time, description) VALUES 
    ('1.0', NULL, 'Default version')
ON CONFLICT (name) DO NOTHING;

-- Create default reports
INSERT INTO report (id, author, title, query, description) VALUES 
(1, NULL, 'Active Tickets', '
SELECT p.value AS __color__,
   id AS ticket, summary, component, version, milestone,
   t.type AS type, owner, status,
   time AS created,
   changetime AS _changetime, description AS _description,
   reporter AS _reporter
FROM ticket t
LEFT JOIN enum p ON p.name = t.priority AND p.type = ''priority''
WHERE status <> ''closed''
ORDER BY CAST(p.value AS integer), milestone, t.type, time
', 'All active tickets by priority and milestone'),

(2, NULL, 'Active Tickets by Version', '
SELECT p.value AS __color__,
   version AS __group__,
   id AS ticket, summary, component, severity, milestone, t.type AS type,
   owner, status,
   time AS created,
   changetime AS _changetime, description AS _description,
   reporter AS _reporter
FROM ticket t
LEFT JOIN enum p ON p.name = t.priority AND p.type = ''priority''
WHERE status <> ''closed''
ORDER BY version, CAST(p.value AS integer), t.type, time
', 'Active tickets grouped by version')
ON CONFLICT (id) DO NOTHING;