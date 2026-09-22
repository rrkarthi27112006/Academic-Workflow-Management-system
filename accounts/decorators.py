from functools import wraps
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required
# pyrefly: ignore [missing-import]
from django.core.exceptions import PermissionDenied


def teacher_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'teacher_profile'):
            raise PermissionDenied('This page is only available to teachers.')
        return view_func(request, *args, **kwargs)
    return _wrapped


def student_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'student_profile'):
            raise PermissionDenied('This page is only available to students.')
        return view_func(request, *args, **kwargs)
    return _wrapped

