# social/context_processors.py
from .models import Notification

def unread_notifications_count(request):
    if request.user.is_authenticated:
        c = Notification.objects.filter(recipient=request.user, is_read=False).count()
    else:
        c = 0
    return {'unread_count': c}
