# app: social/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields.get("is_staff") or not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_staff   = models.BooleanField(default=False)
    is_active  = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # no username

    def __str__(self):
        return self.email




class Profile(models.Model):
    
    MAJOR = [
        ('CST','CST'),
        ('CS','Computer Science (CS)'),
        ('CT','Computer Technology (CT)')
    
    ]
    
    ACADEMIC_YEAR = [
        ('FIRST_YEAR','first year'),
        ('SECOND_YEAR','Second year'),
        ('THIRD_YEAR','Third year'),
        ('FORUTH_YEAR','Fourth year'),
        ('FINAL_YEAR','Final year')
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    major = models.CharField(max_length=15,choices=MAJOR,blank=True,null=True)
    year = models.CharField(max_length=15,choices=ACADEMIC_YEAR,blank=True,null=True)
    roll_no = models.CharField(max_length=15,blank=True,null=True)
    photo = models.ImageField(upload_to='profile', blank=True, null=True)
    phone_no = models.CharField(max_length=15,blank=True,null=True)
    # convenience counters (denormalized; keep in sync with signals)
    posts_count = models.PositiveIntegerField(default=0)
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.email}'s profile"



class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    text = models.TextField(blank=True)  # text can be empty if only photo(s)
    photo = models.ImageField(upload_to='post',blank=True,null=True)
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # fast counts (optional denormalized fields)
    comments_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    saves_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["author", "-created_at"]),
        ]

    def __str__(self):
        return f"Post {self.id} by {self.author}"





# ---------- COMMENTS ----------
class Comment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["post", "-created_at"])]

    def __str__(self):
        return f"Comment {self.id} on Post {self.post_id}"


# ---------- LIKES ----------
class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_like_per_user_post"),
        ]
        indexes = [models.Index(fields=["post"]), models.Index(fields=["user"])]

    def __str__(self):
        return f"{self.user} likes Post {self.post_id}"


# ---------- FOLLOW (self-referential) ----------
class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow"),
            models.CheckConstraint(check=~models.Q(follower=models.F("following")), name="prevent_self_follow"),
        ]
        indexes = [models.Index(fields=["following"]), models.Index(fields=["follower"])]

    def __str__(self):
        return f"{self.follower} -> {self.following}"


# ---------- SAVED POSTS ----------
class SavedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_save_per_user_post"),
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user} saved Post {self.post_id}"


# ---------- NOTIFICATIONS (generic) ----------
class Notification(models.Model):
    # who receives it
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    # who triggered it (optional; system notifications may not have an actor)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="actor_notifications")
    verb = models.CharField(max_length=64)  # e.g., "liked", "commented", "followed"
    # generic link to the thing (post/comment/follow)
    target_ct = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    target_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("target_ct", "target_id")

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]

    def __str__(self):
        return f"Notif to {self.recipient_id}: {self.verb}"
