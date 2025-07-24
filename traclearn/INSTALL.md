# TracLearn Installation Guide

## Prerequisites

1. **Trac Installation** (1.4 or later) with Python 2.7
2. **Python 3.11** for the API service
3. **Database**: SQLite, PostgreSQL, or MySQL
4. **Nginx** for routing between services
5. **Redis** (optional) for caching

## Installation Steps

### 1. Install TracLearn Plugin

```bash
cd /path/to/traclearn
python setup.py install
```

### 2. Enable TracLearn in Trac

Add to your `trac.ini`:

```ini
[components]
traclearn.* = enabled
```

### 3. Configure TracLearn

Copy the example configuration and customize:

```bash
cp trac.ini.example /path/to/trac/env/conf/trac.ini
# Edit the configuration as needed
```

Key settings to configure:
- Database connection
- API service URL and port
- AI provider credentials
- File upload paths

### 4. Upgrade Trac Database

```bash
trac-admin /path/to/trac/env upgrade
```

### 5. Set Up Python 3.11 API Service

```bash
cd /path/to/traclearn-api
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` file:
```
TRAC_CONF_PATH=/path/to/trac/env/conf/trac.ini
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-api-key
```

### 6. Configure Nginx

```bash
sudo cp nginx/traclearn.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/traclearn.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Start Services

#### Start Trac (example with Gunicorn):
```bash
gunicorn --bind 0.0.0.0:8080 trac.web.standalone:application
```

#### Start TracLearn API:
```bash
cd /path/to/traclearn-api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 8. Create SystemD Services (Production)

Create `/etc/systemd/system/traclearn-api.service`:

```ini
[Unit]
Description=TracLearn API Service
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/path/to/traclearn-api
Environment="PATH=/path/to/traclearn-api/venv/bin"
ExecStart=/path/to/traclearn-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable traclearn-api
sudo systemctl start traclearn-api
```

## Post-Installation

### 1. Set Permissions

Grant TracLearn permissions to users:

```bash
trac-admin /path/to/trac/env permission add authenticated TRACLEARN_VIEW
trac-admin /path/to/trac/env permission add student TRACLEARN_STUDENT
trac-admin /path/to/trac/env permission add instructor TRACLEARN_INSTRUCTOR
trac-admin /path/to/trac/env permission add admin TRACLEARN_ADMIN
```

### 2. Create Initial Course

Navigate to `/traclearn/courses` and create your first course.

### 3. Test Integration

1. Create a ticket with learning fields
2. Check the dashboard at `/traclearn`
3. Verify API health at `http://localhost:8000/health`

## Troubleshooting

### Database Connection Issues

- Verify database URI in trac.ini
- Check database permissions
- Ensure Python database drivers are installed

### API Connection Errors

- Check if API service is running
- Verify nginx configuration
- Check firewall rules

### Missing Learning Fields

Run database upgrade again:
```bash
trac-admin /path/to/trac/env upgrade --no-backup
```

## Security Considerations

1. Change default API tokens
2. Use HTTPS in production
3. Restrict API access with firewall rules
4. Enable CORS only for trusted origins
5. Regular backup of database and uploaded files