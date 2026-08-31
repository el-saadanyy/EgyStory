"""
Chatbot Views for EgyStory.
Handles HTTP POST requests, CSRF validation, session conversation storage, and responses.
"""

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from .context_builder import build_chatbot_context
from .gemini_service import generate_chat_response

# Maximum turns to keep in session to prevent session bloat
MAX_HISTORY_MESSAGES = 10
MAX_MESSAGE_LENGTH = 1000

@require_POST
def send_message(request):
    """
    POST /chatbot/message/
    Accepts JSON: {"message": "..."}
    Returns JSON: {"status": "success", "reply": "...", "history": [...]}
    or {"status": "error", "message": "..."}
    """
    # 1. Parse JSON payload
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON format in request.'
        }, status=400)

    # 2. Validate message content
    message = data.get('message', '').strip()
    lang = data.get('lang', 'ar').strip().lower()
    if lang not in ['ar', 'en']:
        lang = 'ar'

    if not message:
        return JsonResponse({
            'status': 'error',
            'message': 'Message cannot be empty.' if lang == 'en' else 'لا يمكن إرسال رسالة فارغة.'
        }, status=400)

    if len(message) > MAX_MESSAGE_LENGTH:
        return JsonResponse({
            'status': 'error',
            'message': f'Message is too long (maximum {MAX_MESSAGE_LENGTH} characters).' if lang == 'en' else f'الرسالة طويلة جداً (الحد الأقصى {MAX_MESSAGE_LENGTH} حرف).'
        }, status=400)

    # 3. Retrieve conversation history from session (Session-only persistence)
    # Format: [{'role': 'user', 'text': '...'}, {'role': 'assistant', 'text': '...'}]
    session_key = 'chatbot_history'
    history = request.session.get(session_key, [])
    if not isinstance(history, list):
        history = []

    # 4. Build dynamic EgyStory database context
    user = request.user if request.user.is_authenticated else None
    egy_context = build_chatbot_context(message, user=user)

    # 5. Call Gemini service
    reply, error = generate_chat_response(message, history, egy_context, lang=lang)

    if error:
        return JsonResponse({
            'status': 'error',
            'message': error
        }, status=500)

    # 6. Update session history safely
    history.append({'role': 'user', 'text': message})
    history.append({'role': 'assistant', 'text': reply})

    # Trim to maximum allowed history to avoid session overflow
    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]

    request.session[session_key] = history
    request.session.modified = True

    return JsonResponse({
        'status': 'success',
        'reply': reply
    })

@require_POST
def clear_history(request):
    """
    POST /chatbot/clear/
    Clears the chatbot session history.
    """
    if 'chatbot_history' in request.session:
        del request.session['chatbot_history']
        request.session.modified = True
    return JsonResponse({'status': 'success', 'message': 'Conversation cleared.'})

def get_history(request):
    """
    GET /chatbot/history/
    Retrieves the current session's conversation history for the UI.
    """
    history = request.session.get('chatbot_history', [])
    if not isinstance(history, list):
        history = []
    return JsonResponse({'status': 'success', 'history': history})
