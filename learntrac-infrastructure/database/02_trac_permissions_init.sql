-- Trac 1.4.4 Permissions Initialization Script
-- This script sets up default permissions and creates an admin user

SET search_path TO trac, public;

-- Default permissions for anonymous users
INSERT INTO permission (username, action) VALUES 
    ('anonymous', 'WIKI_VIEW'),
    ('anonymous', 'CHANGESET_VIEW'),
    ('anonymous', 'FILE_VIEW'),
    ('anonymous', 'LOG_VIEW'),
    ('anonymous', 'MILESTONE_VIEW'),
    ('anonymous', 'REPORT_VIEW'),
    ('anonymous', 'ROADMAP_VIEW'),
    ('anonymous', 'SEARCH_VIEW'),
    ('anonymous', 'TICKET_VIEW'),
    ('anonymous', 'TIMELINE_VIEW'),
    ('anonymous', 'BROWSER_VIEW')
ON CONFLICT (username, action) DO NOTHING;

-- Default permissions for authenticated users (inherit anonymous permissions)
INSERT INTO permission (username, action) VALUES 
    ('authenticated', 'TICKET_CREATE'),
    ('authenticated', 'TICKET_MODIFY'),
    ('authenticated', 'WIKI_CREATE'),
    ('authenticated', 'WIKI_MODIFY'),
    ('authenticated', 'TICKET_APPEND'),
    ('authenticated', 'TICKET_CHGPROP'),
    ('authenticated', 'REPORT_CREATE'),
    ('authenticated', 'REPORT_MODIFY'),
    ('authenticated', 'REPORT_SQL_VIEW')
ON CONFLICT (username, action) DO NOTHING;

-- Create admin user with all permissions
-- Note: The password should be changed after initial setup
INSERT INTO session (sid, authenticated, last_visit) VALUES 
    ('admin', 1, EXTRACT(EPOCH FROM NOW())::INTEGER)
ON CONFLICT (sid, authenticated) DO UPDATE 
    SET last_visit = EXCLUDED.last_visit;

-- Grant all permissions to admin
INSERT INTO permission (username, action) VALUES 
    ('admin', 'TRAC_ADMIN'),
    ('admin', 'PERMISSION_GRANT'),
    ('admin', 'PERMISSION_REVOKE'),
    ('admin', 'PERMISSION_ADMIN'),
    ('admin', 'TICKET_ADMIN'),
    ('admin', 'MILESTONE_ADMIN'),
    ('admin', 'COMPONENT_ADMIN'),
    ('admin', 'VERSION_ADMIN'),
    ('admin', 'PRIORITY_ADMIN'),
    ('admin', 'SEVERITY_ADMIN'),
    ('admin', 'RESOLUTION_ADMIN'),
    ('admin', 'TICKET_TYPE_ADMIN'),
    ('admin', 'REPORT_ADMIN'),
    ('admin', 'WIKI_ADMIN'),
    ('admin', 'CONFIG_VIEW'),
    ('admin', 'EMAIL_VIEW')
ON CONFLICT (username, action) DO NOTHING;

-- Additional standard permissions for admin
INSERT INTO permission (username, action) VALUES 
    ('admin', 'BROWSER_VIEW'),
    ('admin', 'CHANGESET_VIEW'),
    ('admin', 'FILE_VIEW'),
    ('admin', 'LOG_VIEW'),
    ('admin', 'MILESTONE_CREATE'),
    ('admin', 'MILESTONE_DELETE'),
    ('admin', 'MILESTONE_MODIFY'),
    ('admin', 'MILESTONE_VIEW'),
    ('admin', 'REPORT_CREATE'),
    ('admin', 'REPORT_DELETE'),
    ('admin', 'REPORT_MODIFY'),
    ('admin', 'REPORT_SQL_VIEW'),
    ('admin', 'REPORT_VIEW'),
    ('admin', 'ROADMAP_VIEW'),
    ('admin', 'SEARCH_VIEW'),
    ('admin', 'TICKET_APPEND'),
    ('admin', 'TICKET_CHGPROP'),
    ('admin', 'TICKET_CREATE'),
    ('admin', 'TICKET_EDIT_CC'),
    ('admin', 'TICKET_EDIT_COMMENT'),
    ('admin', 'TICKET_EDIT_DESCRIPTION'),
    ('admin', 'TICKET_MODIFY'),
    ('admin', 'TICKET_VIEW'),
    ('admin', 'TIMELINE_VIEW'),
    ('admin', 'WIKI_CREATE'),
    ('admin', 'WIKI_DELETE'),
    ('admin', 'WIKI_MODIFY'),
    ('admin', 'WIKI_RENAME'),
    ('admin', 'WIKI_VIEW')
