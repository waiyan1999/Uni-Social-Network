from django.apps import AppConfig

class AdmindashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admindashboard"

    def ready(self):
        from . import signals  # noqa: F401  (register signal handlers)
