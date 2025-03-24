# BioChat Deployment Guide

This guide covers different deployment options for BioChat, from simple standalone servers to production deployments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Deployment](#development-deployment)
- [Docker Deployment](#docker-deployment)
- [Production Deployment with FastAPI](#production-deployment-with-fastapi)
- [Production Deployment with Django](#production-deployment-with-django)
- [Security Considerations](#security-considerations)
- [Monitoring and Logging](#monitoring-and-logging)

## Prerequisites

- Python 3.8 or higher
- API keys for:
  - OpenAI (for GPT-4 access)
  - NCBI E-utilities
  - BioGRID (optional)
- Docker (for containerized deployment)
- A reverse proxy like Nginx (for production)

## Development Deployment

### FastAPI Development Server

```bash
# Install dependencies
pip install biochat uvicorn python-dotenv

# Create a simple FastAPI app
cat > app.py << EOF
from fastapi import FastAPI, Depends
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from biochat import BioChatOrchestrator

# Load environment variables
load_dotenv()

app = FastAPI(title="BioChat API")

class Query(BaseModel):
    text: str

def get_orchestrator():
    return BioChatOrchestrator(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ncbi_api_key=os.getenv("NCBI_API_KEY"),
        biogrid_access_key=os.getenv("BIOGRID_ACCESS_KEY"),
        tool_name="BioChat_Dev",
        email=os.getenv("CONTACT_EMAIL")
    )

@app.post("/query")
async def process_query(query: Query, orchestrator=Depends(get_orchestrator)):
    response = await orchestrator.process_query(query.text)
    return {"response": response}
EOF

# Run the development server
uvicorn app:app --reload
```

### Django Development Server

For Django, follow the steps in the [Installation Guide](INSTALLATION.md) to set up a Django app, then run:

```bash
python manage.py runserver
```

## Docker Deployment

### Create a Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Create a requirements.txt file

```
biochat
fastapi
uvicorn
python-dotenv
```

### Create a docker-compose.yml file

```yaml
version: '3'

services:
  biochat:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./:/app
    restart: unless-stopped
```

### Build and run the Docker container

```bash
docker-compose up --build
```

## Production Deployment with FastAPI

For production deployment, we'll use Gunicorn with Uvicorn workers behind Nginx.

### Create a Gunicorn configuration

```python
# gunicorn_conf.py
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"
```

### Nginx configuration

```nginx
# /etc/nginx/sites-available/biochat
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/biochat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Create a systemd service

```ini
# /etc/systemd/system/biochat.service
[Unit]
Description=BioChat API Service
After=network.target

[Service]
User=biochat
Group=biochat
WorkingDirectory=/path/to/app
ExecStart=/path/to/venv/bin/gunicorn -c gunicorn_conf.py app:app
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable biochat
sudo systemctl start biochat
```

## Production Deployment with Django

### Update settings.py for production

```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['example.com', 'www.example.com']

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Set up Gunicorn

```bash
# Create a Gunicorn startup script
cat > start_gunicorn.sh << EOF
#!/bin/bash
NAME="biochat"
DJANGODIR=/path/to/project
SOCKFILE=/path/to/project/run/gunicorn.sock
USER=biochat
GROUP=biochat
NUM_WORKERS=3
DJANGO_SETTINGS_MODULE=myproject.settings
DJANGO_WSGI_MODULE=myproject.wsgi

echo "Starting $NAME as `whoami`"

# Activate the virtual environment
cd $DJANGODIR
source /path/to/venv/bin/activate

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# Start your Django Unicorn
exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user=$USER --group=$GROUP \
  --bind=unix:$SOCKFILE \
  --log-level=warning \
  --log-file=-
EOF

chmod +x start_gunicorn.sh
```

### Nginx configuration for Django

```nginx
# /etc/nginx/sites-available/biochat
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /path/to/project;
    }

    location /media/ {
        root /path/to/project;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/project/run/gunicorn.sock;
    }
}
```

### Create a systemd service for Django

```ini
# /etc/systemd/system/biochat.service
[Unit]
Description=BioChat Django Service
After=network.target

[Service]
User=biochat
Group=biochat
WorkingDirectory=/path/to/project
ExecStart=/path/to/project/start_gunicorn.sh
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

## Security Considerations

### API Keys and Secrets

- Store API keys and secrets in environment variables
- Use a secrets management solution for production (AWS Secrets Manager, HashiCorp Vault)
- Rotate API keys regularly

### Rate Limiting

Implement rate limiting to protect your API from abuse:

```python
# For FastAPI
from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/query")
@limiter.limit("10/minute")
async def process_query(request: Request, query: Query, orchestrator=Depends(get_orchestrator)):
    response = await orchestrator.process_query(query.text)
    return {"response": response}
```

### Authentication

Add authentication for API access:

```python
# For FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

@app.post("/query")
async def process_query(
    query: Query, 
    api_key: str = Depends(get_api_key),
    orchestrator=Depends(get_orchestrator)
):
    response = await orchestrator.process_query(query.text)
    return {"response": response}
```

## Monitoring and Logging

### Configure Logging

```python
# logging_config.py
import os
import logging
from logging.handlers import RotatingFileHandler

def configure_logging(log_dir="logs"):
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "biochat.log"),
        maxBytes=10485760,  # 10 MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# Use in your application
configure_logging()
```

### Health Check Endpoint

Add a health check endpoint to monitor the application:

```python
@app.get("/health")
async def health_check():
    try:
        # Check if orchestrator can be initialized
        orchestrator = get_orchestrator()
        
        # Check if database connections are alive
        # (example: check if APIs are accessible)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### Set Up Prometheus Metrics

```python
# For FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

# Initialize FastAPI app
app = FastAPI()

# Initialize Prometheus instrumentation
Instrumentator().instrument(app).expose(app)
```

Then configure Prometheus to scrape these metrics and Grafana to visualize them.