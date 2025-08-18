# api/serializers.py
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef
from rest_framework import serializers

from myapp.models import (
    User, Profile, Post, Comment, Like, Follow, SavedPost, Notification
)


# --- Small helpers ---

class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email"]


class ProfileSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Profile
        fields = [
            "user", "full_name", "bio", "major", "year", "roll_no",
            "photo", "phone_no", "posts_count", "followers_count", "following_count",
        ]
        read_only_fields = ["posts_count", "followers_count", "following_count"]


class UserPublicSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "date_joined", "profile"]


# --- Post & Comment ---

class CommentSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "author", "body", "created_at", "updated_at", "is_edited", "is_owner"]
        read_only_fields = ["author", "created_at", "updated_at", "is_edited"]

    def get_is_owner(self, obj):
        u = self.context.get("request").user if self.context.get("request") else None
        return bool(u and u.is_authenticated and obj.author_id == u.id)


class PostSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    # fast counts (already denormalized in your model)
    comments_count = serializers.IntegerField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    saves_count = serializers.IntegerField(read_only=True)

    # personalized flags
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    is_commented = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id", "author", "text", "photo", "is_edited",
            "created_at", "updated_at",
            "comments_count", "likes_count", "saves_count",
            "is_liked", "is_saved", "is_commented",
        ]
        read_only_fields = ["author", "is_edited", "created_at", "updated_at",
                            "comments_count", "likes_count", "saves_count",
                            "is_liked", "is_saved", "is_commented"]

    def get_is_liked(self, obj):
        req = self.context.get("request")
        u = getattr(req, "user", None)
        if not u or not u.is_authenticated:
            return False
        # If the view annotated is_liked=Exists(...), prefer that
        val = getattr(obj, "is_liked", None)
        if val is not None:
            return bool(val)
        return Like.objects.filter(post=obj, user=u).exists()

    def get_is_saved(self, obj):
        req = self.context.get("request")
        u = getattr(req, "user", None)
        if not u or not u.is_authenticated:
            return False
        val = getattr(obj, "is_saved", None)
        if val is not None:
            return bool(val)
        return SavedPost.objects.filter(post=obj, user=u).exists()

    def get_is_commented(self, obj):
        req = self.context.get("request")
        u = getattr(req, "user", None)
        if not u or not u.is_authenticated:
            return False
        val = getattr(obj, "is_commented", None)
        if val is not None:
            return bool(val)
        return Comment.objects.filter(post=obj, author=u).exists()


# --- Follow / Saved / Notification (optional detail serializers) ---

class FollowSerializer(serializers.ModelSerializer):
    follower = UserPublicSerializer(read_only=True)
    following = UserPublicSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "follower", "following", "created_at"]


class SavedPostSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)

    class Meta:
        model = SavedPost
        fields = ["id", "post", "created_at"]


# class NotificationSerializer(serializers.ModelSerializer):
#     recipient = UserMiniSerializer(read_only=True)
#     actor = UserMiniSerializer(read_only=True)
#     target_type = serializers.SerializerMethodField()

#     class Meta:
#         model = Notification
#         fields = [
#             "id", "recipient", "actor", "verb",
#             "target_id", "target_type",
#             "is_read", "created_at",
#         ]
#         read_only_fields = ["recipient", "actor", "created_at"]

#     def get_target_type(self, obj):
#         return obj.target_ct.model if obj.target_ct else None
    
# class NotificationSerializer(serializers.ModelSerializer):
#     actor_name = serializers.SerializerMethodField()

#     class Meta:
#         model = Notification
#         fields = ['id', 'verb', 'is_read', 'created_at', 'actor', 'actor_name']
#         read_only_fields = ['id', 'created_at', 'actor', 'actor_name']

#     def get_actor_name(self, obj):
#         # Show full_name (or email) safely
#         user = getattr(obj, 'actor', None)
#         if user is None:
#             return None
#         return getattr(user, 'full_name', None) or getattr(user, 'email', None)

# api/serializers.py
from rest_framework import serializers
from myapp.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()
    extra = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'verb', 'is_read', 'created_at',
            'actor_name', 'link', 'extra'
        ]
        read_only_fields = ['id', 'created_at', 'actor_name', 'link', 'extra']

    def get_actor_name(self, obj):
        u = getattr(obj, 'actor', None)
        if not u: return None
        return getattr(u, 'full_name', None) or getattr(u, 'email', None)

    def get_link(self, obj):
        # Return a URL to the related target if you have one
        # Example if you store a GenericForeignKey to Post/Comment:
        t = getattr(obj, 'target', None)
        try:
            return t.get_absolute_url() if t and hasattr(t, 'get_absolute_url') else None
        except Exception:
            return None

    def get_extra(self, obj):
        # If you store metadata (e.g., JSONField like obj.meta)
        return getattr(obj, 'meta', None)
