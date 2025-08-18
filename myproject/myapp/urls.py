from django.urls import path
from . import views
from .views import EmailLoginView, LogoutUserView, signup_view

app_name = "social"

urlpatterns = [
    # Feed & posts
    path("", views.feed, name="feed"),
    path("posts/author/<int:user_id>/", views.posts_by_author, name="posts-by-author"),
    path("posts/<int:pk>/", views.post_detail, name="post-detail"),
    path("posts/new/", views.post_create, name="post-create"),
    path("posts/<int:pk>/edit/", views.post_edit, name="post-edit"),
    path("posts/<int:pk>/delete/", views.post_delete, name="post-delete"),

    # Comments
    path("posts/<int:post_id>/comments/add/", views.comment_add, name="comment-add"),
    path("comments/<int:comment_id>/delete/", views.comment_delete, name="comment-delete"),

    # AJAX toggles
    path("posts/<int:post_id>/like/", views.toggle_like, name="post-like"),
    path("posts/<int:post_id>/save/", views.toggle_save, name="post-save"),
    path("follow/toggle/", views.toggle_follow, name="follow-toggle"),

    # Followers / following lists
    path("followers/<int:user_id>/", views.followers_list, name="followers-list"),
    path("following/<int:user_id>/", views.following_list, name="following-list"),

    # Profiles
    path("profiles/<int:user_id>/", views.profile_detail, name="profile-detail"),
    path("profiles/me/edit/", views.profile_edit, name="profile-edit"),

    # Notifications
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:notif_id>/read/", views.notification_read, name="notification-read"),
    path("notifications/read_all/", views.notifications_read_all, name="notifications-read-all"),
    
    
    
    
    
    path("login/",  EmailLoginView.as_view(), name="login"),
    path("logout/", LogoutUserView.as_view(next_page="social:feed"), name="logout"),
    path("signup/", signup_view, name="signup"),
    
    
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("faq/", views.faq_view, name="faq"),
    
    path("search/", views.search_view, name="search"),
]
