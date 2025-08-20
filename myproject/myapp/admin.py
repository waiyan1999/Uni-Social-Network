# myapp/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

from .models import Post, Comment, Like, SavedPost, Follow, Notification  # add Profile here only if you created it

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    # your User has only: email, is_staff, is_active, date_joined (plus auth fields)
    list_display = ("id", "email", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser", "groups")
    search_fields = ("email",)      # removed first_name / last_name
    ordering = ("email",)

    # remove first/last name from fieldsets
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active"),
        }),
    )


# --- Register the rest (only once each) ---
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "created_at", "likes_count", "comments_count", "saves_count")
    list_select_related = ("author",)
    search_fields = ("author__email", "text")
    date_hierarchy = "created_at"

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "created_at", "is_edited")
    list_select_related = ("post", "author")
    search_fields = ("author__email", "body")
    date_hierarchy = "created_at"

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    list_select_related = ("post", "user")
    search_fields = ("user__email", "post__id")

@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    list_select_related = ("post", "user")
    search_fields = ("user__email", "post__id")

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("id", "follower", "following", "created_at")
    list_select_related = ("follower", "following")
    search_fields = ("follower__email", "following__email")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "actor", "verb", "is_read", "created_at")
    list_filter = ("is_read", "verb")
    list_select_related = ("recipient", "actor")
    search_fields = ("recipient__email", "actor__email")
    date_hierarchy = "created_at"
