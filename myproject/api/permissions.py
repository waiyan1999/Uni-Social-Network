# api/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrReadOnly(BasePermission):
    """
    Object must have .author (Post/Comment) to check ownership.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner_id = getattr(obj, "author_id", None) or getattr(obj, "user_id", None)
        return bool(request.user and request.user.is_authenticated and owner_id == request.user.id)


class IsSelfOrReadOnly(BasePermission):
    """
    For Profile updates: only the owner can modify.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.id)
