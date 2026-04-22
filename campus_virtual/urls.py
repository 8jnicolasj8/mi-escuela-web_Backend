from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # API v1 (principal)
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.schools.urls')),
    path('api/v1/', include('apps.academics.urls')),
    
    # API sin prefijo v1 (compatibilidad)
    path('api/', include('apps.users.urls')),
    path('api/', include('apps.schools.urls')),
    path('api/', include('apps.academics.urls')),
    
    # Admin
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)