from django.contrib.auth.decorators import user_passes_test

def staff_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view_func)
