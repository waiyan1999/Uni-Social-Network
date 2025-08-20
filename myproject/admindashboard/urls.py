# admindashboard/urls.py
from django.urls import path
from . import views

app_name = "admindashboard"

urlpatterns = [
    path("", views.home, name="home"),  # Dashboard page with users + posts

    # Summary JSON endpoints (optional but handy for charts)
    path("api/summary/users/", views.users_summary, name="users-summary"),
    path("api/summary/posts/", views.posts_summary, name="posts-summary"),
    path("api/summary/likes/", views.likes_summary, name="likes-summary"),
    path("api/summary/comments/", views.comments_summary, name="comments-summary"),

    # List JSON endpoints (optional)
    path("api/users/", views.users_list_api, name="users-list-api"),
    path("api/posts/", views.posts_list_api, name="posts-list-api"),
]
