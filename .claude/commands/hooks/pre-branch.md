# hook pre-branch

Create and configure a new feature branch before making changes.

## Usage

```bash
npx claude-flow hook pre-branch [options]
```

## Options

- `--name, -n <branch-name>` - Custom branch name (default: auto-generated)
- `--from, -f <base-branch>` - Base branch to create from (default: main)
- `--prefix, -p <prefix>` - Branch prefix (default: feature/)
- `--issue, -i <issue-number>` - Link to GitHub issue
- `--description, -d <text>` - Branch description for memory

## Examples

### Auto-generated branch name

```bash
npx claude-flow hook pre-branch --description "Add user authentication"
```

### Custom branch name

```bash
npx claude-flow hook pre-branch --name "auth-jwt-implementation"
```

### Branch from specific base

```bash
npx claude-flow hook pre-branch --from develop --prefix bugfix/
```

### Link to issue

```bash
npx claude-flow hook pre-branch --issue 123 --description "Fix login bug"
```

## Features

### Automatic Branch Naming

- Generates semantic branch names
- Includes timestamp for uniqueness
- Follows git-flow conventions
- Sanitizes special characters

### Branch Protection

- Checks for uncommitted changes
- Verifies base branch is up-to-date
- Prevents duplicate branch names
- Validates branch permissions

### Memory Integration

- Stores branch metadata
- Links to parent branches
- Tracks creation context
- Maintains branch history

### Issue Linking

- Automatically links to GitHub issues
- Includes issue number in branch name
- Updates issue with branch info
- Tracks related PRs

## Integration

This hook should be called:

- Before starting new features
- When fixing bugs
- Before making breaking changes
- When experimenting with ideas

Manual usage:

```bash
# Create feature branch
npx claude-flow hook pre-branch --prefix feature/ --description "New feature"

# Create hotfix branch
npx claude-flow hook pre-branch --prefix hotfix/ --from production
```

## Output

Returns JSON with:

```json
{
  "success": true,
  "branchName": "feature/auth-jwt-20241224-123456",
  "baseBranch": "main",
  "created": "2024-12-24T12:34:56Z",
  "issue": 123,
  "memoryKey": "branch/feature/auth-jwt-20241224-123456"
}
```

## See Also

- `hook post-branch` - Post-branch setup
- `hook pre-edit` - Pre-edit validation
- `git checkout -b` - Git branch creation