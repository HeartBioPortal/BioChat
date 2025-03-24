# BioChat Installation Guide

This guide will help you install and set up BioChat for various use cases.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- API keys for:
  - OpenAI (for GPT-4 access)
  - NCBI E-utilities
  - BioGRID (optional)

## Basic Installation

### Install from PyPI

```bash
pip install biochat
```

### Install from Source

```bash
git clone https://github.com/yourusername/biochat.git
cd biochat
pip install -e .
```

### Set up Environment Variables

Create a `.env` file in your project root:

```
OPENAI_API_KEY=your_openai_api_key
NCBI_API_KEY=your_ncbi_api_key
CONTACT_EMAIL=your_email@example.com
BIOGRID_ACCESS_KEY=your_biogrid_api_key  # Optional
```

## Integration with FastAPI

### Installation

```bash
pip install biochat fastapi uvicorn
```

### Quick Start

Create a file named `main.py`:

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict
import os
from dotenv import load_dotenv

from biochat import BioChatOrchestrator

# Load environment variables
load_dotenv()

# FastAPI app
app = FastAPI(title="BioChat API")

# Pydantic model
class Query(BaseModel):
    text: str

# Dependency
def get_orchestrator():
    return BioChatOrchestrator(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ncbi_api_key=os.getenv("NCBI_API_KEY"),
        biogrid_access_key=os.getenv("BIOGRID_ACCESS_KEY"),
        tool_name="BioChat_FastAPI",
        email=os.getenv("CONTACT_EMAIL")
    )

@app.post("/query")
async def process_query(
    query: Query,
    orchestrator: BioChatOrchestrator = Depends(get_orchestrator)
) -> Dict:
    try:
        response = await orchestrator.process_query(query.text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run the server:

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload
```

## Integration with Django

### Installation

```bash
pip install biochat django
```

### 1. Create a Django app

```bash
python manage.py startapp biochat_api
```

### 2. Add to INSTALLED_APPS

In your `settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps
    'biochat_api',
]

# BioChat settings
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
NCBI_API_KEY = os.environ.get('NCBI_API_KEY')
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL')
BIOGRID_ACCESS_KEY = os.environ.get('BIOGRID_ACCESS_KEY')
```

### 3. Create models and views

Create `biochat_api/models.py`, `biochat_api/views.py`, and other files as shown in the examples.

### 4. Add URLs to your project

In your project's `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('api/biochat/', include('biochat_api.urls')),
]
```

### 5. Run migrations

```bash
python manage.py makemigrations biochat_api
python manage.py migrate
```

## Troubleshooting

### API Keys

If you encounter authentication errors, check that your API keys are correctly set in environment variables or passed to the `BioChatOrchestrator` constructor.

### Dependency Issues

If you encounter dependency conflicts, try creating a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install biochat
```

### CORS Issues (for web applications)

If you're building a web application and encounter CORS issues, ensure you've added CORS middleware to your FastAPI or Django application.

For FastAPI, add:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For Django, install `django-cors-headers`:

```bash
pip install django-cors-headers
```

And add to your `settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ... other middleware
]

CORS_ALLOW_ALL_ORIGINS = True  # Modify this in production
```