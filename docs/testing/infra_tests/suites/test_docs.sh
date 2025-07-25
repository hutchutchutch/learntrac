#!/bin/bash
# Test Suite: Documentation and Configuration Validation
# Validates subtask 1.10 (Documentation)

set -euo pipefail

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"
source "$SCRIPT_DIR/../utils/common.sh"

# Test Functions

test_infrastructure_readme() {
    local readme_path="$TF_DIR/README.md"
    
    if [ -f "$readme_path" ]; then
        log_success "README.md exists in infrastructure directory"
        
        # Check file size (should have substantial content)
        local file_size=$(stat -f%z "$readme_path" 2>/dev/null || stat -c%s "$readme_path" 2>/dev/null)
        
        if [ "$file_size" -gt 1000 ]; then
            log_success "README.md has substantial content ($file_size bytes)"
        else
            log_warning "README.md seems too small ($file_size bytes)"
        fi
        
        # Check for key sections
        local required_sections=(
            "Architecture"
            "Setup"
            "Configuration"
            "Deployment"
            "Troubleshooting"
        )
        
        for section in "${required_sections[@]}"; do
            if grep -qi "$section" "$readme_path"; then
                log_success "Found section: $section"
            else
                log_warning "Missing section: $section"
            fi
        done
        
        return 0
    else
        log_error "README.md not found in infrastructure directory"
        return 1
    fi
}

test_terraform_outputs_documented() {
    if [ -f "$TF_DIR/outputs.tf" ]; then
        log_info "Checking Terraform outputs..."
        
        # Count outputs
        local output_count=$(grep -c "output \"" "$TF_DIR/outputs.tf" 2>/dev/null || echo "0")
        
        if [ "$output_count" -gt 0 ]; then
            log_success "Found $output_count Terraform outputs defined"
            
            # Check if outputs have descriptions
            local outputs_with_desc=$(grep -B2 "description" "$TF_DIR/outputs.tf" | grep "output \"" | wc -l)
            
            if [ "$outputs_with_desc" -eq "$output_count" ]; then
                log_success "All outputs have descriptions"
            else
                log_warning "Some outputs lack descriptions"
            fi
        else
            log_warning "No Terraform outputs defined"
        fi
        
        return 0
    else
        log_warning "outputs.tf not found"
        return 0
    fi
}

test_variables_documented() {
    if [ -f "$TF_DIR/variables.tf" ]; then
        log_info "Checking Terraform variables..."
        
        # Count variables
        local var_count=$(grep -c "variable \"" "$TF_DIR/variables.tf" 2>/dev/null || echo "0")
        
        if [ "$var_count" -gt 0 ]; then
            log_success "Found $var_count Terraform variables defined"
            
            # Check if variables have descriptions
            local vars_with_desc=$(grep -B2 "description" "$TF_DIR/variables.tf" | grep "variable \"" | wc -l)
            
            if [ "$vars_with_desc" -eq "$var_count" ]; then
                log_success "All variables have descriptions"
            else
                log_warning "Some variables lack descriptions ($vars_with_desc/$var_count have descriptions)"
            fi
        else
            log_warning "No Terraform variables defined"
        fi
        
        return 0
    else
        log_warning "variables.tf not found"
        return 0
    fi
}

test_example_tfvars() {
    local example_files=(
        "$TF_DIR/terraform.tfvars.example"
        "$TF_DIR/example.tfvars"
        "$TF_DIR/terraform.tfvars.template"
    )
    
    local found_example=false
    for example_file in "${example_files[@]}"; do
        if [ -f "$example_file" ]; then
            log_success "Found example variables file: $(basename "$example_file")"
            found_example=true
            
            # Check if it contains all required variables
            if [ -f "$TF_DIR/variables.tf" ]; then
                local missing_vars=0
                while IFS= read -r var_name; do
                    if ! grep -q "$var_name" "$example_file"; then
                        log_warning "Example file missing variable: $var_name"
                        missing_vars=$((missing_vars + 1))
                    fi
                done < <(grep "variable \"" "$TF_DIR/variables.tf" | sed 's/variable "\([^"]*\)".*/\1/')
                
                if [ "$missing_vars" -eq 0 ]; then
                    log_success "Example file contains all variables"
                fi
            fi
            
            break
        fi
    done
    
    if [ "$found_example" = false ]; then
        log_warning "No example terraform.tfvars file found"
    fi
    
    return 0
}

test_architecture_diagram() {
    local diagram_files=(
        "$TF_DIR/architecture.png"
        "$TF_DIR/architecture.jpg"
        "$TF_DIR/architecture.svg"
        "$TF_DIR/docs/architecture.png"
        "$TF_DIR/docs/architecture.jpg"
        "$TF_DIR/docs/architecture.svg"
        "$TF_DIR/ARCHITECTURE_DIAGRAM.md"
    )
    
    local found_diagram=false
    for diagram_file in "${diagram_files[@]}"; do
        if [ -f "$diagram_file" ]; then
            log_success "Found architecture diagram: $(basename "$diagram_file")"
            found_diagram=true
            
            # Check file size
            local file_size=$(stat -f%z "$diagram_file" 2>/dev/null || stat -c%s "$diagram_file" 2>/dev/null)
            if [ "$file_size" -gt 1000 ]; then
                log_success "Diagram has reasonable size ($file_size bytes)"
            fi
            
            break
        fi
    done
    
    if [ "$found_diagram" = false ]; then
        log_warning "No architecture diagram found"
    fi
    
    return 0
}

