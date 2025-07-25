# Claude Branch and PR Workflow Guide

This guide explains how Claude Code automatically creates branches and pull requests for every change, ensuring clean merge workflows and proper code review.

## Overview

When Claude is mentioned in GitHub issues or PR comments with `@claude`, the system:

1. **Creates a feature branch** automatically
2. **Makes requested changes** using Claude Flow hooks
3. **Commits changes** with descriptive messages
4. **Creates a pull request** for review
5. **Links everything** back to the original issue

## Key Components

### 1. GitHub Actions Workflow

The workflow (`claude-pr-auto-branch.yml`) triggers when:
- Someone mentions `@claude` in an issue
- Someone mentions `@claude` in a PR comment
- A new issue is opened with `@claude` in the body

### 2. Claude Flow Hooks

#### Pre-Branch Hook
```bash
npx claude-flow hook pre-branch --description "Task description"
```
- Creates semantically named branches
- Links to GitHub issues
- Stores branch metadata in memory

#### Pre-Edit Hook
```bash
npx claude-flow hook pre-edit --file "path/to/file"
```
- Validates before editing
- Assigns appropriate agents
- Checks for conflicts

#### Post-Edit Hook
```bash
npx claude-flow hook post-edit --file "path/to/file" --memory-key "edit/description"
```
- Tracks all changes
- Updates memory
- Prepares for commit

#### Auto-PR Hook
```bash
npx claude-flow hook auto-pr --branch [branch-name] --title "PR Title"
```
- Creates comprehensive PR
- Links to issues
- Assigns reviewers
- Adds labels

## Workflow Examples

### Example 1: Bug Fix Request

**Issue Comment:**
```markdown
@claude fix the login bug where users can't authenticate with email addresses containing special characters
```

**What Happens:**
1. GitHub Action triggers
2. Claude creates branch: `claude-feature/fix-login-special-chars-20240724-143022`
3. Claude analyzes the codebase
4. Uses pre-edit hooks before modifying files
5. Fixes the bug
6. Uses post-edit hooks to track changes
7. Commits: `fix(auth): handle special characters in email authentication`
8. Creates PR with full context
9. Comments on original issue with PR link

### Example 2: Feature Implementation

**Issue:**
```markdown
Title: Add dark mode support

@claude implement dark mode toggle in the settings page with system preference detection
```

**Workflow:**
1. Branch created: `claude-feature/dark-mode-settings-20240724-150130`
2. Claude spawns specialized agents:
   - UI agent for frontend changes
   - Settings agent for preference storage
   - Test agent for test coverage
3. Each agent uses coordination hooks
4. Multiple commits for logical changes
5. PR created with:
   - Implementation details
   - Test coverage report
   - Screenshots (if applicable)
   - Review checklist

## Configuration

### Settings (.claude/settings.json)

```json
{
  "env": {
    "CLAUDE_FLOW_AUTO_BRANCH": "true",
    "CLAUDE_FLOW_AUTO_PR": "true",
    "CLAUDE_FLOW_BRANCH_PREFIX": "claude-feature/",
    "CLAUDE_FLOW_REQUIRE_PR_REVIEW": "true"
  }
}
```

### CLAUDE.md Guidelines

The CLAUDE.md file now includes:
- Branch creation protocol
- Commit message format
- PR best practices
- Review requirements

## Best Practices

### 1. Clear Commands
```markdown
✅ Good: @claude add input validation to the user registration form
❌ Bad: @claude fix the form
```

### 2. Atomic PRs
- One feature/fix per PR
- Logical commit grouping
- Clear commit messages

### 3. Review Process
- All Claude PRs require review
- Reviewers automatically assigned
- CI/CD runs on all PRs

### 4. Memory Integration
- Branch metadata stored
- Change history tracked
- Learning from reviews

## Advanced Features

### Parallel Branch Creation

When multiple features are requested:
```markdown
@claude implement:
1. User profile page
2. Email notifications
3. API rate limiting
```

Claude can create multiple branches and PRs in parallel.

### Cross-PR Coordination

Claude tracks dependencies between PRs:
- Identifies conflicting changes
- Suggests merge order
- Updates dependent branches

### Auto-Merge Capability

For approved changes:
```bash
npx claude-flow hook auto-pr --auto-merge --required-checks "ci/build,ci/test"
```

## Troubleshooting

### PR Creation Failed
- Check GitHub token permissions
- Verify branch protection rules
- Ensure CI/CD is configured

### Merge Conflicts
- Claude detects conflicts early
- Suggests resolution strategies
- Can rebase automatically

### Hook Failures
- Check npm/npx availability
- Verify claude-flow installation
- Review hook permissions

## Security Considerations

1. **Branch Protection**: Main branch protected from direct commits
2. **Review Requirements**: All PRs require approval
3. **CI/CD Gates**: Tests must pass before merge
4. **Audit Trail**: All changes tracked and attributed

## Integration with Existing Workflows

### With JIRA
- Branch names can include JIRA ticket IDs
- PRs automatically linked to tickets

### With CI/CD
- Branches trigger appropriate pipelines
- PR checks enforced before merge

### With Code Owners
- CODEOWNERS file respected
- Appropriate reviewers auto-assigned

## Metrics and Monitoring

Claude Flow tracks:
- Time from request to PR
- Review turnaround time
- Merge success rate
- Code quality metrics

Access metrics:
```bash
npx claude-flow metrics --report branch-pr-workflow
```

## Future Enhancements

1. **Stacked PRs**: Support for dependent changes
2. **Conflict Resolution AI**: Automated merge conflict resolution
3. **Review Assistant**: AI-powered code review suggestions
4. **Performance Optimization**: Faster branch/PR creation

## Summary

The Claude branch and PR workflow ensures:
- ✅ No direct commits to main
- ✅ All changes go through review
- ✅ Full audit trail
- ✅ Consistent code quality
- ✅ Automated best practices

This workflow integrates seamlessly with Claude's swarm orchestration, memory system, and GitHub integration to provide a complete development automation solution.