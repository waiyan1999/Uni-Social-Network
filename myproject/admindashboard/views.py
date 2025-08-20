# admindashboard/views.py
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Sum, F, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.timezone import localtime

# Adjust import path if models live elsewhere
from myapp.models import Post
try:
    from myapp.models import Comment  # optional
    HAS_COMMENT_MODEL = True
except Exception:
    Comment = None
    HAS_COMMENT_MODEL = False

User = get_user_model()


# ----------------------------
# Helpers
# ----------------------------
def _staff_required(user):
    return user.is_staff or user.is_superuser

def _dt_to_str(dt):
    if not dt:
        return None
    return localtime(dt).strftime("%Y-%m-%d %H:%M")

def _name_or_email(user):
    """
    Show a nice display name:
    - profile.full_name if available
    - else email
    """
    try:
        prof = getattr(user, "profile", None)
        if prof:
            name = (getattr(prof, "full_name", "") or "").strip()
            if name:
                return name
    except Exception:
        pass
    return getattr(user, "email", "") or ""

def _paginate(request, queryset, per_page=10, page_param="page"):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get(page_param)
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)
    return page_obj

def _post_likes_count_queryset():
    """
    Returns a queryset of Post annotated with 'likes_count_eff' that works
    whether you store likes in IntegerField 'likes_count' or M2M 'likes'.
    """
    try:
        Post._meta.get_field("likes_count")  # raises if not present
        return Post.objects.annotate(likes_count_eff=Coalesce(F("likes_count"), Value(0)))
    except Exception:
        return Post.objects.annotate(likes_count_eff=Count("likes"))


# ----------------------------
# Dashboard Page (users + posts)
# ----------------------------
@login_required
@user_passes_test(_staff_required)
def home(request):
    """
    University Social Network Admin Dashboard
    Renders:
      - Users table (paginated)
      - Posts table (paginated)
    Query params:
      - u (users page), p (posts page)
      - u_size (users page size), p_size (posts page size)
    """
    # Page sizes (defaults)
    try:
        u_size = int(request.GET.get("u_size", 10))
    except Exception:
        u_size = 10
    try:
        p_size = int(request.GET.get("p_size", 10))
    except Exception:
        p_size = 10

    # Users queryset
    users_qs = (
        User.objects
        .select_related("profile")
        .order_by("-date_joined")
    )
    users_page = _paginate(request, users_qs, per_page=u_size, page_param="u")

    # Posts queryset (with author, comment count, likes count)
    posts_qs = (
        _post_likes_count_queryset()
        .select_related("author", "author__profile")
        .annotate(num_comments=Count("comments"))
        .order_by("-created_at")
    )
    posts_page = _paginate(request, posts_qs, per_page=p_size, page_param="p")

    context = {
        "total_users": User.objects.count(),
        "total_posts": Post.objects.count(),
        "users_page": users_page,
        "posts_page": posts_page,
        "u_size": u_size,
        "p_size": p_size,
    }
    return render(request, "admindashboard/index.html", context)


# ----------------------------
# Summary JSON Endpoints (optional)
# ----------------------------
@login_required
@user_passes_test(_staff_required)
def users_summary(request):
    latest_user = (
        User.objects
        .order_by("-date_joined")
        .values("id", "email", "date_joined")
        .first()
    )
    latest_post = (
        Post.objects
        .order_by("-created_at")
        .values("id", "text", "created_at", "author_id")
        .first()
    )
    data = {
        "total_users": User.objects.count(),
        "total_posts": Post.objects.count(),
        "latest_user": (
            {**latest_user, "date_joined": _dt_to_str(latest_user["date_joined"])}
            if latest_user else None
        ),
        "latest_post": (
            {**latest_post, "created_at": _dt_to_str(latest_post["created_at"])}
            if latest_post else None
        ),
    }
    return JsonResponse(data)

@login_required
@user_passes_test(_staff_required)
def posts_summary(request):
    top_author_row = (
        Post.objects.values("author_id", "author__email")
        .annotate(num_posts=Count("id"))
        .order_by("-num_posts")
        .first()
    )
    top_author = (
        {
            "id": top_author_row["author_id"],
            "email": top_author_row["author__email"],
            "num_posts": top_author_row["num_posts"],
        } if top_author_row else None
    )
    latest_post = (
        Post.objects
        .order_by("-created_at")
        .values("id", "text", "created_at", "author_id")
        .first()
    )
    data = {
        "total_posts": Post.objects.count(),
        "latest_post": (
            {**latest_post, "created_at": _dt_to_str(latest_post["created_at"])}
            if latest_post else None
        ),
        "top_author": top_author,
    }
    return JsonResponse(data)

