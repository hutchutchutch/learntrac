# -*- coding: utf-8 -*-
"""
TracLearn Database Schema Definitions
Supports SQLite, PostgreSQL, and MySQL
"""

from __future__ import absolute_import, print_function, unicode_literals

# SQLite schema (default for Trac)
sqlite_schema = [
    """CREATE TABLE IF NOT EXISTS traclearn_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_code VARCHAR(20) NOT NULL UNIQUE,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        instructor VARCHAR(100),
        start_date DATE,
        end_date DATE,
        max_students INTEGER DEFAULT 50,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        student_username VARCHAR(100) NOT NULL,
        enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) DEFAULT 'enrolled',
        grade VARCHAR(10),
        completion_date TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES traclearn_courses(id),
        UNIQUE(course_id, student_username)
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER NOT NULL,
        ticket_id INTEGER NOT NULL,
        progress_type VARCHAR(50) NOT NULL,
        progress_value FLOAT DEFAULT 0,
        details TEXT,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (enrollment_id) REFERENCES traclearn_enrollments(id)
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title VARCHAR(200) NOT NULL,
        assessment_type VARCHAR(50) NOT NULL,
        description TEXT,
        max_score FLOAT DEFAULT 100,
        weight FLOAT DEFAULT 1.0,
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES traclearn_courses(id)
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL,
        enrollment_id INTEGER NOT NULL,
        ticket_id INTEGER,
        submission_text TEXT,
        submission_file VARCHAR(255),
        score FLOAT,
        feedback TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        graded_at TIMESTAMP,
        graded_by VARCHAR(100),
        FOREIGN KEY (assessment_id) REFERENCES traclearn_assessments(id),
        FOREIGN KEY (enrollment_id) REFERENCES traclearn_enrollments(id)
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analytics_type VARCHAR(50) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id INTEGER NOT NULL,
        metric_name VARCHAR(100) NOT NULL,
        metric_value FLOAT,
        metadata TEXT,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_analytics_entity (entity_type, entity_id),
        INDEX idx_analytics_time (calculated_at)
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_ai_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insight_type VARCHAR(50) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id INTEGER NOT NULL,
        insight_text TEXT NOT NULL,
        confidence_score FLOAT,
        action_recommended TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        applied BOOLEAN DEFAULT 0
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_learning_paths (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path_name VARCHAR(200) NOT NULL,
        description TEXT,
        prerequisites TEXT,
        learning_objectives TEXT,
        estimated_hours INTEGER,
        difficulty_level VARCHAR(20),
        created_by VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_path_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        sequence_order INTEGER NOT NULL,
        is_required BOOLEAN DEFAULT 1,
        FOREIGN KEY (path_id) REFERENCES traclearn_learning_paths(id),
        FOREIGN KEY (course_id) REFERENCES traclearn_courses(id),
        UNIQUE(path_id, course_id)
    )""",
    
    # Indexes for performance
    """CREATE INDEX IF NOT EXISTS idx_enrollments_student 
       ON traclearn_enrollments(student_username)""",
    
    """CREATE INDEX IF NOT EXISTS idx_progress_enrollment 
       ON traclearn_progress(enrollment_id)""",
    
    """CREATE INDEX IF NOT EXISTS idx_submissions_assessment 
       ON traclearn_submissions(assessment_id)""",
    
    """CREATE INDEX IF NOT EXISTS idx_ai_insights_entity 
       ON traclearn_ai_insights(entity_type, entity_id)"""
]

# PostgreSQL schema
postgres_schema = [
    """CREATE TABLE IF NOT EXISTS traclearn_courses (
        id SERIAL PRIMARY KEY,
        course_code VARCHAR(20) NOT NULL UNIQUE,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        instructor VARCHAR(100),
        start_date DATE,
        end_date DATE,
        max_students INTEGER DEFAULT 50,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_enrollments (
        id SERIAL PRIMARY KEY,
        course_id INTEGER NOT NULL REFERENCES traclearn_courses(id),
        student_username VARCHAR(100) NOT NULL,
        enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) DEFAULT 'enrolled',
        grade VARCHAR(10),
        completion_date TIMESTAMP,
        UNIQUE(course_id, student_username)
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_progress (
        id SERIAL PRIMARY KEY,
        enrollment_id INTEGER NOT NULL REFERENCES traclearn_enrollments(id),
        ticket_id INTEGER NOT NULL,
        progress_type VARCHAR(50) NOT NULL,
        progress_value FLOAT DEFAULT 0,
        details JSONB,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_assessments (
        id SERIAL PRIMARY KEY,
        course_id INTEGER NOT NULL REFERENCES traclearn_courses(id),
        title VARCHAR(200) NOT NULL,
        assessment_type VARCHAR(50) NOT NULL,
        description TEXT,
        max_score FLOAT DEFAULT 100,
        weight FLOAT DEFAULT 1.0,
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_submissions (
        id SERIAL PRIMARY KEY,
        assessment_id INTEGER NOT NULL REFERENCES traclearn_assessments(id),
        enrollment_id INTEGER NOT NULL REFERENCES traclearn_enrollments(id),
        ticket_id INTEGER,
        submission_text TEXT,
        submission_file VARCHAR(255),
        score FLOAT,
        feedback TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        graded_at TIMESTAMP,
        graded_by VARCHAR(100)
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_analytics (
        id SERIAL PRIMARY KEY,
        analytics_type VARCHAR(50) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id INTEGER NOT NULL,
        metric_name VARCHAR(100) NOT NULL,
        metric_value FLOAT,
        metadata JSONB,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_ai_insights (
        id SERIAL PRIMARY KEY,
        insight_type VARCHAR(50) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id INTEGER NOT NULL,
        insight_text TEXT NOT NULL,
        confidence_score FLOAT,
        action_recommended TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        applied BOOLEAN DEFAULT FALSE
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_learning_paths (
        id SERIAL PRIMARY KEY,
        path_name VARCHAR(200) NOT NULL,
        description TEXT,
        prerequisites JSONB,
        learning_objectives JSONB,
        estimated_hours INTEGER,
        difficulty_level VARCHAR(20),
        created_by VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_path_courses (
        id SERIAL PRIMARY KEY,
        path_id INTEGER NOT NULL REFERENCES traclearn_learning_paths(id),
        course_id INTEGER NOT NULL REFERENCES traclearn_courses(id),
        sequence_order INTEGER NOT NULL,
        is_required BOOLEAN DEFAULT TRUE,
        UNIQUE(path_id, course_id)
    )""",
    
    # PostgreSQL specific indexes
    """CREATE INDEX IF NOT EXISTS idx_enrollments_student 
       ON traclearn_enrollments(student_username)""",
    
    """CREATE INDEX IF NOT EXISTS idx_progress_enrollment 
       ON traclearn_progress(enrollment_id)""",
    
    """CREATE INDEX IF NOT EXISTS idx_submissions_assessment 
       ON traclearn_submissions(assessment_id)""",
    
    """CREATE INDEX IF NOT EXISTS idx_analytics_entity 
       ON traclearn_analytics(entity_type, entity_id)""",
    
    """CREATE INDEX IF NOT EXISTS idx_analytics_time 
       ON traclearn_analytics(calculated_at)""",
    
    """CREATE INDEX IF NOT EXISTS idx_ai_insights_entity 
       ON traclearn_ai_insights(entity_type, entity_id)""",
    
    # PostgreSQL trigger for updated_at
    """CREATE OR REPLACE FUNCTION update_updated_at_column()
       RETURNS TRIGGER AS $$
       BEGIN
           NEW.updated_at = NOW();
           RETURN NEW;
       END;
       $$ language 'plpgsql'""",
    
    """CREATE TRIGGER update_traclearn_courses_updated_at 
       BEFORE UPDATE ON traclearn_courses 
       FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"""
]

