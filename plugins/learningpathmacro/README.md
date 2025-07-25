# Learning Path Macro for Trac

This plugin provides a `[[LearningPath]]` Wiki macro that displays structured learning paths for educational content in Trac.

## Features

- **Multiple View Types**: Tree, List, Graph, and Timeline views
- **Progress Tracking**: Track user progress through learning paths
- **Prerequisites**: Define and display prerequisite relationships
- **Interactive UI**: Expandable trees, clickable items, keyboard navigation
- **Difficulty Filtering**: Filter paths by beginner, intermediate, or advanced
- **Database Storage**: Persistent storage of learning paths and progress
- **Extensible API**: Other plugins can integrate with learning paths

## Installation

1. Install the plugin:
   ```bash
   cd plugins/learningpathmacro
   python setup.py develop
   ```

2. Update your `trac.ini` to enable the plugin:
   ```ini
   [components]
   learningpathmacro.* = enabled
   ```

3. Upgrade your Trac environment to create the database tables:
   ```bash
   trac-admin /path/to/env upgrade
   ```

## Usage

### Basic Usage

```wiki
[[LearningPath(topic=mathematics)]]
```

### With Options

```wiki
[[LearningPath(topic=python-programming, view=tree, show_progress=true, depth=3)]]
```

### Available Parameters

- `topic` - The main topic of the learning path (required)
- `view` - Display style: 'tree' (default), 'list', 'graph', or 'timeline'
- `show_progress` - Show progress indicators (true/false, default: true)
- `depth` - Maximum depth of subtopics to display (default: 3)
- `expand` - Auto-expand to specified level (default: 1)
- `filter` - Filter by difficulty: 'beginner', 'intermediate', 'advanced'
- `show_prerequisites` - Show prerequisite connections (true/false, default: false)
- `interactive` - Enable interactive features (true/false, default: true)
- `style` - Custom CSS class for styling

## Examples

### Tree View with Progress
```wiki
[[LearningPath(topic=web-development, view=tree, show_progress=true)]]
```

### Filtered List for Beginners
```wiki
[[LearningPath(topic=programming, view=list, filter=beginner)]]
```

### Graph View with Prerequisites
```wiki
[[LearningPath(topic=data-science, view=graph, show_prerequisites=true)]]
```

### Timeline View
```wiki
[[LearningPath(topic=machine-learning, view=timeline)]]
```

## Database Schema

The plugin creates the following tables:

- `learning_path` - Stores learning path definitions
- `learning_path_prerequisites` - Stores prerequisite relationships
- `learning_path_resources` - Links to wiki pages, tickets, and external resources
- `learning_path_progress` - Tracks user progress

## API

Other plugins can interact with learning paths:

```python
from learningpathmacro.api import LearningPathSystem

lps = LearningPathSystem(self.env)

# Get all learning paths
paths = lps.get_all_learning_paths(req)

# Get specific path
path = lps.get_learning_path(req, 'python-programming')

# Update user progress
lps.update_progress(req, 'python-programming', progress=50, status='in_progress')

# Get user's learning paths
user_paths = lps.get_user_paths(req, status_filter='in_progress')

# Get recommended next path
recommendation = lps.recommend_next_path(req)
```

## Permissions

The plugin defines two permissions:

- `LEARNING_PATH_VIEW` - View learning paths
- `LEARNING_PATH_ADMIN` - Administer learning paths

## Styling

The plugin includes default CSS styling. You can customize the appearance by:

1. Adding custom CSS to your theme
2. Using the `style` parameter to add custom classes
3. Overriding the default styles in your `site.css`

## Development

To contribute to the plugin:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This plugin is licensed under the BSD License.

## Support

For issues and feature requests, please use the project's issue tracker.