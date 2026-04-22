from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from apps.users.views import (
    UserViewSet, UserSchoolViewSet, SolicitudViewSet,
    generar_codigo_view, vincular_alumno_view, mis_hijos_view,
    mi_codigo_view, vincular_hijo_view
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'userschool', UserSchoolViewSet, basename='userschool')
router.register(r'solicitudes', SolicitudViewSet, basename='solicitud')

urlpatterns = [
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('generar-codigo/', generar_codigo_view, name='generar-codigo'),
    path('vincular/', vincular_alumno_view, name='vincular'),
    path('mis-hijos/', mis_hijos_view, name='mis-hijos'),
    path('mi-codigo/', mi_codigo_view, name='mi-codigo'),
    path('vincular-hijo/', vincular_hijo_view, name='vincular-hijo'),
    path('', include(router.urls)),
]