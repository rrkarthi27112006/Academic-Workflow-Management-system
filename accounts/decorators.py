from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def _role_required(profile_attr, role_name):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not hasattr(request.user, profile_attr):
                raise PermissionDenied(f'This page is only available to {role_name}.')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


teacher_required = _role_required('teacher_profile', 'teachers')
student_required = _role_required('student_profile', 'students')
