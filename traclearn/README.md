# TracLearn - Educational Learning Management Plugin for Trac

TracLearn is a comprehensive learning management system (LMS) plugin for Trac that bridges Python 2.7 (Trac) with Python 3.11 (modern AI/analytics capabilities).

## Features

- **Learning Management**: Track student progress, assignments, and assessments through Trac tickets
- **Analytics Dashboard**: Real-time analytics and reporting on learning outcomes
- **AI Integration**: AI-powered insights and recommendations via Python 3.11 backend
- **Voice Interface**: Optional voice command support for accessibility
- **Multi-language Support**: Internationalization ready with i18n support
- **Modern UI**: HTMX-powered dynamic interfaces while maintaining Trac compatibility

## Architecture

TracLearn uses a dual-process architecture:
- **Trac Plugin (Python 2.7)**: Core plugin integrated with Trac's component system
- **API Service (Python 3.11)**: Modern FastAPI backend for AI and analytics

The two services communicate via HTTP REST API with nginx routing.

## Installation

1. Install the TracLearn plugin:
   ```bash
   cd /path/to/traclearn
   python setup.py install
   ```

2. Enable TracLearn in your `trac.ini`:
   ```ini
   [components]
   traclearn.* = enabled
   ```

3. Set up the Python 3.11 API service:
   ```bash
   cd /path/to/traclearn-api
   pip install -r requirements.txt
   python -m uvicorn app.main:app --port 8000
   ```

4. Configure nginx for routing (see `nginx/traclearn.conf`)

5. Upgrade your Trac environment:
   ```bash
   trac-admin /path/to/env upgrade
   ```

## Configuration

Add to your `trac.ini`:

```ini
[traclearn]
api_enabled = true
api_port = 8000
analytics_enabled = true
ai_features_enabled = true
voice_interface_enabled = false
default_language = en
max_file_size = 10485760
cache_ttl = 3600
python3_executable = python3
api_base_url = http://localhost:8000/api/v1
```

## Database Schema

TracLearn creates the following tables:
- `traclearn_courses`: Course definitions
- `traclearn_enrollments`: Student enrollments
- `traclearn_progress`: Learning progress tracking
- `traclearn_assessments`: Assessment results
- `traclearn_analytics`: Analytics data

## API Endpoints

The Python 3.11 API service provides:
- `/api/v1/analytics`: Analytics endpoints
- `/api/v1/ai`: AI-powered features
- `/api/v1/reports`: Reporting endpoints
- `/api/v1/voice`: Voice interface endpoints

## Development

### Plugin Structure
```
traclearn/
├── __init__.py              # Main plugin setup
├── components/              # Trac components
├── db/                      # Database schemas and bridges
├── web/                     # Web handlers and API proxy
├── templates/               # Jinja2 templates
├── htdocs/                  # Static assets
├── ticket_extensions/       # Ticket field extensions
└── locale/                  # Translations
```

### Running Tests
```bash
python -m pytest tests/
```

## License

BSD 3-Clause License

## Support

For issues and feature requests, please use the project issue tracker.