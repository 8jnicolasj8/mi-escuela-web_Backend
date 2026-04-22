"""
Middleware para gestión multi-tenant (multi-escuela)
"""
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied


class TenantMiddleware:
    """
    Middleware que extrae la escuela del request basándose en:
    1. Query param: ?school=slug
    2. Header: X-School-Slug
    3. Subdominio (para producción)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Rutas que no requieren tenant
        exempt_urls = [
            '/admin/',
            '/api/v1/auth/',
            '/api/v1/schools/public/',
            '/api/v1/users/me/',
            '/api/v1/schools/',
            '/api/v1/schools/',
            '/api/v1/userschool/',
            '/api/v1/users/',
            '/api/v1/anios/',
            '/api/v1/cursos/',
            '/api/v1/materias/',
            '/api/v1/alumnos/',
            '/api/v1/classrooms/',
            '/api/v1/publicaciones/',
        ]
        
        # Allow schools detail endpoints (like /schools/{id}/directivos/)
        if request.path.startswith('/api/v1/schools/') and len(request.path.split('/')) >= 5:
            return self.get_response(request)
        
        if any(request.path.startswith(url) for url in exempt_urls):
            # STILL try to set school from header for these endpoints
            school_slug = (
                request.GET.get('school') or
                request.headers.get('X-School-Slug')
            )
            if school_slug:
                from apps.schools.models import School
                try:
                    request.escuela = School.objects.get(
                        slug=school_slug, 
                        activa=True
                    )
                except School.DoesNotExist:
                    pass
            return self.get_response(request)
        
        # Superadmin puede acceder sin escuela
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)
        
        # Extraer school slug
        school_slug = (
            request.GET.get('school') or
            request.headers.get('X-School-Slug')
        )
        
        if school_slug:
            from apps.schools.models import School
            
            try:
                request.escuela = School.objects.get(
                    slug=school_slug, 
                    activa=True
                )
            except School.DoesNotExist:
                return JsonResponse({
                    'error': 'Escuela no encontrada',
                    'code': 'SCHOOL_NOT_FOUND'
                }, status=404)
        
        return self.get_response(request)


class RequireSchoolMixin:
    """Mixin para views que requieren una escuela"""
    
    @property
    def escuela(self):
        if not hasattr(self, '_escuela'):
            self._escuela = getattr(self.request, 'escuela', None)
        return self._escuela
    
    def dispatch(self, request, *args, **kwargs):
        if not self.escuela:
            return JsonResponse({
                'error': 'School header required',
                'code': 'SCHOOL_REQUIRED'
            }, status=400)
        return super().dispatch(request, *args, **kwargs)