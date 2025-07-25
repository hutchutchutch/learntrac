# Learntrac Display Plugin

A Trac plugin that displays learning questions in the ticket view to help users test their understanding of concepts related to tickets.

## Features

- Displays learning questions directly in the ticket view
- Supports multiple question types:
  - Multiple choice questions
  - Open-ended questions
- Difficulty indicators (easy, medium, hard)
- Interactive submission of answers
- Clean, responsive UI design

## Installation

1. Build the plugin:
   ```bash
   cd plugins/learntrac_display
   python setup.py bdist_egg
   ```

2. Install the plugin:
   ```bash
   cp dist/LearntracDisplay-*.egg /path/to/trac/plugins/
   ```

3. Enable the plugin in trac.ini:
   ```ini
   [components]
   learntrac_display.* = enabled
   ```

4. Restart Trac to load the plugin.

## Configuration

No additional configuration is required for basic functionality. The plugin will automatically display learning questions on ticket pages.

## Architecture

The plugin implements the following Trac interfaces:

- **ITicketManipulator**: Integrates with the ticket system
- **ITemplateProvider**: Provides templates and static resources
- **ITemplateStreamFilter**: Injects learning questions into ticket view

## Components

### Main Component: LearningTicketDisplay

Located in `learntrac_display/ticket_display.py`, this component:

1. Filters the ticket template stream
2. Retrieves learning questions for the ticket
3. Injects a questions panel into the ticket view
4. Provides CSS and JavaScript resources

### Static Resources

- **CSS**: `htdocs/css/learntrac.css` - Styles for the questions panel
- **JavaScript**: `htdocs/js/learntrac.js` - Handles user interactions

### Templates

- **learntrac_panel.html**: Genshi template for complex question rendering (optional)

## Development

### Adding New Question Types

To add a new question type:

1. Update `_get_learning_questions()` to include the new type
2. Add rendering logic in `_create_questions_panel()`
3. Update JavaScript to handle the new interaction
4. Add appropriate CSS styles

### Connecting to Learning API

The current implementation uses mock data. To connect to a real API:

1. Update `_get_learning_questions()` to call your API
2. Implement proper error handling
3. Add configuration options for API endpoints

## Future Enhancements

- [ ] Connect to real learning API
- [ ] Add more question types (drag-and-drop, code exercises)
- [ ] Implement answer validation and feedback
- [ ] Add progress tracking
- [ ] Support for hints and explanations
- [ ] Analytics on question performance
- [ ] Caching for better performance

## License

This plugin is licensed under the BSD license, same as Trac.