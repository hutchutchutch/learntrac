# Unnecessary Files and Folders to Clean Up

## 🗑️ Files and Folders That Can Be Safely Removed

### 1. Python Cache Files
These are automatically generated and should not be in version control:

```bash
# Python bytecode cache files
**/__pycache__/
**/*.pyc
**/*.pyo
**/*.pyd
```

**Found in:**
- `plugins/__pycache__/`
- `plugins/**/*.pyc`
- `learntrac-api/venv/` (entire virtual environment)

### 2. Virtual Environment
The entire virtual environment should not be in the repository:

```bash
learntrac-api/venv/
```

This folder contains 3rd-party dependencies that should be installed via `pip install -r requirements.txt`.

### 3. Build Artifacts
These are generated during package building:

```bash
# Plugin build directories
plugins/learntrac_display/build/
plugins/learntrac_display/dist/
plugins/cognitoauth/build/
plugins/cognitoauth/dist/
plugins/learningpathmacro/build/
plugins/learningpathmacro/dist/

# Egg info directories
**/*.egg-info/
**/*.egg

# Specific found artifacts
plugins/TracCognitoAuth-0.1-py3.9.egg
plugins/learntrac_display/dist/LearntracDisplay-0.1.0-py2.7.egg
```

### 4. Log Files and Test Results
These should not be tracked in version control:

```bash
# Log directories
logs/
log/

# Test results
api_tests/test_results/*.json
api_tests/test_results/*.log
api_tests/test_results/*.txt

# Specific log files
log/trac.log
```

### 5. OS-Specific Files
System-generated files:

```bash
# macOS
.DS_Store
**/.DS_Store

# Windows
Thumbs.db
desktop.ini

# Linux
*~
```

### 6. IDE and Editor Files
These are user-specific preferences:

```bash
# VS Code
.vscode/

# PyCharm
.idea/
*.iml

# Vim
*.swp
*.swo
*.swn
.*.swp
```

### 7. Temporary and Backup Files
```bash
# Backup files
*.backup
*.bak
*.tmp
*.temp
terraform.tfstate.backup

# Terraform state files (should use remote state)
terraform.tfstate
```

### 8. Potentially Redundant Files

#### Claude Flow Files (if not using)
```bash
claude-flow
claude-flow.bat
claude-flow.ps1
claude-flow.config.json
coordination/
memory/
```

#### Duplicate or Test Containers
```bash
test-containers/     # If covered by main docker setup
trac-legacy/        # If not needed for reference
```

#### Empty Directories
```bash
htdocs/             # Empty directory
logs/api/           # Empty log directories
logs/trac/
```

### 9. Generated Documentation Files
These appear to be auto-generated and can be regenerated:

```bash
# Task Master files (if using Task Master)
.taskmaster/tasks/*.md    # Auto-generated from tasks.json
```

### 10. Archive/Old Files
```bash
docs/archive/       # If these are truly archived and not needed
```

## 🧹 Cleanup Commands

### Option 1: Add to .gitignore and Remove from Tracking

First, update your `.gitignore` file to include these patterns, then run:

```bash
# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# Remove virtual environment
rm -rf learntrac-api/venv/

# Remove build artifacts
rm -rf plugins/*/build/ plugins/*/dist/ plugins/*/*.egg-info/
rm -f plugins/*.egg

# Remove logs and test results
rm -rf logs/ log/
rm -rf api_tests/test_results/

# Remove OS files
find . -name ".DS_Store" -delete

# Remove from git tracking but keep locally
git rm -r --cached learntrac-api/venv/
git rm -r --cached "**/__pycache__"
git rm -r --cached "**/*.pyc"
git rm --cached **/.DS_Store
```

### Option 2: Complete Cleanup Script

Create a `cleanup.sh` script:

```bash
#!/bin/bash

echo "Cleaning up unnecessary files..."

# Python artifacts
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.pyd" -delete

# Virtual environments
rm -rf learntrac-api/venv/
rm -rf venv/
rm -rf env/

# Build artifacts
rm -rf plugins/*/build/
rm -rf plugins/*/dist/
rm -rf plugins/*/*.egg-info/
rm -f plugins/*.egg

# Logs and test results
rm -rf logs/
rm -rf log/
rm -rf api_tests/test_results/

# OS-specific files
find . -name ".DS_Store" -delete
find . -name "Thumbs.db" -delete
find . -name "*~" -delete

# IDE files
rm -rf .vscode/
rm -rf .idea/
find . -name "*.swp" -delete

# Backup files
find . -name "*.bak" -delete
find . -name "*.backup" -delete

echo "Cleanup complete!"
```

## 📋 Recommended .gitignore

Add these patterns to your `.gitignore` file:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
*.egg-info/
*.egg
dist/
build/

# Logs
logs/
log/
*.log

# Test results
test_results/
*.test.json

# OS
.DS_Store
Thumbs.db
*~

# IDE
.vscode/
.idea/
*.swp
*.swo

# Terraform
*.tfstate
*.tfstate.*
.terraform/

# Project specific
claude-flow.config.json
memory/
coordination/
api_tests/test_results/
```

## 💡 Space Savings Estimate

Removing these unnecessary files will likely free up:
- **Virtual environment**: ~200-500 MB
- **Python cache**: ~10-50 MB  
- **Build artifacts**: ~5-20 MB
- **Logs and test results**: ~1-10 MB
- **Total**: ~216-580 MB

This will also make your repository cleaner, faster to clone, and easier to manage.