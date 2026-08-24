from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """
    Decorator that:
    - Redirects unauthenticated users to the admin login page.
    - Returns 403 Forbidden for authenticated non-staff users.
    - Allows only is_staff users through.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin-panel/login/')
        if not request.user.is_staff:
            raise PermissionDenied  # → renders 403
        return view_func(request, *args, **kwargs)
    return wrapper

def superuser_required(view_func):
    """
    Decorator that:
    - Redirects unauthenticated users to the admin login page.
    - Returns 403 Forbidden for anyone who is not a superuser (including normal staff).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin-panel/login/')
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
