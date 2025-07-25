# hook auto-pr

Automatically create pull requests with intelligent defaults and Claude integration.

## Usage

```bash
npx claude-flow hook auto-pr [options]
```

## Options

- `--branch, -b <name>` - Source branch (default: current)
- `--target, -t <branch>` - Target branch (default: main)
- `--title <text>` - PR title (auto-generated if not provided)
- `--draft` - Create as draft PR (default: false)
- `--reviewers, -r <users>` - Comma-separated reviewer list
- `--labels, -l <labels>` - Comma-separated label list
- `--auto-merge` - Enable auto-merge when checks pass

## Examples

### Basic PR creation

```bash
npx claude-flow hook auto-pr --branch feature/auth
```

### Draft PR with reviewers

```bash
npx claude-flow hook auto-pr -b feature/api --draft --reviewers "user1,user2"
```

### Auto-merge PR

```bash
npx claude-flow hook auto-pr --branch hotfix/security --auto-merge
```

### Full configuration

```bash
npx claude-flow hook auto-pr \
  --branch feature/payments \
  --target develop \
  --title "Add payment processing" \
  --reviewers "lead-dev,security-team" \
  --labels "enhancement,needs-review" \
  --draft
```

## Features

### Intelligent PR Creation

- Analyzes commits for title/description
- Generates comprehensive PR body
- Links related issues automatically
- Includes change summary

### Claude Integration

- Adds Claude context to PR
- Includes memory references
- Links coordination data
- Shows agent activity

### PR Template

Automatically generates:

```markdown
## Summary
[Auto-generated summary of changes]

## Changes Made
- List of key changes
- File modifications
- Dependencies updated

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Claude Context
- Branch created by: Claude Assistant
- Coordination ID: [swarm-id]
- Agents involved: [list]
- Memory keys: [relevant keys]

## Related Issues
Closes #[issue-number]

---
🤖 Generated with Claude Flow
```

### Review Automation

- Auto-assigns reviewers by code area
- Adds relevant labels
- Sets milestone
- Configures merge strategy

## Integration

Called automatically when:

- Completing feature branches
- After significant changes
- When requested via @claude
- During workflow completion

Manual usage:

```bash
# Create PR for current branch
npx claude-flow hook auto-pr

# Create PR with specific configuration
npx claude-flow hook auto-pr --branch feature/new --reviewers "team-lead"
```

## Output

Returns JSON with:

```json
{
  "success": true,
  "prNumber": 789,
  "prUrl": "https://github.com/owner/repo/pull/789",
  "title": "Add payment processing",
  "state": "open",
  "draft": true,
  "reviewers": ["user1", "user2"],
  "labels": ["enhancement", "needs-review"],
  "autoMerge": false
}
```

## See Also

- `hook post-branch` - Branch setup
- `hook pre-pr` - PR validation
- `gh pr create` - GitHub CLI
- `hook auto-merge` - Merge automation