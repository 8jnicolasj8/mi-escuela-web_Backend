from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status


def custom_exception_handler(exc, context):
    """Manejador de excepciones personalizado"""
    response = exception_handler(exc, context)
    
    if response is not None:
        error_data = {
            'error': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
            'code': getattr(exc, 'default_code', 'ERROR'),
        }
        
        # Agregar detalles extra si existen
        if hasattr(exc, 'extra'):
            error_data['detail'] = exc.extra
            
        response.data = error_data
    
    return response


class AppException(APIException):
    """Excepción base con código personalizado"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Error en la aplicación'
    default_code = 'APP_ERROR'
    
    def __init__(self, detail=None, code=None):
        if detail is not None:
            self.detail = {'detail': detail}
        else:
            self.detail = {'detail': self.default_detail}
        
        if code is not None:
            self.detail['code'] = code
        else:
            self.detail['code'] = self.default_code


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Recurso no encontrado'
    default_code = 'NOT_FOUND'


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'No autorizado'
    default_code = 'UNAUTHORIZED'


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Acceso denegado'
    default_code = 'FORBIDDEN'