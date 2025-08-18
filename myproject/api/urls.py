# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet, ProfileViewSet, PostViewSet, CommentViewSet,
    SavedPostViewSet, NotificationViewSet,FollowToggleAPIView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'saved', SavedPostViewSet, basename='saved')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
     path('follow/', FollowToggleAPIView.as_view(), name='api-follow-toggle'),
]
