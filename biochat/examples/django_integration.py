"""
Example of integrating BioChat with Django.

This example shows how to create a Django view that uses BioChat.
"""

# views.py example
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import asyncio
import os

from biochat import BioChatOrchestrator

# Initialize the orchestrator (consider using Django settings for API keys)
# This could be initialized in settings.py or using a singleton pattern
orchestrator = BioChatOrchestrator(
    openai_api_key=os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY,
    ncbi_api_key=os.getenv("NCBI_API_KEY") or settings.NCBI_API_KEY,
    biogrid_access_key=os.getenv("BIOGRID_ACCESS_KEY") or getattr(settings, "BIOGRID_ACCESS_KEY", None),
    tool_name="BioChat_Django",
    email=os.getenv("CONTACT_EMAIL") or settings.CONTACT_EMAIL
)

@csrf_exempt
def process_query(request):
    """Django view to process a BioChat query"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        # Parse request body
        data = json.loads(request.body)
        query_text = data.get('query')
        
        if not query_text:
            return JsonResponse({"error": "Query text is required"}, status=400)
        
        # Run the async function in the Django sync environment
        response = asyncio.run(orchestrator.process_query(query_text))
        
        return JsonResponse({
            "response": response,
            "status": "success"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def clear_history(request):
    """Django view to clear conversation history"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        orchestrator.clear_conversation_history()
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# urls.py example
"""
from django.urls import path
from . import views

urlpatterns = [
    path('biochat/query/', views.process_query, name='biochat_query'),
    path('biochat/clear/', views.clear_history, name='biochat_clear'),
]
"""

# settings.py example
"""
# BioChat settings
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
NCBI_API_KEY = os.environ.get('NCBI_API_KEY')
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL')
BIOGRID_ACCESS_KEY = os.environ.get('BIOGRID_ACCESS_KEY')

# Validate required settings
if not all([OPENAI_API_KEY, NCBI_API_KEY, CONTACT_EMAIL]):
    raise ValueError('Missing required BioChat API keys in settings')
"""