# myapp/views.py

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.text import Truncator  # <-- for safe excerpts

from .forms import (
    SignUpForm,
    EmailAuthenticationForm,
    PostForm,
    CommentForm,
    ProfileForm,
)
from .models import (
    Profile,
    Post,
    Comment,
    Like,
    SavedPost,
    Follow,
    Notification,
)

User = get_user_model()


# -----------------------------
# Auth Views (accounts)
# -----------------------------
class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"


class LogoutUserView(LogoutView):
    next_page = reverse_lazy("social:feed")


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("social:feed")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("social:feed")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("social:feed")
    next_url = request.GET.get("next") or request.POST.get("next")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect(next_url or "social:feed")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form, "next": next_url})


# -----------------------------
# Utils
# -----------------------------
def _paginate(request, queryset, per_page=10):
    page_number = request.GET.get("page", 1)
    paginator = Paginator(queryset, per_page)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return page_obj


def _notify_post(*, actor, recipient, post, verb, comment_text=None):
    """
    Create a Notification for a post action.
    Stores only JSON in `extra` (no GenericForeignKey), so no kwargs errors.
    Skips self-notify.
    """
    if not actor or not recipient or recipient.id == actor.id:
        return  # don't notify yourself

    post_excerpt = Truncator(post.text or "").chars(120) if hasattr(post, "text") else ""
    extra = {
        "post_id": post.id,
        "post_excerpt": post_excerpt,
    }
    if comment_text:
        extra["comment_excerpt"] = Truncator(comment_text or "").chars(120)

    Notification.objects.create(
        actor=actor,
        recipient=recipient,
        verb=verb,         # e.g., "liked" / "commented"
        extra=extra,       # JSONField
    )


# -----------------------------
# Feed / Posts
# -----------------------------
@login_required
def feed(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect("admindashboard:home")
    qs = (
        Post.objects
        .select_related("author", "author__profile")
        .order_by("-created_at")
    )
    page_obj = _paginate(request, qs, per_page=10)
    return render(request, "social/feed.html", {"page_obj": page_obj})


@login_required
def posts_by_author(request, user_id):
    qs = (
        Post.objects.select_related("author", "author__profile")
        .filter(author_id=user_id)
        .order_by("-created_at")
    )
    page_obj = _paginate(request, qs, per_page=10)
    return render(request, "social/feed.html", {"page_obj": page_obj})


@login_required
def post_detail(request, pk):
    post = get_object_or_404(
        Post.objects.select_related("author", "author__profile"),
        pk=pk
    )
    comments = (
        Comment.objects.select_related("author", "author__profile")
        .filter(post=post).order_by("-created_at")
    )
    return render(
        request,
        "social/post_detail.html",
        {"post": post, "comments": comments, "comment_form": CommentForm()},
    )


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
@require_POST
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.id:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": "Forbidden"}, status=403)
        messages.warning(request, "You can delete only your own post.")
        return redirect("social:feed")

    post.delete()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return HttpResponse(status=204)

    messages.success(request, "Post deleted.")
    return redirect("social:feed")


# -----------------------------
# Comments  (OPEN to everyone)
# -----------------------------
@login_required
@require_POST
def comment_add(request, post_id):
    """
    Any authenticated user can comment on any post.
    Creates a notification to the post author (unless self).
    """
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Comment cannot be empty.")
        return redirect("social:post-detail", pk=post.id)

    comment = Comment.objects.create(
        post=post,
        author=request.user,
        body=form.cleaned_data["body"],
    )

    # Notify post author (skip if actor == recipient)
    _notify_post(
        actor=request.user,
        recipient=post.author,
        post=post,
        verb="commented",
        comment_text=comment.body,
    )

    messages.success(request, "Comment added.")
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


# -----------------------------
# AJAX Toggles: Like / Save / Follow
# -----------------------------
@login_required
@require_POST
def toggle_like(request, post_id):
    """
    Any authenticated user can like/unlike any post.
    When a like is created, notify the post author (unless self).
    Returns JSON for async UI updates.
    """
    post = get_object_or_404(Post, pk=post_id)

    obj, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        # already liked -> unlike
        obj.delete()
        # If you keep counter fields on Post via signals, the refresh lines are fine.
        post.refresh_from_db(fields=["likes_count"])
        return JsonResponse({"liked": False, "likes_count": post.likes_count})

    # New like -> notify author (skip self)
    _notify_post(
        actor=request.user,
        recipient=post.author,
        post=post,
        verb="liked",
    )

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


# -----------------------------
# Followers / Following lists
# -----------------------------
@login_required
def followers_list(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    follower_ids = Follow.objects.filter(
        following=target
    ).values_list("follower_id", flat=True)

    profiles = list(
        Profile.objects.filter(user_id__in=follower_ids).select_related("user")
    )

    my_following_ids = set(
        Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    )
    for p in profiles:
        p.is_following = p.user_id in my_following_ids

    return render(
        request,
        "social/followers_list.html",
        {"profiles": profiles, "target_user": target},
    )


@login_required
def following_list(request, user_id):
    target = get_object_or_404(User, pk=user_id)

    following_ids = Follow.objects.filter(
        follower=target
    ).values_list("following_id", flat=True)

    profiles = list(
        Profile.objects.filter(user_id__in=following_ids).select_related("user")
    )

    my_following_ids = set(
        Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    )
    for p in profiles:
        p.is_following = p.user_id in my_following_ids

    return render(request, "social/following_list.html", {"profiles": profiles})


# -----------------------------
# Profiles
# -----------------------------
@login_required
def profile_detail(request, user_id):
    profile = get_object_or_404(
        Profile.objects.select_related("user"), user_id=user_id
    )
    is_following = Follow.objects.filter(
        follower=request.user, following=profile.user
    ).exists()
    posts = profile.user.posts.all().order_by("-created_at")
    return render(
        request,
        "social/profile_detail.html",
        {"profile": profile, "posts": posts, "is_following": is_following},
    )


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


# -----------------------------
# Notifications
# -----------------------------
@login_required
def notifications(request):
    qs = (
        Notification.objects
        .select_related("actor", "actor__profile")
        .filter(recipient=request.user)
        .order_by("-created_at")
    )
    page_obj = _paginate(request, qs, per_page=20)
    return render(request, "social/notifications.html", {
        "notifications": page_obj,
        "page_obj": page_obj
    })


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


# -----------------------------
# Static pages
# -----------------------------
def about_view(request):
    return render(request, "social/about.html", {"default_tab": "about"})


def contact_view(request):
    return render(request, "social/about.html", {"default_tab": "contact"})


def faq_view(request):
    return render(request, "social/about.html", {"default_tab": "faq"})


# -----------------------------
# Search
# -----------------------------
def search_view(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return redirect("social:feed")

    people = (
        Profile.objects.filter(Q(full_name__icontains=q) | Q(user__email__icontains=q))
        .select_related("user")
        .order_by("full_name", "user__email")[:20]
    )

    posts = (
        Post.objects.filter(
            Q(text__icontains=q)
            | Q(author__email__icontains=q)
            | Q(author__profile__full_name__icontains=q)
        )
        .select_related("author", "author__profile")
        .order_by("-created_at")[:50]
    )

    return render(
        request,
        "social/search_results.html",
        {"q": q, "people": people, "posts": posts},
    )