# MySQL schema
mysql_schema = [
    """CREATE TABLE IF NOT EXISTS traclearn_courses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        course_code VARCHAR(20) NOT NULL UNIQUE,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        instructor VARCHAR(100),
        start_date DATE,
        end_date DATE,
        max_students INT DEFAULT 50,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_enrollments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        course_id INT NOT NULL,
        student_username VARCHAR(100) NOT NULL,
        enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) DEFAULT 'enrolled',
        grade VARCHAR(10),
        completion_date TIMESTAMP NULL,
        FOREIGN KEY (course_id) REFERENCES traclearn_courses(id),
        UNIQUE KEY unique_enrollment (course_id, student_username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_progress (
        id INT AUTO_INCREMENT PRIMARY KEY,
        enrollment_id INT NOT NULL,
        ticket_id INT NOT NULL,
        progress_type VARCHAR(50) NOT NULL,
        progress_value FLOAT DEFAULT 0,
        details JSON,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (enrollment_id) REFERENCES traclearn_enrollments(id),
        INDEX idx_enrollment (enrollment_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_assessments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        course_id INT NOT NULL,
        title VARCHAR(200) NOT NULL,
        assessment_type VARCHAR(50) NOT NULL,
        description TEXT,
        max_score FLOAT DEFAULT 100,
        weight FLOAT DEFAULT 1.0,
        due_date TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES traclearn_courses(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_submissions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        assessment_id INT NOT NULL,
        enrollment_id INT NOT NULL,
        ticket_id INT,
        submission_text TEXT,
        submission_file VARCHAR(255),
        score FLOAT,
        feedback TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        graded_at TIMESTAMP NULL,
        graded_by VARCHAR(100),
        FOREIGN KEY (assessment_id) REFERENCES traclearn_assessments(id),
        FOREIGN KEY (enrollment_id) REFERENCES traclearn_enrollments(id),
        INDEX idx_assessment (assessment_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_analytics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        analytics_type VARCHAR(50) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id INT NOT NULL,
        metric_name VARCHAR(100) NOT NULL,
        metric_value FLOAT,
        metadata JSON,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_entity (entity_type, entity_id),
        INDEX idx_time (calculated_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_ai_insights (
        id INT AUTO_INCREMENT PRIMARY KEY,
        insight_type VARCHAR(50) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id INT NOT NULL,
        insight_text TEXT NOT NULL,
        confidence_score FLOAT,
        action_recommended TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NULL,
        applied BOOLEAN DEFAULT FALSE,
        INDEX idx_entity (entity_type, entity_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_learning_paths (
        id INT AUTO_INCREMENT PRIMARY KEY,
        path_name VARCHAR(200) NOT NULL,
        description TEXT,
        prerequisites JSON,
        learning_objectives JSON,
        estimated_hours INT,
        difficulty_level VARCHAR(20),
        created_by VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    """CREATE TABLE IF NOT EXISTS traclearn_path_courses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        path_id INT NOT NULL,
        course_id INT NOT NULL,
        sequence_order INT NOT NULL,
        is_required BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (path_id) REFERENCES traclearn_learning_paths(id),
        FOREIGN KEY (course_id) REFERENCES traclearn_courses(id),
        UNIQUE KEY unique_path_course (path_id, course_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
]

def get_schema(db_type):
    """Get schema for specific database type"""
    schemas = {
        'sqlite': sqlite_schema,
        'postgres': postgres_schema,
        'postgresql': postgres_schema,
        'mysql': mysql_schema,
    }
    return schemas.get(db_type.lower(), sqlite_schema)