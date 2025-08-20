# api/serializers.py

from django.urls import reverse
from django.contrib.humanize.templatetags.humanize import naturaltime
from rest_framework import serializers

from myapp.models import (
    User, Profile, Post, Comment, Like, Follow, SavedPost, Notification
)

# ------------------------
# Helpers
# ------------------------

def display_name(user):
    """
    Build a portable display name that works with either Django's AbstractUser
    or a custom AbstractBaseUser.
    Order: profile.full_name -> user.get_full_name() -> first/last -> username -> email.
    """
    if not user:
        return "Someone"

    # Profile full name
    pf = getattr(user, "profile", None)
    full = getattr(pf, "full_name", None)
    if full and str(full).strip():
        return str(full).strip()

    # get_full_name if present (AbstractUser)
    if hasattr(user, "get_full_name"):
        try:
            name = user.get_full_name()
            if name and str(name).strip():
                return str(name).strip()
        except Exception:
            pass

    # First/last (won't crash even if fields don't exist)
    first = getattr(user, "first_name", "") or ""
    last = getattr(user, "last_name", "") or ""
    fl = f"{first} {last}".strip()
    if fl:
        return fl

    # Username / email
    un = getattr(user, "username", None)
    if un:
        return un
    em = getattr(user, "email", None)
    if em:
        return em

    return "Someone"


def safe_photo_url(image_field):
    try:
        return image_field.url if image_field else None
    except Exception:
        return None


# ------------------------
# Users & Profiles
# ------------------------

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


# ------------------------
# Posts & Comments
# ------------------------

class CommentSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "author", "body", "created_at", "updated_at", "is_edited", "is_owner"]
        read_only_fields = ["author", "created_at", "updated_at", "is_edited"]

    def get_is_owner(self, obj):
        req = self.context.get("request")
        u = getattr(req, "user", None)
        return bool(u and u.is_authenticated and obj.author_id == u.id)


class PostSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    # denormalized counts
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
    read_only_fields = [
        "author", "is_edited", "created_at", "updated_at",
        "comments_count", "likes_count", "saves_count",
        "is_liked", "is_saved", "is_commented"
    ]

    def get_is_liked(self, obj):
        req = self.context.get("request")
        u = getattr(req, "user", None)
        if not u or not u.is_authenticated:
            return False
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


# ------------------------
# Follow / Saved
# ------------------------

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


# ------------------------
# Notifications
# ------------------------

class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    actor_profile_url = serializers.SerializerMethodField()
    target_url = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    target_post = serializers.SerializerMethodField()
    created_at_human = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id", "verb", "is_read", "created_at",
            "actor",             # pk of actor (FK)
            "actor_name",
            "actor_profile_url",
            "extra",             # keep raw extra if needed
            "target_url",
            "preview",
            "target_post",
            "created_at_human",
        ]
        read_only_fields = [
            "id", "created_at", "actor", "actor_name",
            "actor_profile_url", "target_url", "preview",
            "target_post", "created_at_human",
        ]

    # ---- actor helpers ----
    def get_actor_name(self, obj):
        return display_name(getattr(obj, "actor", None))

    def get_actor_profile_url(self, obj):
        u = getattr(obj, "actor", None)
        if not u:
            return None
        try:
            return reverse("social:profile-detail", args=[u.id])
        except Exception:
            return None

    # ---- target helpers ----
    def _post_id_from_extra(self, obj):
        ex = getattr(obj, "extra", None) or {}
        return ex.get("post_id")

    def get_target_url(self, obj):
        post_id = self._post_id_from_extra(obj)
        if not post_id:
            return None
        try:
            return reverse("social:post-detail", args=[post_id])
        except Exception:
            return None

    def get_preview(self, obj):
        # comment excerpt > post excerpt > None
        ex = getattr(obj, "extra", None) or {}
        return ex.get("comment_excerpt") or ex.get("post_excerpt")

    def get_target_post(self, obj):
        """
        Returns a compact post payload for your modal or list:
        {
            id, url, text, photo_url,
            created_at, created_at_human,
            author_name, author_profile_url
        }
        """
        post_id = self._post_id_from_extra(obj)
        if not post_id:
            return None

        try:
            # IMPORTANT: don't .only() unknown fields like author__first_name/last_name
            p = Post.objects.select_related("author", "author__profile").get(id=post_id)
        except Post.DoesNotExist:
            return None

        return {
            "id": p.id,
            "url": reverse("social:post-detail", args=[p.id]),
            "text": p.text or "",
            "photo_url": safe_photo_url(getattr(p, "photo", None)),
            "created_at": p.created_at.isoformat(),
            "created_at_human": naturaltime(p.created_at),
            "author_name": display_name(p.author),
            "author_profile_url": reverse("social:profile-detail", args=[p.author_id]),
        }

    # ---- convenience ----
    def get_created_at_human(self, obj):
        return naturaltime(obj.created_at)
