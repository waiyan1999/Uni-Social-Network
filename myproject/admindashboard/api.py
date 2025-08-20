from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import TruncDay
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from admindashboard.premissions import IsStaff
from .models import UserSessionLog, RegistrationLog
from myapp.models import User, Post, Like, Comment  # adjust if your app label differs

class StaffOnlyMixin:
    permission_classes = [IsAuthenticated, IsStaff]

def _range(request, default_days=30):
    end = timezone.now()
    days = int(request.GET.get("days", default_days))
    start = end - timedelta(days=days)
    return start, end

class UsersSummary(StaffOnlyMixin, APIView):
    def get(self, request):
        start, end = _range(request)
        regs = (RegistrationLog.objects.filter(created_at__range=(start, end))
                .annotate(day=TruncDay("created_at"))
                .values("day").order_by("day")
                .annotate(count=Count("id")))
        logins = (UserSessionLog.objects.filter(created_at__range=(start, end), action=UserSessionLog.LOGIN)
                  .annotate(day=TruncDay("created_at"))
                  .values("day").order_by("day")
                  .annotate(count=Count("id")))
        return Response({"registrations": list(regs), "logins": list(logins)})

class PostsSummary(StaffOnlyMixin, APIView):
    def get(self, request):
        start, end = _range(request)
        posts = (Post.objects.filter(created_at__range=(start, end))
                 .annotate(day=TruncDay("created_at"))
                 .values("day").order_by("day")
                 .annotate(count=Count("id")))
        top_authors = (Post.objects.filter(created_at__range=(start, end))
                       .values("author_id").annotate(posts=Count("id")).order_by("-posts")[:10])
        return Response({"posts": list(posts), "top_authors": list(top_authors)})

class LikesSummary(StaffOnlyMixin, APIView):
    def get(self, request):
        start, end = _range(request)
        likes = (Like.objects.filter(created_at__range=(start, end))
                 .annotate(day=TruncDay("created_at"))
                 .values("day").order_by("day")
                 .annotate(count=Count("id")))
        top_posts = (Like.objects.filter(created_at__range=(start, end))
                     .values("post_id").annotate(likes=Count("id")).order_by("-likes")[:10])
        return Response({"likes": list(likes), "top_posts": list(top_posts)})

class CommentsSummary(StaffOnlyMixin, APIView):
    def get(self, request):
        start, end = _range(request)
        comments = (Comment.objects.filter(created_at__range=(start, end))
                    .annotate(day=TruncDay("created_at"))
                    .values("day").order_by("day")
                    .annotate(count=Count("id")))
        return Response({"comments": list(comments)})

class AuthSummary(StaffOnlyMixin, APIView):
    def get(self, request):
        start, end = _range(request)
        totals = (UserSessionLog.objects.filter(created_at__range=(start, end))
                  .values("action").annotate(count=Count("id")))
        return Response({"auth": list(totals)})