test_runbook_exists() {
    local runbook_files=(
        "$TF_DIR/RUNBOOK.md"
        "$TF_DIR/docs/RUNBOOK.md"
        "$TF_DIR/OPERATIONS.md"
        "$TF_DIR/docs/OPERATIONS.md"
    )
    
    local found_runbook=false
    for runbook_file in "${runbook_files[@]}"; do
        if [ -f "$runbook_file" ]; then
            log_success "Found runbook: $(basename "$runbook_file")"
            found_runbook=true
            
            # Check for disaster recovery procedures
            if grep -qi "disaster\|recovery\|backup\|restore" "$runbook_file"; then
                log_success "Runbook contains disaster recovery procedures"
            else
                log_warning "Runbook missing disaster recovery procedures"
            fi
            
            break
        fi
    done
    
    if [ "$found_runbook" = false ]; then
        log_warning "No runbook/operations guide found"
    fi
    
    return 0
}

test_environment_documentation() {
    # Check for environment-specific documentation
    local env_docs=(
        "$TF_DIR/environments/"
        "$TF_DIR/docs/environments/"
    )
    
    local found_env_docs=false
    for env_dir in "${env_docs[@]}"; do
        if [ -d "$env_dir" ]; then
            log_success "Found environment documentation directory: $env_dir"
            found_env_docs=true
            
            # List environment docs
            local env_files=$(find "$env_dir" -name "*.md" -o -name "*.txt" 2>/dev/null | head -10)
            if [ -n "$env_files" ]; then
                log_info "Environment documentation files:"
                echo "$env_files" | while read -r file; do
                    log_info "  - $(basename "$file")"
                done
            fi
            
            break
        fi
    done
    
    if [ "$found_env_docs" = false ]; then
        log_info "No separate environment documentation directory (may be in main docs)"
    fi
    
    return 0
}

test_security_documentation() {
    local security_files=(
        "$TF_DIR/SECURITY.md"
        "$TF_DIR/docs/SECURITY.md"
        "$TF_DIR/SECURITY_README.md"
    )
    
    local found_security=false
    for security_file in "${security_files[@]}"; do
        if [ -f "$security_file" ]; then
            log_success "Found security documentation: $(basename "$security_file")"
            found_security=true
            
            # Check for key security topics
            local security_topics=(
                "encryption"
                "authentication"
                "authorization"
                "network"
                "compliance"
            )
            
            for topic in "${security_topics[@]}"; do
                if grep -qi "$topic" "$security_file"; then
                    log_success "Security docs cover: $topic"
                else
                    log_warning "Security docs missing: $topic"
                fi
            done
            
            break
        fi
    done
    
    if [ "$found_security" = false ]; then
        log_warning "No dedicated security documentation found"
    fi
    
    return 0
}

test_api_documentation() {
    local api_files=(
        "$TF_DIR/API.md"
        "$TF_DIR/docs/API.md"
        "$TF_DIR/API_REFERENCE.md"
        "docs/api/"
    )
    
    local found_api_docs=false
    for api_file in "${api_files[@]}"; do
        if [ -f "$api_file" ] || [ -d "$api_file" ]; then
            log_success "Found API documentation: $api_file"
            found_api_docs=true
            break
        fi
    done
    
    if [ "$found_api_docs" = false ]; then
        log_info "No separate API documentation (may be in main docs)"
    fi
    
    return 0
}

test_changelog_exists() {
    local changelog_files=(
        "$TF_DIR/CHANGELOG.md"
        "$TF_DIR/CHANGES.md"
        "$TF_DIR/HISTORY.md"
    )
    
    local found_changelog=false
    for changelog_file in "${changelog_files[@]}"; do
        if [ -f "$changelog_file" ]; then
            log_success "Found changelog: $(basename "$changelog_file")"
            found_changelog=true
            
            # Check if it has recent entries
            local last_modified=$(stat -f%m "$changelog_file" 2>/dev/null || stat -c%Y "$changelog_file" 2>/dev/null)
            local current_time=$(date +%s)
            local days_old=$(( (current_time - last_modified) / 86400 ))
            
            if [ "$days_old" -lt 90 ]; then
                log_success "Changelog updated within last 90 days"
            else
                log_warning "Changelog not updated for $days_old days"
            fi
            
            break
        fi
    done
    
    if [ "$found_changelog" = false ]; then
        log_info "No changelog found (optional)"
    fi
    
    return 0
}

# Main test execution
main() {
    log_info "Starting Documentation Tests..."
    echo "========================================="
    
    # Validate configuration
    if ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi
    
    # Check if Terraform directory exists
    if [ ! -d "$TF_DIR" ]; then
        log_error "Terraform directory not found: $TF_DIR"
        exit 1
    fi
    
    # Run tests
    run_test "Infrastructure README" test_infrastructure_readme
    run_test "Terraform outputs documented" test_terraform_outputs_documented
    run_test "Terraform variables documented" test_variables_documented
    run_test "Example tfvars file" test_example_tfvars
    run_test "Architecture diagram" test_architecture_diagram
    run_test "Runbook/operations guide" test_runbook_exists
    run_test "Environment documentation" test_environment_documentation
    run_test "Security documentation" test_security_documentation
    run_test "API documentation" test_api_documentation
    run_test "Changelog" test_changelog_exists
    
    # Print summary
    print_test_summary
}

# Execute main function
main "$@"