@login_required
@user_passes_test(_staff_required)
def likes_summary(request):
    qs = _post_likes_count_queryset()
    agg = qs.aggregate(total_likes=Coalesce(Sum("likes_count_eff"), Value(0)))
    top_row = (
        qs.order_by(F("likes_count_eff").desc(nulls_last=True))
          .values("id", "text", "created_at", "author_id", "likes_count_eff")
          .first()
    )
    top_post = (
        {
            "id": top_row["id"],
            "text": top_row["text"],
            "created_at": _dt_to_str(top_row["created_at"]),
            "author_id": top_row["author_id"],
            "likes": top_row["likes_count_eff"] or 0,
        } if top_row else None
    )
    return JsonResponse({"total_likes": agg["total_likes"] or 0, "top_post": top_post})

@login_required
@user_passes_test(_staff_required)
def comments_summary(request):
    if HAS_COMMENT_MODEL and Comment is not None:
        total_comments = Comment.objects.count()
        qs = Post.objects.annotate(num_comments=Count("comments"))
    else:
        qs = Post.objects.annotate(num_comments=Count("comments"))
        total_comments = qs.aggregate(c=Coalesce(Sum("num_comments"), Value(0)))["c"] or 0

    top_row = (
        qs.order_by(F("num_comments").desc(nulls_last=True))
          .values("id", "text", "created_at", "author_id", "num_comments")
          .first()
    )
    top_post = (
        {
            "id": top_row["id"],
            "text": top_row["text"],
            "created_at": _dt_to_str(top_row["created_at"]),
            "author_id": top_row["author_id"],
            "comments": top_row["num_comments"] or 0,
        } if top_row else None
    )
    return JsonResponse({"total_comments": total_comments, "top_post": top_post})


# ----------------------------
# List JSON Endpoints (optional)
# ----------------------------
@login_required
@user_passes_test(_staff_required)
def users_list_api(request):
    try:
        page = int(request.GET.get("page", 1))
    except Exception:
        page = 1
    try:
        page_size = int(request.GET.get("page_size", 10))
    except Exception:
        page_size = 10

    qs = User.objects.select_related("profile").order_by("-date_joined")
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    items = []
    for u in page_obj.object_list:
        photo_url = ""
        try:
            if getattr(u, "profile", None) and u.profile.photo:
                photo_url = u.profile.photo.url
        except Exception:
            photo_url = ""
        items.append({
            "id": u.id,
            "name": _name_or_email(u),
            "email": u.email,
            "date_joined": _dt_to_str(u.date_joined),
            "photo": photo_url,
        })

    return JsonResponse({
        "page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "total_items": paginator.count,
        "items": items,
    })

@login_required
@user_passes_test(_staff_required)
def posts_list_api(request):
    try:
        page = int(request.GET.get("page", 1))
    except Exception:
        page = 1
    try:
        page_size = int(request.GET.get("page_size", 10))
    except Exception:
        page_size = 10

    qs = (
        _post_likes_count_queryset()
        .select_related("author", "author__profile")
        .annotate(num_comments=Count("comments"))
        .order_by("-created_at")
    )
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    items = []
    for p in page_obj.object_list:
        author = p.author
        author_name = _name_or_email(author) if author else ""
        author_photo = ""
        try:
            if author and getattr(author, "profile", None) and author.profile.photo:
                author_photo = author.profile.photo.url
        except Exception:
            author_photo = ""
        items.append({
            "id": p.id,
            "text": p.text or "",
            "created_at": _dt_to_str(p.created_at),
            "author_id": author.id if author else None,
            "author_name": author_name,
            "author_photo": author_photo,
            "num_comments": getattr(p, "num_comments", 0) or 0,
            "likes": getattr(p, "likes_count_eff", 0) or 0,
        })

    return JsonResponse({
        "page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "total_items": paginator.count,
        "items": items,
    })