ON CONFLICT (username, action) DO NOTHING;

-- Create developer role permissions
INSERT INTO permission (username, action) VALUES 
    ('developer', 'BROWSER_VIEW'),
    ('developer', 'CHANGESET_VIEW'),
    ('developer', 'FILE_VIEW'),
    ('developer', 'LOG_VIEW'),
    ('developer', 'MILESTONE_VIEW'),
    ('developer', 'REPORT_CREATE'),
    ('developer', 'REPORT_MODIFY'),
    ('developer', 'REPORT_SQL_VIEW'),
    ('developer', 'REPORT_VIEW'),
    ('developer', 'ROADMAP_VIEW'),
    ('developer', 'SEARCH_VIEW'),
    ('developer', 'TICKET_APPEND'),
    ('developer', 'TICKET_CHGPROP'),
    ('developer', 'TICKET_CREATE'),
    ('developer', 'TICKET_EDIT_CC'),
    ('developer', 'TICKET_MODIFY'),
    ('developer', 'TICKET_VIEW'),
    ('developer', 'TIMELINE_VIEW'),
    ('developer', 'WIKI_CREATE'),
    ('developer', 'WIKI_MODIFY'),
    ('developer', 'WIKI_VIEW')
ON CONFLICT (username, action) DO NOTHING;

-- Create default wiki pages
INSERT INTO wiki (name, version, time, author, ipnr, text, comment, readonly) VALUES 
    ('WikiStart', 1, EXTRACT(EPOCH FROM NOW())::BIGINT * 1000000, 'admin', '127.0.0.1', 
     '= Welcome to LearnTrac =

Welcome to the LearnTrac project management system powered by Trac 1.4.4.

== Getting Started ==

* TracGuide -- Built-in documentation
* [wiki:TracAdmin Trac Administration] -- Admin features
* [wiki:TracSupport Trac Support] -- Get help

== For Developers ==

* [wiki:TracDev Development Resources]
* [wiki:TracPlugins Plugin Development]

== Quick Links ==

* [/timeline Timeline] -- See recent changes
* [/roadmap Roadmap] -- View project milestones
* [/browser Browse Source] -- Browse the repository
* [/report Active Tickets] -- View active tickets
', 'Initial wiki page', 0),
    ('TracGuide', 1, EXTRACT(EPOCH FROM NOW())::BIGINT * 1000000, 'admin', '127.0.0.1',
     '= Trac User Guide =

The TracGuide is meant to serve as a starting point for all documentation regarding Trac usage.

== Table of Contents ==

* TracInstall -- How to install and run Trac
* TracAdmin -- Administering a Trac project
* TracBackup -- How to backup a Trac environment
* TracIni -- Trac configuration file reference
* TracPermissions -- Access control and permissions
* TracWiki -- Using the built-in Wiki
* TracBrowser -- Browsing the source code
* TracTimeline -- The timeline view
* TracTickets -- Using the ticket system
* TracReports -- Writing and using reports
* TracQuery -- Executing custom ticket queries
* TracRoadmap -- The project roadmap
* TracNotification -- Email notifications
', 'Trac guide page', 0)
ON CONFLICT (name, version) DO NOTHING;