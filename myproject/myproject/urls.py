# config/urls.py (project-level)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Your main app (folder is myapp, but the namespace is "social")
    path("", include(("myapp.urls", "social"), namespace="social")),

    # Accounts app
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),

    # API
    path("api/", include("api.urls")),
    
    #Admin Dashboard
    path("admin-dash/", include("admindashboard.urls", namespace="admindashboard")),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
