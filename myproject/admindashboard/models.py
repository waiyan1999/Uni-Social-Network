from django.db import models
from django.conf import settings

class UserSessionLog(models.Model):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    ACTION_CHOICES = [
        (LOGIN, "Login"),
        (LOGOUT, "Logout"),
        (LOGIN_FAILED, "Login failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]
        ordering = ["-created_at"]

class RegistrationLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    source = models.CharField(max_length=50, blank=True, default="signup_form")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["created_at"])]
        ordering = ["-created_at"]
