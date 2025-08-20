from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from myapp.forms import SignUpForm  # reuse your existing form

@require_http_methods(["GET", "POST"])
def signup(request):
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
