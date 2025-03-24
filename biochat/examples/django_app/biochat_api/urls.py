"""
URL configuration for the BioChat Django application.
"""

from django.urls import path
from . import views

app_name = 'biochat_api'

urlpatterns = [
    # Query processing
    path('query/', views.process_query, name='process_query'),
    
    # Conversation management
    path('conversations/', views.list_conversations, name='list_conversations'),
    path('conversations/<uuid:conversation_id>/', views.get_conversation, name='get_conversation'),
    path('conversations/<uuid:conversation_id>/clear/', views.clear_conversation, name='clear_conversation'),
    path('conversations/<uuid:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
]