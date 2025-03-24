"""
Views for the BioChat Django application.
"""

import json
import asyncio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone

from biochat import BioChatOrchestrator

from .models import Conversation, Message, APIResult
from .utils import get_orchestrator

# Create singleton orchestrator
orchestrator = None

def get_biochat_orchestrator():
    """Get or create the BioChat orchestrator singleton"""
    global orchestrator
    if orchestrator is None:
        orchestrator = get_orchestrator()
    return orchestrator

@csrf_exempt
@login_required
def process_query(request):
    """Process a query and store the results in the database"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        # Parse request body
        data = json.loads(request.body)
        query_text = data.get('query')
        conversation_id = data.get('conversation_id')
        
        if not query_text:
            return JsonResponse({"error": "Query text is required"}, status=400)
        
        # Get or create conversation
        if conversation_id:
            conversation = get_object_or_404(
                Conversation, 
                id=conversation_id, 
                user=request.user
            )
        else:
            # Create a new conversation with the query as the title
            title = query_text[:50] + ('...' if len(query_text) > 50 else '')
            conversation = Conversation.objects.create(
                user=request.user,
                title=title
            )
        
        # Create user message
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=query_text,
            timestamp=timezone.now()
        )
        
        # Get orchestrator
        orchestrator = get_biochat_orchestrator()
        
        # Load conversation history from database
        db_messages = conversation.messages.all().order_by('timestamp')
        orchestrator.clear_conversation_history()
        
        for msg in db_messages:
            role = msg.role
            content = msg.content
            
            if role == 'user':
                orchestrator.conversation_history.append({
                    'role': 'user',
                    'content': content
                })
            elif role == 'assistant':
                orchestrator.conversation_history.append({
                    'role': 'assistant',
                    'content': content
                })
            elif role == 'tool' and msg.tool_call_id:
                orchestrator.conversation_history.append({
                    'role': 'tool',
                    'content': content,
                    'tool_call_id': msg.tool_call_id
                })
        
        # Run the async function in the Django sync environment
        response = asyncio.run(orchestrator.process_query(query_text))
        
        # Store assistant's response
        assistant_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=response,
            timestamp=timezone.now()
        )
        
        # Update conversation timestamp
        conversation.updated_at = timezone.now()
        conversation.save()
        
        return JsonResponse({
            "response": response,
            "conversation_id": str(conversation.id),
            "status": "success"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def get_conversation(request, conversation_id):
    """Get a specific conversation and its messages"""
    if request.method != 'GET':
        return JsonResponse({"error": "Only GET method is allowed"}, status=405)
    
    try:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            user=request.user
        )
        
        messages = conversation.messages.all().order_by('timestamp')
        
        return JsonResponse({
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at
            },
            "messages": [
                {
                    "id": str(message.id),
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp
                }
                for message in messages
            ]
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def list_conversations(request):
    """List all conversations for the current user"""
    if request.method != 'GET':
        return JsonResponse({"error": "Only GET method is allowed"}, status=405)
    
    try:
        conversations = Conversation.objects.filter(user=request.user)
        
        return JsonResponse({
            "conversations": [
                {
                    "id": str(conversation.id),
                    "title": conversation.title,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                    "message_count": conversation.messages.count()
                }
                for conversation in conversations
            ]
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def clear_conversation(request, conversation_id):
    """Clear a specific conversation's messages"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            user=request.user
        )
        
        # Delete all messages in the conversation
        conversation.messages.all().delete()
        
        # Also clear orchestrator history
        orchestrator = get_biochat_orchestrator()
        orchestrator.clear_conversation_history()
        
        return JsonResponse({
            "status": "success",
            "message": "Conversation cleared"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def delete_conversation(request, conversation_id):
    """Delete a specific conversation and all its messages"""
    if request.method != 'DELETE':
        return JsonResponse({"error": "Only DELETE method is allowed"}, status=405)
    
    try:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            user=request.user
        )
        
        # Delete the conversation (this will cascade to messages)
        conversation.delete()
        
        return JsonResponse({
            "status": "success",
            "message": "Conversation deleted"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)