# myapp/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models as djmodels
from django.utils.text import Truncator

from .models import (
    User, Profile, Post, Comment, Like,
    Follow, SavedPost, Notification
)

# ---------- DO NOT re-create Profile here ----------
# You already auto-create Profile in social/models.py:
# @receiver(post_save, sender=User) -> Profile.objects.get_or_create(user=instance)
# If we also create() here, it will raise IntegrityError on the one-to-one.
# So REMOVE the duplicate signal entirely.

# ---------- POSTS COUNTERS ----------
@receiver(post_save, sender=Post)
def post_created(sender, instance, created, **kwargs):
    if created:
        Profile.objects.filter(user=instance.author).update(
            posts_count=djmodels.F("posts_count") + 1
        )

@receiver(post_delete, sender=Post)
def post_deleted(sender, instance, **kwargs):
    Profile.objects.filter(user=instance.author).update(
        posts_count=djmodels.F("posts_count") - 1
    )

# ---------- Helper to build Notification.extra ----------
def _post_extra(post: Post, comment_text: str | None = None):
    ex = {
        "post_id": post.id,
        "post_excerpt": Truncator(post.text or "").chars(120),
    }
    if comment_text:
        ex["comment_excerpt"] = Truncator(comment_text or "").chars(120)
    return ex

# ---------- LIKES ----------
@receiver(post_save, sender=Like)
def like_created(sender, instance, created, **kwargs):
    if created:
        Post.objects.filter(id=instance.post_id).update(
            likes_count=djmodels.F("likes_count") + 1
        )
        # notify post author, but not yourself
        if instance.user_id != instance.post.author_id:
            Notification.objects.create(
                recipient=instance.post.author,
                actor=instance.user,
                verb="liked",                      # matches notifications.html
                extra=_post_extra(instance.post),  # JSON only
            )

@receiver(post_delete, sender=Like)
def like_deleted(sender, instance, **kwargs):
    Post.objects.filter(id=instance.post_id).update(
        likes_count=djmodels.F("likes_count") - 1
    )

# ---------- COMMENTS ----------
@receiver(post_save, sender=Comment)
def comment_created(sender, instance, created, **kwargs):
    if created:
        Post.objects.filter(id=instance.post_id).update(
            comments_count=djmodels.F("comments_count") + 1
        )
        if instance.author_id != instance.post.author_id:
            Notification.objects.create(
                recipient=instance.post.author,
                actor=instance.author,
                verb="commented",                               # matches notifications.html
                extra=_post_extra(instance.post, instance.body)
            )

@receiver(post_delete, sender=Comment)
def comment_deleted(sender, instance, **kwargs):
    Post.objects.filter(id=instance.post_id).update(
        comments_count=djmodels.F("comments_count") - 1
    )

# ---------- FOLLOW ----------
@receiver(post_save, sender=Follow)
def follow_created(sender, instance, created, **kwargs):
    if created:
        Profile.objects.filter(user=instance.follower).update(
            following_count=djmodels.F("following_count") + 1
        )
        Profile.objects.filter(user=instance.following).update(
            followers_count=djmodels.F("followers_count") + 1
        )
        if instance.follower_id != instance.following_id:
            Notification.objects.create(
                recipient=instance.following,
                actor=instance.follower,
                verb="started following you",
                extra=None,
            )

@receiver(post_delete, sender=Follow)
def follow_deleted(sender, instance, **kwargs):
    Profile.objects.filter(user=instance.follower).update(
        following_count=djmodels.F("following_count") - 1
    )
    Profile.objects.filter(user=instance.following).update(
        followers_count=djmodels.F("followers_count") - 1
    )

# ---------- SAVED POSTS ----------
@receiver(post_save, sender=SavedPost)
def save_created(sender, instance, created, **kwargs):
    if created:
        Post.objects.filter(id=instance.post_id).update(
            saves_count=djmodels.F("saves_count") + 1
        )

@receiver(post_delete, sender=SavedPost)
def save_deleted(sender, instance, **kwargs):
    Post.objects.filter(id=instance.post_id).update(
        saves_count=djmodels.F("saves_count") - 1
    )
