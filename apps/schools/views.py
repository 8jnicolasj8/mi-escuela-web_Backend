from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from apps.schools.models import School
from apps.schools.serializers import SchoolSerializer


class SchoolViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar escuelas
    """
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    lookup_field = 'id'
    
    def get_permissions(self):
        if self.action == 'list':
            return []
        if self.action == 'retrieve':
            return []
        if self.action == 'buscar':
            return []
        if self.action == 'public':
            return []
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        return SchoolSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset
    
    @action(detail=False, methods=['get'])
    def public(self, request):
        """Lista pública de escuelas activas"""
        schools = School.objects.filter(activa=True)
        serializer = self.get_serializer(schools, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def directivos(self, request, id=None):
        """Get directivos of a school"""
        school = self.get_object()
        from apps.users.models import UserSchool
        directivos = UserSchool.objects.filter(
            escuela=school,
            rol='DIRECTIVO',
            activo=True
        ).select_related('usuario')
        
        from apps.users.serializers import UserSchoolSerializer
        serializer = UserSchoolSerializer(directivos, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def set_directivo(self, request, id=None):
        """Set or add a directivo to the school"""
        school = self.get_object()
        usuario_id = request.data.get('usuario_id')
        
        if not usuario_id:
            return Response({'error': 'usuario_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.users.models import User, UserSchool
        
        try:
            usuario = User.objects.get(id=usuario_id)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        existing = UserSchool.objects.filter(usuario=usuario, escuela=school).first()
        
        if existing:
            existing.rol = 'DIRECTIVO'
            existing.activo = True
            existing.estado_solicitud = 'APROBADO'
            existing.save()
            return Response({'message': 'Usuario actualizado a DIRECTIVO'})
        else:
            UserSchool.objects.create(
                usuario=usuario,
                escuela=school,
                rol='DIRECTIVO',
                activo=True,
                estado_solicitud='APROBADO'
            )
            return Response({'message': 'DIRECTIVO agregado a la escuela'}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def remove_directivo(self, request, id=None):
        """Remove a directivo from a school"""
        school = self.get_object()
        usuario_id = request.data.get('usuario_id')
        
        if not usuario_id:
            return Response({'error': 'usuario_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.users.models import UserSchool
        
        try:
            user_school = UserSchool.objects.get(
                usuario_id=usuario_id,
                escuela=school,
                rol='DIRECTIVO'
            )
            user_school.delete()
            return Response({'message': 'DIRECTIVO eliminado de la escuela'})
        except UserSchool.DoesNotExist:
            return Response({'error': 'Directivo no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def buscar(self, request):
        """
        Búsqueda avanzada de escuelas
        Parámetros:
        - q: búsqueda general en todos los campos
        - provincia: filtrar por provincia
        - localidad: filtrar por localidad
        - cue: buscar por CUE exacto
        - nombre: buscar por nombre
        - limit: máximo de resultados (default 50)
        """
        from django.db.models import Q
        
        queryset = School.objects.all()
        
        # Búsqueda general
        q = request.query_params.get('q', '').strip()
        
        # Filtros específicos
        provincia = request.query_params.get('provincia', '').strip()
        localidad = request.query_params.get('localidad', '').strip()
        cue = request.query_params.get('cue', '').strip()
        nombre = request.query_params.get('nombre', '').strip()
        codigo_postal = request.query_params.get('codigo_postal', '').strip()
        
        # Aplicar búsqueda general
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(cue__icontains=q) |
                Q(provincia__icontains=q) |
                Q(localidad__icontains=q) |
                Q(direccion__icontains=q) |
                Q(telefono__icontains=q) |
                Q(email__icontains=q) |
                Q(codigo_postal__icontains=q)
            )
        
        # Aplicar filtros específicos
        if provincia:
            queryset = queryset.filter(provincia__icontains=provincia)
        
        if localidad:
            queryset = queryset.filter(localidad__icontains=localidad)
        
        if cue:
            queryset = queryset.filter(cue__icontains=cue)
        
        if nombre:
            queryset = queryset.filter(nombre__icontains=nombre)
        
        if codigo_postal:
            queryset = queryset.filter(codigo_postal=codigo_postal)
        
        # Limitar resultados
        try:
            limit = int(request.query_params.get('limit', 50))
            limit = min(limit, 100)  # Maximo 100
        except ValueError:
            limit = 50
        
        queryset = queryset[:limit]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })