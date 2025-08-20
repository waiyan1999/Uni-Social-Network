# api/views_unread.py (or append to your NotificationViewSet as @action)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return Response({'count': count})