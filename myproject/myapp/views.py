from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth import login, get_user_model,logout
from .forms import SignUpForm

from .models import (
    User, Profile, Post, Comment, Like, SavedPost, Follow, Notification
)
from .forms import PostForm, CommentForm, ProfileForm


from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .forms import SignUpForm, EmailAuthenticationForm

class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "registration/login.html"   # see template below


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("social:feed")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


class LogoutUserView(LogoutView):
    next_page = reverse_lazy("feed")




# -------- Helpers --------
def _paginate(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    return paginator.get_page(page_number)


# -------- Feed / Posts --------
@login_required
def feed(request):
    following_ids = Follow.objects.filter(
        follower=request.user
    ).values_list("following_id", flat=True)

    qs = (Post.objects.select_related("author", "author__profile")
          .filter(Q(author__in=following_ids) | Q(author=request.user))
          .order_by("-created_at"))
    page_obj = _paginate(request, qs, per_page=10)
    
    
    
    # likes_subq = Like.objects.filter(user=request.user, post=OuterRef("pk"))
    # posts = (
    #     Post.objects
    #     .select_related("author")
    #     .annotate(is_liked=Exists(likes_subq))
    #     .order_by("-created_at")
    # )
    
    
    # likes_subq = Like.objects.filter(user=request.user, post=OuterRef("pk"))
    # posts = (
    #     Post.objects
    #     .annotate(is_liked=Exists(likes_subq))
    #     .order_by("-created_at")
    # )
    
    posts = Post.objects.all().order_by("-created_at")
    context = {'posts':posts,'qs':qs}
    
    return render(request, "social/feed.html", context)


@login_required
def posts_by_author(request, user_id):
    qs = (Post.objects.select_related("author", "author__profile")
          .filter(author_id=user_id)
          .order_by("-created_at"))
    page_obj = _paginate(request, qs, per_page=10)
    return render(request, "social/feed.html", {"posts": page_obj, "page_obj": page_obj})


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related("author", "author__profile"), pk=pk)
    comments = (Comment.objects.select_related("author", "author__profile")
                .filter(post=post).order_by("-created_at"))
    return render(request, "social/post_detail.html", {
        "post": post,
        "comments": comments,
        "comment_form": CommentForm(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.author = request.user
            obj.save()
            messages.success(request, "Post created.")
            return redirect("social:feed")
    else:
        form = PostForm()
    return render(request, "social/post_form.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.id:
        return HttpResponseForbidden("You can edit only your post.")
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated.")
            return redirect("social:post-detail", pk=post.id)
    else:
        form = PostForm(instance=post)
    return render(request, "social/post_form.html", {"form": form, "object": post})


@login_required
@require_http_methods(["GET", "POST"])
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.id:
        return HttpResponseForbidden("You can delete only your post.")
    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted.")
        return redirect("social:feed")
    # Simple inline confirm (you can make a dedicated template if you want)
    return render(request, "social/post_confirm_delete.html", {"post": post})


# -------- Comments --------
@login_required
@require_POST
def comment_add(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        Comment.objects.create(post=post, author=request.user, body=form.cleaned_data["body"])
        messages.success(request, "Comment added.")
    else:
        messages.error(request, "Comment cannot be empty.")
    return redirect("social:post-detail", pk=post.id)


@login_required
@require_POST
def comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if comment.author_id != request.user.id:
        return HttpResponseForbidden("You can delete only your comments.")
    post_id = comment.post_id
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect("social:post-detail", pk=post_id)


# -------- AJAX Toggles: Like / Save / Follow --------
@login_required
@require_POST
def toggle_like(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    obj, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        obj.delete()
        post.refresh_from_db(fields=["likes_count"])
        return JsonResponse({"liked": False, "likes_count": post.likes_count})
    post.refresh_from_db(fields=["likes_count"])
    return JsonResponse({"liked": True, "likes_count": post.likes_count})


@login_required
@require_POST
def toggle_save(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    obj, created = SavedPost.objects.get_or_create(user=request.user, post=post)
    if not created:
        obj.delete()
        post.refresh_from_db(fields=["saves_count"])
        return JsonResponse({"saved": False, "saves_count": post.saves_count})
    post.refresh_from_db(fields=["saves_count"])
    return JsonResponse({"saved": True, "saves_count": post.saves_count})


@login_required
@require_POST
def toggle_follow(request):
    user_id = request.POST.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id required"}, status=400)
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        return JsonResponse({"error": "Cannot follow yourself."}, status=400)
    obj, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        obj.delete()
        return JsonResponse({"following": False})
    return JsonResponse({"following": True})


# -------- Followers / Following lists --------
@login_required
def followers_list(request, user_id):
    follower_ids = Follow.objects.filter(following_id=user_id).values_list("follower_id", flat=True)
    qs = Profile.objects.select_related("user").filter(user_id__in=follower_ids).order_by("user__username")
    page_obj = _paginate(request, qs, per_page=20)
    return render(request, "social/followers_list.html", {"profiles": page_obj, "page_obj": page_obj})


@login_required
def following_list(request, user_id):
    following_ids = Follow.objects.filter(follower_id=user_id).values_list("following_id", flat=True)
    qs = Profile.objects.select_related("user").filter(user_id__in=following_ids).order_by("user__username")
    page_obj = _paginate(request, qs, per_page=20)
    return render(request, "social/following_list.html", {"profiles": page_obj, "page_obj": page_obj})


# -------- Profiles --------
@login_required
def profile_detail(request, user_id):
    profile = get_object_or_404(Profile.objects.select_related("user"), user_id=user_id)
    # show posts (newest first)
    posts = profile.user.posts.all().order_by("-created_at")
    return render(request, "social/profile_detail.html", {"profile": profile, "posts": posts})


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    profile = get_object_or_404(Profile, user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("social:profile-detail", user_id=request.user.id)
    else:
        form = ProfileForm(instance=profile)
    return render(request, "social/profile_edit.html", {"form": form, "profile": profile})


# -------- Notifications --------
@login_required
def notifications(request):
    qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    page_obj = _paginate(request, qs, per_page=20)
    return render(request, "social/notifications.html", {"notifications": page_obj, "page_obj": page_obj})


@login_required
@require_POST
def notification_read(request, notif_id):
    notif = get_object_or_404(Notification, pk=notif_id, recipient=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=["is_read"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
def notifications_read_all(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})


# social/views.py (add this function)
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        # Already logged in → go home
        return redirect("social:feed")

    next_url = request.GET.get("next") or request.POST.get("next")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()              # signals will auto-create Profile
            login(request, user)            # log the new user in
            messages.success(request, "Welcome! Your account has been created.")
            return redirect(next_url or "social:feed")
    else:
        form = SignUpForm()

    return render(request, "registration/register.html", {"form": form, "next": next_url})


