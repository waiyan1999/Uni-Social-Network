# api/views.py
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from myapp.models import (
    User, Profile, Post, Comment, Like, Follow, SavedPost, Notification
)
from .serializers import (
    UserPublicSerializer, ProfileSerializer, PostSerializer, CommentSerializer,
    FollowSerializer, SavedPostSerializer, NotificationSerializer
)
from .permissions import IsOwnerOrReadOnly, IsSelfOrReadOnly
from .pagination import DefaultPagination


# ---- Users & Profiles ----

class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = User.objects.all().select_related("profile")
    serializer_class = UserPublicSerializer
    permission_classes = [AllowAny]
    pagination_class = DefaultPagination

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        target = self.get_object()
        if target.id == request.user.id:
            return Response({"detail": "cannot follow yourself"}, status=400)
        rel, created = Follow.objects.get_or_create(follower=request.user, following=target)
        if not created:
            rel.delete()
            following = False
        else:
            following = True
        followers_count = Follow.objects.filter(following=target).count()
        return Response({"following": following, "followers_count": followers_count})


class ProfileViewSet(mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    queryset = Profile.objects.select_related("user")
    serializer_class = ProfileSerializer
    permission_classes = [IsSelfOrReadOnly]


# ---- Posts & Comments ----

class PostViewSet(viewsets.ModelViewSet):
    """
    CRUD for posts + actions: like, save, comments sub-endpoints.
    """
    serializer_class = PostSerializer
    permission_classes = [IsOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = DefaultPagination

    def get_queryset(self):
        u = self.request.user if self.request else None
        qs = Post.objects.all().select_related("author", "author__profile")

        if u and u.is_authenticated:
            qs = qs.annotate(
                is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=u)),
                is_saved=Exists(SavedPost.objects.filter(post=OuterRef("pk"), user=u)),
                is_commented=Exists(Comment.objects.filter(post=OuterRef("pk"), author=u)),
            )
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        obj, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            obj.delete()
            liked = False
        else:
            liked = True
        # refresh counters (you can keep your signal-based counters instead)
        post.likes_count = post.likes.count()
        post.save(update_fields=["likes_count"])
        return Response({"liked": liked, "likes_count": post.likes_count})

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    def save(self, request, pk=None):
        post = self.get_object()
        obj, created = SavedPost.objects.get_or_create(post=post, user=request.user)
        if not created:
            obj.delete()
            saved = False
        else:
            saved = True
        post.saves_count = post.saved_by.count()
        post.save(update_fields=["saves_count"])
        return Response({"saved": saved, "saves_count": post.saves_count})

    @action(methods=["get", "post"], detail=True, permission_classes=[IsAuthenticated])
    def comments(self, request, pk=None):
        """
        GET: list comments for the post
        POST: create comment for the post
        """
        post = self.get_object()
        if request.method.lower() == "get":
            qs = post.comments.select_related("author", "author__profile").order_by("-created_at")
            page = self.paginate_queryset(qs)
            ser = CommentSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(ser.data)
        # POST
        ser = CommentSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save(author=request.user, post=post)
        # update counter (or rely on your signals)
        post.comments_count = post.comments.count()
        post.save(update_fields=["comments_count"])
        return Response(ser.data, status=status.HTTP_201_CREATED)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related("author", "author__profile", "post")
    serializer_class = CommentSerializer
    permission_classes = [IsOwnerOrReadOnly]
    pagination_class = DefaultPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# ---- Saved posts (current user) ----

class SavedPostViewSet(mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    serializer_class = SavedPostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination

    def get_queryset(self):
        return SavedPost.objects.filter(user=self.request.user).select_related(
            "post", "post__author", "post__author__profile"
        ).order_by("-created_at")


# ---- Notifications ----

# class NotificationViewSet(mixins.ListModelMixin,
#                           viewsets.GenericViewSet):
#     serializer_class = NotificationSerializer
#     permission_classes = [IsAuthenticated]
#     pagination_class = DefaultPagination

#     def get_queryset(self):
#         return Notification.objects.filter(recipient=self.request.user).select_related("actor", "recipient").order_by("-created_at")

#     @action(methods=["post"], detail=True)
#     def mark_read(self, request, pk=None):
#         notif = self.get_object()
#         notif.is_read = True
#         notif.save(update_fields=["is_read"])
#         return Response({"ok": True})

#     @action(methods=["post"], detail=False)
#     def mark_all_read(self, request):
#         Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
#         return Response({"ok": True})
# from rest_framework import viewsets, permissions, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from .serializers import NotificationSerializer
# from myapp.models import Notification  # adjust import

# class NotificationViewSet(viewsets.ModelViewSet):
#     serializer_class = NotificationSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

#     def partial_update(self, request, *args, **kwargs):
#         # PATCH /api/notifications/{id}/ {"is_read": true}
#         return super().partial_update(request, *args, **kwargs)

#     @action(detail=False, methods=['post'], url_path='mark_all_read')
#     def mark_all_read(self, request):
#         qs = self.get_queryset().filter(is_read=False)
#         updated = qs.update(is_read=True)
#         return Response({'ok': True, 'updated': updated}, status=status.HTTP_200_OK)

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.serializers import NotificationSerializer
from myapp.models import Notification

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (Notification.objects
                .filter(recipient=self.request.user)
                .order_by('-created_at'))

    # PATCH /api/notifications/{id}/ {"is_read": true} works via partial_update()

    @action(detail=False, methods=['post'], url_path='mark_all_read')
    def mark_all_read(self, request):
        qs = self.get_queryset().filter(is_read=False)
        updated = qs.update(is_read=True)
        return Response({'ok': True, 'updated': updated})

    @action(detail=False, methods=['post'], url_path='delete_all')
    def delete_all(self, request):
        # Optionally: only delete read ones by filtering is_read=True
        deleted, _ = self.get_queryset().delete()
        return Response({'ok': True, 'deleted': deleted})
    
    @action(detail=False, methods=['get'], url_path='unread_count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})
    

# api/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from myapp.models import Follow  # adjust to your app

User = get_user_model()

class FollowToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        action = request.data.get('action')
        if not user_id or action not in ('follow','unfollow'):
            return Response({'ok': False, 'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

        if str(request.user.id) == str(user_id):
            return Response({'ok': False, 'error': "You can't follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'ok': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if action == 'follow':
            Follow.objects.get_or_create(follower=request.user, following=target)
            return Response({'ok': True, 'status': 'followed'})
        else:  # unfollow
            Follow.objects.filter(follower=request.user, following=target).delete()
            return Response({'ok': True, 'status': 'unfollowed'})
