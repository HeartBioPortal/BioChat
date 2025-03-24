"""
Utility functions for the BioChat Django application.
"""

import os
from django.conf import settings
from biochat import BioChatOrchestrator

def get_orchestrator():
    """
    Create and return a BioChat orchestrator instance.
    
    Retrieves API keys from Django settings or environment variables.
    """
    # Try to get API keys from Django settings first, fall back to environment variables
    openai_api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
    ncbi_api_key = getattr(settings, 'NCBI_API_KEY', os.getenv('NCBI_API_KEY'))
    contact_email = getattr(settings, 'CONTACT_EMAIL', os.getenv('CONTACT_EMAIL'))
    biogrid_access_key = getattr(settings, 'BIOGRID_ACCESS_KEY', os.getenv('BIOGRID_ACCESS_KEY'))
    
    # Validate required API keys
    if not openai_api_key or not ncbi_api_key or not contact_email:
        missing = []
        if not openai_api_key:
            missing.append('OPENAI_API_KEY')
        if not ncbi_api_key:
            missing.append('NCBI_API_KEY')
        if not contact_email:
            missing.append('CONTACT_EMAIL')
        
        raise ValueError(f"Missing required API keys: {', '.join(missing)}")
    
    # Create and return the orchestrator
    return BioChatOrchestrator(
        openai_api_key=openai_api_key,
        ncbi_api_key=ncbi_api_key,
        biogrid_access_key=biogrid_access_key,
        tool_name="BioChat_Django",
        email=contact_email
    )

def save_api_result(message, api_name, query, result):
    """
    Save an API result to the database for future reference.
    
    Args:
        message: The Message model instance
        api_name: The name of the API
        query: The query that was sent to the API
        result: The API result (must be JSON serializable)
    
    Returns:
        The created APIResult instance
    """
    from .models import APIResult
    
    return APIResult.objects.create(
        message=message,
        api_name=api_name,
        query=query,
        result=result
    )