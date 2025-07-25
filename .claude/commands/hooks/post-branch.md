# hook post-branch

Configure and prepare a newly created branch for development.

## Usage

```bash
npx claude-flow hook post-branch [options]
```

## Options

- `--branch, -b <name>` - Branch name to configure
- `--setup-pr` - Prepare draft PR (default: true)
- `--protect` - Enable branch protection
- `--notify-team` - Send team notifications
- `--init-ci` - Initialize CI/CD configuration

## Examples

### Basic post-branch setup

```bash
npx claude-flow hook post-branch --branch feature/new-auth
```

### With PR preparation

```bash
npx claude-flow hook post-branch -b feature/api-v2 --setup-pr
```

### Full setup with protection

```bash
npx claude-flow hook post-branch -b main-feature --protect --notify-team
```

## Features

### Draft PR Creation

- Creates draft pull request
- Adds PR template
- Sets reviewers
- Links to issues

### Branch Configuration

- Sets upstream tracking
- Configures push rules
- Enables CI/CD
- Sets merge strategy

### Team Coordination

- Notifies relevant team members
- Updates project boards
- Creates tracking issues
- Schedules reviews

### Memory Storage

- Saves branch configuration
- Tracks PR associations
- Stores team assignments
- Maintains activity log

## Integration

This hook is automatically called:

- After creating new branches
- When setting up features
- During workflow initialization
- After branch switching

Manual usage:

```bash
# Setup newly created branch
npx claude-flow hook post-branch --branch feature/oauth --setup-pr

# Configure protection
npx claude-flow hook post-branch -b release/v2.0 --protect
```

## Output

Returns JSON with:

```json
{
  "success": true,
  "branch": "feature/new-auth",
  "prNumber": 456,
  "prUrl": "https://github.com/owner/repo/pull/456",
  "protected": false,
  "upstream": "origin/feature/new-auth",
  "notifications": ["team-lead", "qa-team"]
}
```

## See Also

- `hook pre-branch` - Branch creation
- `hook pre-pr` - PR preparation
- `gh pr create` - GitHub CLI PR creation