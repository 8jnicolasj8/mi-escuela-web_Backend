from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.http import Http404
from apps.users.models import User, UserSchool
from apps.users.serializers import (
    UserSerializer, UserSchoolSerializer, UserSchoolCreateSerializer,
    SolicitudRegistroSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = []
    
    def get_queryset(self):
        user = self.request.user
        school = getattr(self.request, 'escuela', None)
        
        if user.is_superuser:
            queryset = User.objects.all()
            search = self.request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(email__icontains=search) |
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search)
                )
        elif school:
            queryset = User.objects.filter(escuelas__escuela=school).distinct()
        else:
            return User.objects.none()
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user info"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Password required'}, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_password(password)
        request.user.save()
        return Response({'message': 'Password changed successfully'})


class UserSchoolViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios por escuela (UserSchool)
    """
    serializer_class = UserSchoolSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        escuela_from_header = getattr(self.request, 'escuela', None)
        
        # Get user's own relationships - ALWAYS - this is critical for auth
        user_schools = UserSchool.objects.filter(usuario=user, activo=True)
        
        if user.is_superuser:
            # Superadmin can see all users in all schools
            queryset = UserSchool.objects.all()
        elif user_schools.exists():
            # ALWAYS prioritize user's own school relationships first
            # Only DIRECTIVO can see other users
            user_is_directivo = user_schools.filter(rol='DIRECTIVO').exists()
            
            if user_is_directivo and 'escuela' in self.request.headers.get('Host', ''):
                # Only when explicitly requesting OTHER users (via school header)
                user_school = user_schools.filter(rol='DIRECTIVO').first()
                queryset = UserSchool.objects.filter(escuela=user_school.escuela)
            else:
                # For own profile/auth - only see OWN relationships
                queryset = user_schools
        else:
            # No school relationships found
            queryset = UserSchool.objects.none()
        
        rol = self.request.query_params.get('rol')
        if rol:
            queryset = queryset.filter(rol=rol)
        
        activo = self.request.query_params.get('activo')
        if activo:
            queryset = queryset.filter(activo=activo.lower() == 'true')
        
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado_solicitud=estado)
        
        return queryset.select_related('usuario', 'escuela')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserSchoolCreateSerializer
        return UserSchoolSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Actualizar el UserSchool actual del usuario"""
        user_school = UserSchool.objects.filter(
            usuario=request.user,
            activo=True
        ).select_related('escuela').first()
        
        if not user_school:
            return Response({'error': 'UserSchool no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Solo permitir actualizar ciertos campos
        allowed_fields = ['foto_perfil']
        for field in allowed_fields:
            if field in request.data:
                setattr(user_school, field, request.data[field])
        
        user_school.save()
        
        serializer = self.get_serializer(user_school)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Cambiar contraseña"""
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response({'error': 'Nueva contraseña requerida'}, status=status.HTTP_400_BAD_REQUEST)
        
        if old_password:
            # Verificar contraseña actual
            if not request.user.check_password(old_password):
                return Response({'error': 'Contraseña actual incorrecta'}, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_password(new_password)
        request.user.save()
        return Response({'message': 'Contraseña cambiada correctamente'})
    
    def _get_school_from_user(self, request):
        """Helper to get school from user"""
        school = getattr(request, 'escuela', None)
        if not school:
            user_school = UserSchool.objects.filter(
                usuario=request.user,
                activo=True
            ).first()
            if user_school:
                school = user_school.escuela
        return school
    
    @action(detail=False, methods=['get'])
    def directivos(self, request):
        """List directivos of the school"""
        school = self._get_school_from_user(request)
        if request.user.is_superuser:
            directivos = UserSchool.objects.filter(
                rol='DIRECTIVO', activo=True
            ).select_related('usuario', 'escuela')
        elif school:
            directivos = UserSchool.objects.filter(
                escuela=school, rol='DIRECTIVO', activo=True
            ).select_related('usuario')
        else:
            return Response({'error': 'School required'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(directivos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def docentes(self, request):
        """List docentes of the school"""
        school = self._get_school_from_user(request)
        if request.user.is_superuser:
            docentes = UserSchool.objects.filter(
                rol='DOCENTE', activo=True
            ).select_related('usuario', 'escuela')
        elif school:
            docentes = UserSchool.objects.filter(
                escuela=school, rol='DOCENTE', activo=True
            ).select_related('usuario')
        else:
            return Response({'error': 'School required'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(docentes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def alumnos(self, request):
        """List alumnos of the school"""
        school = self._get_school_from_user(request)
        if request.user.is_superuser:
            alumnos = UserSchool.objects.filter(
                rol='ALUMNO', activo=True
            ).select_related('usuario', 'escuela')
        elif school:
            alumnos = UserSchool.objects.filter(
                escuela=school, rol='ALUMNO', activo=True
            ).select_related('usuario')
        else:
            return Response({'error': 'School required'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(alumnos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def solicitudes(self, request):
        """List pending solicitudes"""
        school = self._get_school_from_user(request)
        if request.user.is_superuser:
            solicitudes = UserSchool.objects.filter(
                estado_solicitud='PENDIENTE'
            ).select_related('usuario', 'escuela')
        elif school:
            solicitudes = UserSchool.objects.filter(
                escuela=school, estado_solicitud='PENDIENTE'
            ).select_related('usuario', 'escuela')
        else:
            return Response({'error': 'School required'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(solicitudes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Approve a solicitud"""
        try:
            user_school = self.get_object()
            
            user_school.estado_solicitud = 'APROBADO'
            user_school.activo = True
            
            rol = request.data.get('rol')
            if rol:
                user_school.rol = rol
            
            user_school.save()
            
            return Response({'message': 'Solicitud aprobada'})
        except Http404:
            return Response({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """Reject a solicitud"""
        try:
            user_school = self.get_object()
            user_school.estado_solicitud = 'RECHAZADO'
            user_school.save()
            return Response({'message': 'Solicitud rechazada'})
        except Http404:
            return Response({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class SolicitudViewSet(viewsets.GenericViewSet):
    """
    ViewSet público para registrar solicitudes de nuevos usuarios
    """
    serializer_class = SolicitudRegistroSerializer
    permission_classes = []
    
    def create(self, request):
        """Crear solicitud de registro"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Solicitud enviada.ungguarde la aprobación de un directivo.'},
            status=status.HTTP_201_CREATED
        )


# Function-based views for linking system
from rest_framework.decorators import api_view, permission_classes

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_codigo_view(request):
    """Genera un código de vinculación para un hijo (APODERADO) o para sí mismo (ALUMNO)"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True
    ).first()
    
    if not user_school:
        return Response({'error': 'UserSchool no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    # Case 1: APODERADO generating code for their hijo
    if user_school.rol == 'APODERADO':
        hijo_id = request.data.get('hijo_id')
        if not hijo_id:
            return Response({'error': 'hijo_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            hijo = UserSchool.objects.get(id=hijo_id, tutor=user_school, activo=True)
        except UserSchool.DoesNotExist:
            return Response({'error': 'Hijo no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        codigo = hijo.generar_codigo_vinculacion()
        
        return Response({
            'codigo': codigo,
            'hijo': hijo.nombre_completo,
            'message': 'Código generado correctamente'
        })
    
    # Case 2: ALUMNO generating code for themselves
    elif user_school.rol == 'ALUMNO':
        codigo = user_school.generar_codigo_vinculacion()
        
        return Response({
            'codigo': codigo,
            'message': 'Tu código de vinculación generado correctamente'
        })
    
    else:
        return Response({'error': 'Rol no autorizado para generar código'}, status=status.HTTP_403_FORBIDDEN)
    
    return Response({
        'codigo': codigo,
        'hijo': hijo.nombre_completo,
        'message': 'Código generado correctamente'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vincular_alumno_view(request):
    """Vincula un alumno a un apoderado mediante código"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='ALUMNO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres alumno'}, status=status.HTTP_403_FORBIDDEN)
    
    codigo = request.data.get('codigo', '').strip().upper()
    if not codigo:
        return Response({'error': 'Código requerido'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Find UserSchool with this code (should be an APODERADO)
    tutor = UserSchool.objects.filter(
        codigo_vinculacion=codigo,
        rol='APODERADO',
        activo=True
    ).first()
    
    if not tutor:
        return Response({'error': 'Código inválido'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if already linked
    if user_school.tutor:
        return Response({'error': 'Ya estás vinculado a otro apoderao'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Link the student
    user_school.tutor = tutor
    user_school.save()
    
    return Response({
        'message': f'Vinculado correctamente a {tutor.nombre_completo}',
        'tutor': tutor.nombre_completo
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mi_codigo_view(request):
    """Get or generate the current user's código de vinculación (for ALUMNO)"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='ALUMNO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres alumno'}, status=status.HTTP_403_FORBIDDEN)
    
    # If code doesn't exist, generate one
    if not user_school.codigo_vinculacion:
        user_school.generar_codigo_vinculacion()
    
    return Response({
        'codigo': user_school.codigo_vinculacion,
        'tutor_actual': user_school.tutor.nombre_completo if user_school.tutor else None
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vincular_hijo_view(request):
    """APODERADO vincula a un hijo mediante el código del hijo"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='APODERADO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres apoderao'}, status=status.HTTP_403_FORBIDDEN)
    
    codigo = request.data.get('codigo', '').strip().upper()
    if not codigo:
        return Response({'error': 'Código requerido'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Find ALUMNO with this code
    hijo = UserSchool.objects.filter(
        codigo_vinculacion=codigo,
        rol='ALUMNO',
        activo=True
    ).first()
    
    if not hijo:
        return Response({'error': 'Código inválido o no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if already linked to another tutor
    if hijo.tutor and hijo.tutor != user_school:
        return Response({'error': f'{hijo.nombre_completo} ya está vinculado a otro apoderao'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Link the child
    hijo.tutor = user_school
    hijo.save()
    
    return Response({
        'message': f'{hijo.nombre_completo} vinculado correctamente',
        'hijo': hijo.nombre_completo
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_hijos_view(request):
    """Get hijos del apoderao"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='APODERADO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres apoderao'}, status=status.HTTP_403_FORBIDDEN)
    
    hijos = UserSchool.objects.filter(
        tutor=user_school,
        activo=True
    ).select_related('usuario', 'escuela')
    
    result = []
    for hijo in hijos:
        # Get curso info from Alumno model
        from apps.academics.models import Alumno
        inscripciones = Alumno.objects.filter(
            usuario_escuela=hijo,
            activo=True
        ).select_related('curso')
        
        cursos = []
        for ins in inscripciones:
            cursos.append({
                'id': ins.curso.id,
                'nombre': ins.curso.nombre_completo
            })
        
        result.append({
            'id': str(hijo.id),
            'nombre': hijo.nombre_completo,
            'email': hijo.usuario.email if hijo.usuario else None,
            'cursos': cursos,
            'codigo': hijo.codigo_vinculacion
        })
    
    return Response(result)