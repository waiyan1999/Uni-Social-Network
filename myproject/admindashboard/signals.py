from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserSessionLog, RegistrationLog

def _meta_from_request(request):
    if not request:
        return None, ""
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "")
    ip = ip.split(",")[0].strip() if ip else None
    ua = request.META.get("HTTP_USER_AGENT", "")
    return ip or None, ua

@receiver(user_logged_in)
def on_logged_in(sender, request, user, **kwargs):
    ip, ua = _meta_from_request(request)
    UserSessionLog.objects.create(user=user, action=UserSessionLog.LOGIN, ip=ip, user_agent=ua)

@receiver(user_logged_out)
def on_logged_out(sender, request, user, **kwargs):
    ip, ua = _meta_from_request(request)
    UserSessionLog.objects.create(user=user, action=UserSessionLog.LOGOUT, ip=ip, user_agent=ua)

@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    ip, ua = _meta_from_request(request)
    UserSessionLog.objects.create(user=None, action=UserSessionLog.LOGIN_FAILED, ip=ip, user_agent=ua)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        RegistrationLog.objects.create(user=instance, source="post_save")
