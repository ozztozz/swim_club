# users/decorators.py
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps

def role_required(allowed_roles=[]):
    """
    Kullanıcının belirtilen rollerden birine sahip olup olmadığını kontrol eden decorator.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('user-login')
            
            # Kullanıcının rolü izin verilen roller arasında mı?
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Yetkisi yoksa 403 / İzin Verilmedi hatası fırlat
            raise PermissionDenied
        return _wrapped_view
    return decorator