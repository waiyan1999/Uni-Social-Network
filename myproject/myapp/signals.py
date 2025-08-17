from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models as djmodels
from django.contrib.contenttypes.models import ContentType

from .models import (
    User, Profile, Post, Comment, Like,
    Follow, SavedPost, Notification
)

# ---------- PROFILE CREATION ----------
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


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


# ---------- LIKES ----------
@receiver(post_save, sender=Like)
def like_created(sender, instance, created, **kwargs):
    if created:
        Post.objects.filter(id=instance.post_id).update(
            likes_count=djmodels.F("likes_count") + 1
        )
        if instance.user_id != instance.post.author_id:
            Notification.objects.create(
                recipient=instance.post.author,
                actor=instance.user,
                verb="liked your post",
                target_ct=ContentType.objects.get_for_model(Post),
                target_id=instance.post.id
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
                verb="commented on your post",
                target_ct=ContentType.objects.get_for_model(Post),
                target_id=instance.post.id
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
                verb="started following you"
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
