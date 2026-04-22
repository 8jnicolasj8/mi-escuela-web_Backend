from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from apps.academics.models import Anio, Curso, Materia, Alumno, Classroom, Publicacion, Periodo, Nota, EscalaEvaluacion, BloqueHorario, Horario, Actividad, Entrega, DIAS_SEMANA
from apps.academics.serializers import (
    AnioSerializer, CursoSerializer, MateriaSerializer,
    AlumnoSerializer, ClassroomSerializer, PublicacionSerializer,
    PeriodoSerializer, NotaSerializer, EscalaEvaluacionSerializer,
    BloqueHorarioSerializer, HorarioSerializer, ActividadSerializer, EntregaSerializer
)
from apps.users.models import UserSchool
from apps.core.exceptions import NotFoundException


class AnioViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar años académicos"""
    serializer_class = AnioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Anio.objects.all().order_by('-numero')
        
        # Get school from user's UserSchool
        from apps.users.models import UserSchool
        user_school = UserSchool.objects.filter(
            usuario=self.request.user,
            activo=True
        ).first()
        if user_school:
            school = user_school.escuela
        else:
            return Anio.objects.none()
        return Anio.objects.filter(escuela=school).order_by('-numero')


class CursoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar cursos"""
    serializer_class = CursoSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'patch', 'head', 'options']
    
    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            import traceback
            return Response(
                {'error': str(e), 'trace': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return Curso.objects.all().select_related('anio')
        
        # Get school from user's UserSchool
        user_schools = UserSchool.objects.filter(
            usuario=user,
            activo=True
        )
        
        if not user_schools.exists():
            return Curso.objects.none()
        
        school = user_schools.first().escuela
        return Curso.objects.filter(anio__escuela=school).select_related('anio')
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def crear_multiple(self, request):
        """
        Crear múltiples divisiones para un año
        Expected payload:
        {
            "anio": "uuid-del-año",
            "ciclo": "SECUNDARIO",
            "divisiones": [
                {"division": "A", "turno": "MANIANA"},
                {"division": "B", "turno": "TARDE"},
                {"division": "C", "turno": "MANIANA"}
            ]
        }
        """
        anio_id = request.data.get('anio')
        ciclo = request.data.get('ciclo', 'SECUNDARIO')
        divisiones = request.data.get('divisiones', [])
        
        if not anio_id or not divisiones:
            return Response(
                {'error': 'Se requiere año y lista de divisiones'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            anio = Anio.objects.get(id=anio_id)
        except Anio.DoesNotExist:
            return Response({'error': 'Año no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        cursos_creados = []
        cursos_existentes = []
        for div in divisiones:
            # Try to create - if it already exists with same anio, division AND turno, it will fail
            try:
                curso = Curso.objects.create(
                    anio=anio,
                    division=div.get('division', ''),
                    turno=div.get('turno', 'MANIANA'),
                    ciclo=ciclo,
                    activo=True
                )
                cursos_creados.append(CursoSerializer(curso).data)
            except Exception:
                # If it already exists, get it
                curso = Curso.objects.filter(
                    anio=anio,
                    division=div.get('division', ''),
                    turno=div.get('turno', 'MANIANA')
                ).first()
                if curso:
                    cursos_existentes.append(CursoSerializer(curso).data)
        
        return Response({
            'message': f'{len(cursos_creados)} cursos creados, {len(cursos_existentes)} ya existían',
            'cursos': cursos_creados + cursos_existentes,
            'creados': len(cursos_creados),
            'existentes': len(cursos_existentes)
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def agregar_alumno(self, request, pk=None):
        """Agregar un alumno al curso"""
        curso = self.get_object()
        alumno_id = request.data.get('alumno_id')
        
        if not alumno_id:
            return Response({'error': 'alumno_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps.users.models import UserSchool
            user_school = UserSchool.objects.get(id=alumno_id, rol='ALUMNO', activo=True)
        except UserSchool.DoesNotExist:
            return Response({'error': 'Alumno no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create the enrollment
        from apps.academics.models import Alumno
        Alumno.objects.create(
            usuario_escuela=user_school,
            curso=curso,
            activo=True
        )
        
        return Response({'message': 'Alumno agregado al curso'})
    
    @action(detail=True, methods=['post'])
    def quitar_alumno(self, request, pk=None):
        """Quitar un alumno del curso"""
        curso = self.get_object()
        alumno_id = request.data.get('alumno_id')
        
        if not alumno_id:
            return Response({'error': 'alumno_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.academics.models import Alumno
        try:
            alumno = Alumno.objects.get(id=alumno_id, curso=curso)
            alumno.delete()
            return Response({'message': 'Alumno quitado del curso'})
        except Alumno.DoesNotExist:
            return Response({'error': 'Alumno no encontrado en este curso'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def alumnos(self, request, pk=None):
        """Get list of students in this course"""
        curso = self.get_object()
        from apps.academics.models import Alumno
        from apps.users.serializers import UserSchoolSerializer
        
        # Get current logged-in user
        current_user_school = UserSchool.objects.filter(
            usuario=request.user,
            activo=True,
            rol='ALUMNO'
        ).first()
        
        inscripciones = Alumno.objects.filter(
            curso=curso,
            activo=True
        ).select_related('usuario_escuela', 'usuario_escuela__usuario')
        
        # Separate current user from others
        current_user_alumno = None
        otros_alumnos = []
        
        for ins in inscripciones:
            us = ins.usuario_escuela
            alum_data = {
                'id': str(us.id),
                'nombre': us.nombre_completo,
                'email': us.usuario.email if us.usuario else '',
                'foto_perfil_url': us.foto_perfil.url if us.foto_perfil else None
            }
            
            if current_user_school and us.id == current_user_school.id:
                current_user_alumno = alum_data
            else:
                otros_alumnos.append(alum_data)
        
        # Sort others alphabetically
        otros_alumnos.sort(key=lambda x: x['nombre'].lower())
        
        # Build result: current user first, then others
        result = []
        if current_user_alumno:
            result.append(current_user_alumno)
        result.extend(otros_alumnos)
        
        return Response(result)


class MateriaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar materias"""
    serializer_class = MateriaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Import here to avoid circular issues
        from apps.users.models import UserSchool
        
        if user.is_superuser:
            return Materia.objects.all().select_related('curso', 'docente')
        
        # Get user's school relationship
        user_schools = UserSchool.objects.filter(usuario=user, activo=True)
        
        if not user_schools.exists():
            return Materia.objects.none()
        
        # Get the school
        school = getattr(self.request, 'escuela', None)
        if not school:
            # Try to get from UserSchool
            user_school = user_schools.first()
            if user_school:
                school = user_school.escuela
        
        if not school:
            return Materia.objects.none()
        
        # If user is DIRECTIVO, can see all materias in their school
        is_directivo = user_schools.filter(rol='DIRECTIVO').exists()
        if is_directivo:
            return Materia.objects.filter(curso__anio__escuela=school).select_related('curso', 'docente')
        
        # Otherwise (DOCENTE), only see their own materias
        return Materia.objects.filter(docente=user_school.first(), curso__anio__escuela=school).select_related('curso', 'docente')


class AlumnoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar alumnos"""
    serializer_class = AlumnoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        school = getattr(self.request, 'escuela', None)
        if self.request.user.is_superuser:
            return Alumno.objects.all().select_related('usuario_escuela__usuario', 'curso')
        if not school:
            return Alumno.objects.none()
        return Alumno.objects.filter(curso__anio__escuela=school).select_related('usuario_escuela__usuario', 'curso')


class ClassroomViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar aulas virtuales"""
    serializer_class = ClassroomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Classroom.objects.all().select_related('materia')
        
        user_school = UserSchool.objects.filter(
            usuario=self.request.user,
            activo=True
        ).first()
        
        if user_school:
            return Classroom.objects.filter(
                materia__curso__anio__escuela=user_school.escuela
            ).select_related('materia')
        
        # For docentes, also return their classrooms
        if user_school and user_school.rol == 'DOCENTE':
            return Classroom.objects.filter(
                materia__docente=user_school
            ).select_related('materia')
        
        return Classroom.objects.none()
    
    @action(detail=False, methods=['get'])
    def by_curso(self, request):
        """Get classrooms by curso"""
        curso_id = request.query_params.get('curso')
        if not curso_id:
            return Response({'error': 'curso required'}, status=status.HTTP_400_BAD_REQUEST)
        
        classrooms = self.get_queryset().filter(materia__curso_id=curso_id)
        serializer = self.get_serializer(classrooms, many=True)
        return Response(serializer.data)


class PublicacionViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar publicaciones"""
    serializer_class = PublicacionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        school = getattr(self.request, 'escuela', None)
        if self.request.user.is_superuser:
            return Publicacion.objects.all().select_related('classroom', 'autor__usuario')
        if not school:
            return Publicacion.objects.none()
        return Publicacion.objects.filter(
            classroom__materia__curso__anio__escuela=school
        ).select_related('classroom', 'autor__usuario')
    
    def perform_create(self, serializer):
        user_school = self.request.user.userschool_set.first()
        if not user_school:
            raise NotFoundException('User not associated with a school')
        serializer.save(autor=user_school)
    
    @action(detail=False, methods=['get'])
    def by_classroom(self, request):
        """Get publications by classroom"""
        classroom_id = request.query_params.get('classroom')
        if not classroom_id:
            return Response({'error': 'classroom required'}, status=status.HTTP_400_BAD_REQUEST)
        
        publicaciones = self.get_queryset().filter(classroom_id=classroom_id)
        serializer = self.get_serializer(publicaciones, many=True)
        return Response(serializer.data)


class PeriodoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar períodos académicos"""
    serializer_class = PeriodoSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        print(f'=== PeriodoViewSet.list() called ===')
        print(f'  User: {request.user}')
        print(f'  Is authenticated: {request.user.is_authenticated}')
        print(f'  Query params: {request.query_params}')
        print(f'  Headers: {dict(request.headers)}')
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Periodo.objects.all()
        
        # Filter by year if provided
        anio = self.request.query_params.get('anio')
        if anio:
            queryset = queryset.filter(anio=int(anio))
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return Periodo.objects.none()
        
        if self.request.user.is_superuser:
            return queryset.order_by('-anio', 'numero')
        
        user_schools = UserSchool.objects.filter(
            usuario=self.request.user,
            activo=True
        )
        # Si es DIRECTIVO, ve todos los períodos de su escuela
        es_directivo = user_schools.filter(rol='DIRECTIVO').exists()
        if es_directivo:
            school = user_schools.first().escuela
            return queryset.filter(escuela=school).order_by('-anio', 'numero')
        # Docentes y alumnos solo ven períodos activos
        if user_schools.exists():
            school = user_schools.first().escuela
            return queryset.filter(escuela=school, activo=True).order_by('-anio', 'numero')
        return Periodo.objects.none()
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """Get períodos activos actuales"""
        queryset = self.get_queryset().filter(activo=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def puede_cargar(self, request, pk=None):
        """Verifica si el período está en fecha de carga de notas"""
        periodo = self.get_object()
        return Response({
            'puede_cargar': periodo.puede_cargar_notas,
            'estado': periodo.estado
        })


class NotaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar notas"""
    serializer_class = NotaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return Nota.objects.all().select_related('periodo', 'materia', 'alumno__usuario_escuela')
        
        user_schools = UserSchool.objects.filter(
            usuario=user,
            activo=True
        )
        
        if not user_schools.exists():
            return Nota.objects.none()
        
        user_school = user_schools.first()
        
        # DIRECTIVO y DOCENTE pueden ver todas las notas de su escuela
        if user_school.rol in ['DIRECTIVO', 'DOCENTE']:
            school = user_school.escuela
            return Nota.objects.filter(
                periodo__escuela=school
            ).select_related('periodo', 'materia', 'alumno__usuario_escuela')
        
        # ALUMNO solo ve sus propias notas
        return Nota.objects.filter(
            alumno__usuario_escuela=user_school
        ).select_related('periodo', 'materia', 'alumno__usuario_escuela')
    
    def get_permissions(self):
        # Por ahora solo DIRECTIVO puede crear/editar notas
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def by_periodo(self, request):
        """Get notas por período"""
        periodo_id = request.query_params.get('periodo')
        if not periodo_id:
            return Response({'error': 'periodo required'}, status=status.HTTP_400_BAD_REQUEST)
        
        notas = self.get_queryset().filter(periodo_id=periodo_id)
        serializer = self.get_serializer(notas, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_materia(self, request):
        """Get notas por materia"""
        materia_id = request.query_params.get('materia')
        periodo_id = request.query_params.get('periodo')
        
        if not materia_id or not periodo_id:
            return Response({'error': 'materia and periodo required'}, status=status.HTTP_400_BAD_REQUEST)
        
        notas = self.get_queryset().filter(
            periodo_id=periodo_id,
            materia_id=materia_id
        )
        serializer = self.get_serializer(notas, many=True)
        return Response(serializer.data)


class EscalaEvaluacionViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar escala de evaluación"""
    serializer_class = EscalaEvaluacionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return EscalaEvaluacion.objects.all()
        
        user_school = UserSchool.objects.filter(
            usuario=self.request.user,
            activo=True,
            rol='DIRECTIVO'
        ).first()
        
        if user_school:
            return EscalaEvaluacion.objects.filter(escuela=user_school.escuela)
        return EscalaEvaluacion.objects.none()
    
    def get_object(self):
        # Si no existe, crear una con valores por defecto
        obj = super().get_object()
        return obj
    
    @action(detail=False, methods=['get'])
    def mi_escala(self, request):
        """Get escala de evaluación de la escuela actual"""
        user_school = UserSchool.objects.filter(
            usuario=request.user,
            activo=True
        ).first()
        
        if not user_school:
            return Response({'error': 'User not associated with school'}, status=status.HTTP_400_BAD_REQUEST)
        
        escala, _ = EscalaEvaluacion.objects.get_or_create(
            escuela=user_school.escuela,
            defaults={'limite_desaprobado': 6}
        )
        serializer = self.get_serializer(escala)
        return Response(serializer.data)


class BloqueHorarioViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar bloques de horario"""
    serializer_class = BloqueHorarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return BloqueHorario.objects.all().order_by('orden', 'hora_inicio')
        
        user_school = UserSchool.objects.filter(
            usuario=self.request.user,
            activo=True
        ).first()
        
        if not user_school:
            return BloqueHorario.objects.none()
        
        if user_school.rol == 'DIRECTIVO':
            return BloqueHorario.objects.filter(escuela=user_school.escuela).order_by('orden', 'hora_inicio')
        
        # For ALUMNO, DOCENTE, APODERADO - return all blocks (they just need to see them)
        return BloqueHorario.objects.all().order_by('orden', 'hora_inicio')
    
    def perform_create(self, serializer):
        user_school = UserSchool.objects.filter(
            usuario=self.request.user,
            activo=True,
            rol='DIRECTIVO'
        ).first()
        
        if user_school:
            serializer.save(escuela=user_school.escuela)
        else:
            raise serializers.ValidationError({"error": "No tienes una escuela asignada"})
    
    def perform_update(self, serializer):
        user_school = UserSchool.objects.filter(
            usuario=self.request.user,
            activo=True,
            rol='DIRECTIVO'
        ).first()
        
        if user_school:
            serializer.save(escuela=user_school.escuela)
        else:
            raise serializers.ValidationError({"error": "No tienes una escuela asignada"})


class HorarioViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar horarios de cursos"""
    serializer_class = HorarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Horario.objects.all().select_related('curso', 'bloque', 'materia', 'materia__docente')
        
        user_school = UserSchool.objects.filter(
            usuario=self.request.user,
            activo=True
        ).first()
        
        if user_school and user_school.rol == 'DIRECTIVO':
            return Horario.objects.filter(
                curso__anio__escuela=user_school.escuela
            ).select_related('curso', 'bloque', 'materia', 'materia__docente')
        return Horario.objects.none()
    
    @action(detail=False, methods=['get'])
    def by_curso(self, request):
        """Get horarios by curso"""
        curso_id = request.query_params.get('curso')
        if not curso_id:
            return Response({'error': 'curso required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            curso_id_int = int(curso_id)
            horarios = self.get_queryset().filter(curso_id=curso_id_int)
        except ValueError:
            # Try as UUID
            horarios = self.get_queryset().filter(curso_id=curso_id)
        
        try:
            serializer = self.get_serializer(horarios, many=True)
            return Response(serializer.data)
        except Exception as e:
            import traceback
            return Response({'error': str(e), 'trace': traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_cursos_view(request):
    """Get cursos donde el usuario tiene acceso"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True
    ).first()
    
    if not user_school:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_403_FORBIDDEN)
    
    if user_school.rol == 'DOCENTE':
        return mis_cursos_docente_view(user_school)
    elif user_school.rol == 'ALUMNO':
        return mis_cursos_alumno_view(user_school)
    else:
        return Response({'error': 'Sin acceso'}, status=status.HTTP_403_FORBIDDEN)


def mis_cursos_docente_view(user_school):
    """Get cursos donde el docente tiene materias asignadas"""
    materias = Materia.objects.filter(
        docente=user_school,
        curso__anio__escuela=user_school.escuela,
        activa=True
    ).select_related('curso', 'curso__anio')
    
    cursos = {}
    for materia in materias:
        curso = materia.curso
        if curso.id not in cursos:
            cursos[curso.id] = {
                'id': curso.id,
                'nombre_completo': curso.nombre_completo,
                'anio_numero': curso.anio.numero,
                'division': curso.division,
                'turno': curso.turno,
                'ciclo': curso.ciclo,
                'materias': []
            }
        
        cursos[curso.id]['materias'].append({
            'id': materia.id,
            'nombre': materia.nombre,
            'nombre_corto': materia.nombre_corto
        })
    
    return Response(list(cursos.values()))


def mis_cursos_alumno_view(user_school):
    """Get cursos/materias donde el alumno está inscripto"""
    from apps.academics.models import Alumno, Materia
    
    inscripciones = Alumno.objects.filter(
        usuario_escuela=user_school,
        activo=True
    ).select_related('curso', 'curso__anio')
    
    result = []
    for ins in inscripciones:
        curso = ins.curso
        materias = Materia.objects.filter(
            curso=curso,
            activa=True
        ).select_related('docente', 'docente__usuario')
        
        for materia in materias:
            nombre_docente = ''
            if materia.docente and materia.docente.usuario:
                try:
                    u = materia.docente.usuario
                    nombre_docente = (u.first_name or '') + ' ' + (u.last_name or '')
                    nombre_docente = nombre_docente.strip()
                except:
                    pass
            result.append({
                'id': materia.id,
                'materia_id': materia.id,
                'materia_nombre': materia.nombre,
                'curso_id': curso.id,
                'curso_nombre': curso.nombre_completo,
                'docente_nombre': nombre_docente,
            })
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_actividades_alumno_view(request):
    """Get actividades para el alumno"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='ALUMNO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres alumno'}, status=status.HTTP_403_FORBIDDEN)
    
    from apps.academics.models import Alumno, Classroom, Entrega, Materia
    
    materia_id = request.query_params.get('materia')
    curso_id = request.query_params.get('curso')
    
    # Get cursos where the student is enrolled
    if materia_id:
        # Filter by specific materia - get classrooms directly for this materia
        classroom_ids = Classroom.objects.filter(
            materia_id=materia_id
        ).values_list('id', flat=True)
    elif curso_id:
        inscripciones = Alumno.objects.filter(
            usuario_escuela=user_school,
            curso_id=curso_id,
            activo=True
        )
        curso_ids = [curso_id]
        
        classroom_ids = Classroom.objects.filter(
            materia__curso_id__in=curso_ids
        ).values_list('id', flat=True)
    else:
        # Get all enrollments
        inscripciones = Alumno.objects.filter(
            usuario_escuela=user_school,
            activo=True
        )
        curso_ids = list(inscripciones.values_list('curso_id', flat=True))
        
        classroom_ids = Classroom.objects.filter(
            materia__curso_id__in=curso_ids
        ).values_list('id', flat=True)
    
    actividades = Actividad.objects.filter(
        classroom_id__in=classroom_ids
    ).order_by('fecha_entrega')
    
    result = []
    for act in actividades:
        entrega = Entrega.objects.filter(
            actividad=act,
            alumno=user_school
        ).first()
        
        result.append({
            'id': act.id,
            'titulo': act.titulo,
            'tipo': act.tipo,
            'descripcion': act.descripcion,
            'fecha_entrega': act.fecha_entrega.strftime('%Y-%m-%dT%H:%M') if act.fecha_entrega else None,
            'classroom_id': act.classroom_id,
            'entrega': {
                'id': entrega.id,
                'estado': 'entregado' if entrega else None,
                'nota': float(entrega.nota) if entrega and entrega.nota else None
            } if entrega else None
        })
    
    return Response(result)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def entregas_alumno_view(request):
    """Entregar actividad (alumno)"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='ALUMNO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres alumno'}, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        return mis_actividades_alumno_view(request)
    
    actividad_id = request.data.get('actividad_id')
    if not actividad_id:
        return Response({'error': 'actividad_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    from apps.academics.models import Entrega
    
    actividad = Actividad.objects.filter(id=actividad_id).first()
    if not actividad:
        return Response({'error': 'Actividad no encontrada'}, status=status.HTTP_404_NOT_FOUND)
    
    entrega, created = Entrega.objects.get_or_create(
        actividad=actividad,
        alumno=user_school,
        defaults={'texto': '', 'comentario': ''}
    )
    
    entrega.texto = request.data.get('texto', entrega.texto)
    entrega.save()
    
    serializer = EntregaSerializer(entrega)
    return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_notas_view(request):
    """Get notas del alumno"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='ALUMNO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres alumno'}, status=status.HTTP_403_FORBIDDEN)
    
    from apps.academics.models import Nota
    
    notas = Nota.objects.filter(
        alumno__usuario_escuela=user_school
    ).select_related('materia', 'periodo')
    
    result = []
    for nota in notas:
        result.append({
            'id': nota.id,
            'materia': nota.materia.nombre if nota.materia else None,
            'periodo': nota.periodo.nombre if nota.periodo else None,
            'nota': float(nota.valor) if nota.valor else None,
            'observaciones': nota.observaciones
        })
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_hijos_view(request):
    """Get hijos del apoderado"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='APODERADO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres apoderado'}, status=status.HTTP_403_FORBIDDEN)
    
    from apps.users.models import UserSchool
    
    hijos = UserSchool.objects.filter(
        tutor=user_school,
        activo=True
    ).select_related('usuario')
    
    result = []
    for hijo in hijos:
        result.append({
            'id': str(hijo.id),
            'nombre': hijo.nombre_completo,
            'email': hijo.usuario.email if hijo.usuario else None
        })
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notas_hijo_view(request, hijо_id):
    """Get notas de un hijo específico"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='APODERADO'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres apoderado'}, status=status.HTTP_403_FORBIDDEN)
    
    from apps.users.models import UserSchool
    from apps.academics.models import Nota
    
    hijo = UserSchool.objects.filter(
        id=hijо_id,
        tutor=user_school,
        activo=True
    ).first()
    
    if not hijo:
        return Response({'error': 'Hijo no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    notas = Nota.objects.filter(
        alumno__usuario_escuela=hijo
    ).select_related('materia', 'periodo')
    
    result = []
    for nota in notas:
        result.append({
            'id': nota.id,
            'materia': nota.materia.nombre if nota.materia else None,
            'periodo': nota.periodo.nombre if nota.periodo else None,
            'nota': float(nota.valor) if nota.valor else None,
            'observaciones': nota.observaciones
        })
    
    return Response({
        'hijo': {'id': hijo.id, 'nombre': hijo.nombre_completo},
        'notas': result
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_classrooms_view(request):
    """Get classrooms donde el docente tiene materias asignadas"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='DOCENTE'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres docente'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get classrooms where docente teaches
    classroom = Classroom.objects.filter(
        materia__docente=user_school,
        permite_publicaciones=True
    ).select_related('materia', 'materia__curso')
    
    result = []
    for cr in classroom:
        result.append({
            'id': str(cr.id),
            'materia_nombre': cr.materia.nombre,
            'curso_nombre': cr.materia.curso.nombre_completo,
            'permite_tareas': cr.permite_tareas,
            'permite_publicaciones': cr.permite_publicaciones,
        })
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_alumnos_view(request):
    """Get alumnos de los cursos donde el docente tiene materias"""
    curso_id = request.query_params.get('curso')
    if not curso_id:
        return Response({'error': 'curso required'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='DOCENTE'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres docente'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get curso
    try:
        curso_id_int = int(curso_id)
        curso = Curso.objects.get(id=curso_id_int)
    except:
        return Response({'error': 'Curso no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    # Verify docente has materia in this curso
    materias_docente = Materia.objects.filter(
        docente=user_school,
        curso=curso,
        activa=True
    )
    
    if not materias_docente.exists():
        return Response({'error': 'No tenés materias en este curso'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get all alumnos from curso
    alumnos = Alumno.objects.filter(
        curso=curso,
        activo=True
    ).select_related('usuario_escuela__usuario')
    
    result = []
    for aluno in alumnos:
        result.append({
            'id': aluno.id,
            'usuario_escuela': str(aluno.usuario_escuela.id),
            'nombre_completo': aluno.usuario_escuela.nombre_completo,
            'dni': aluno.usuario_escuela.usuario.dni if aluno.usuario_escuela.usuario else None,
            'activo': aluno.activo
        })
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_horarios_view(request):
    """Get horarios del usuario"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True
    ).first()
    
    if not user_school:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_403_FORBIDDEN)
    
    if user_school.rol == 'DOCENTE':
        return mis_horarios_docente_view(user_school)
    elif user_school.rol == 'ALUMNO':
        return mis_horarios_alumno_view(user_school)
    else:
        return Response({'error': 'Sin acceso'}, status=status.HTTP_403_FORBIDDEN)


def mis_horarios_alumno_view(user_school):
    """Get horarios del alumno"""
    from apps.academics.models import Alumno
    
    # Get cursos where the student is enrolled
    inscripciones = Alumno.objects.filter(
        usuario_escuela=user_school,
        activo=True
    ).values_list('curso_id', flat=True)
    
    # Get horarios for those cursos
    horarios = Horario.objects.filter(
        curso_id__in=inscripciones
    ).select_related('curso', 'bloque', 'materia')
    
    result = []
    for h in horarios:
        result.append({
            'id': h.id,
            'curso': {
                'id': h.curso.id,
                'nombre': h.curso.nombre_completo
            },
            'dia_semana': h.dia_semana,
            'dia_nombre': DIAS_SEMANA[h.dia_semana][1] if h.dia_semana < len(DIAS_SEMANA) else '',
            'bloque': {
                'id': h.bloque.id,
                'hora_inicio': h.bloque.hora_inicio.strftime('%H:%M'),
                'hora_fin': h.bloque.hora_fin.strftime('%H:%M')
            },
            'bloque_horario': h.bloque.hora_inicio.strftime('%H:%M'),
            'materia': h.materia.nombre if h.materia else None
        })
    
    return Response(result)


def mis_horarios_docente_view(user_school):
    """Get horarios del docente (solo sus bloques)"""
    materias = Materia.objects.filter(
        docente=user_school,
        curso__anio__escuela=user_school.escuela,
        activa=True
    ).values_list('id', flat=True)
    
    horarios = Horario.objects.filter(
        materia_id__in=materias
    ).select_related('curso', 'bloque', 'materia')
    
    result = []
    for h in horarios:
        result.append({
            'id': h.id,
            'curso': {
                'id': h.curso.id,
                'nombre': h.curso.nombre_completo
            },
            'dia_semana': h.dia_semana,
            'dia_nombre': DIAS_SEMANA[h.dia_semana][1] if h.dia_semana < len(DIAS_SEMANA) else '',
            'bloque': {
                'id': h.bloque.id,
                'hora_inicio': h.bloque.hora_inicio.strftime('%H:%M'),
                'hora_fin': h.bloque.hora_fin.strftime('%H:%M')
            },
            'materia': {
                'id': h.materia.id,
                'nombre': h.materia.nombre,
                'nombre_corto': h.materia.nombre_corto
            }
        })
    
    return Response(result)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def actividades_view(request):
    """CRUD de actividades"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='DOCENTE'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres docente'}, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        classroom_id = request.query_params.get('classroom')
        if not classroom_id:
            return Response({'error': 'classroom required'}, status=status.HTTP_400_BAD_REQUEST)
        
        actividades = Actividad.objects.filter(
            classroom_id=classroom_id,
            classroom__materia__docente=user_school
        ).order_by('-created_at')
        
        serializer = ActividadSerializer(actividades, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        classroom_id = request.data.get('classroom')
        if not classroom_id:
            return Response({'error': 'classroom required'}, status=status.HTTP_400_BAD_REQUEST)
        
        classroom = Classroom.objects.filter(
            id=classroom_id,
            materia__docente=user_school
        ).first()
        
        if not classroom:
            return Response({'error': 'No tenes acceso a este classroom'}, status=status.HTTP_403_FORBIDDEN)
        
        actividad = Actividad.objects.create(
            classroom=classroom,
            titulo=request.data.get('titulo'),
            tipo=request.data.get('tipo', 'TAREA'),
            descripcion=request.data.get('descripcion', ''),
            fecha_entrega=request.data.get('fecha_entrega') or None,
            creado_por=user_school
        )
        
        serializer = ActividadSerializer(actividad)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendario_view(request):
    """Get actividades for docente's calendar"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='DOCENTE'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres docente'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get classrooms where docente teaches
    classroom_ids = Classroom.objects.filter(
        materia__docente=user_school
    ).values_list('id', flat=True)
    
    actividades = Actividad.objects.filter(
        classroom_id__in=classroom_ids
    ).exclude(fecha_entrega__isnull=True).order_by('fecha_entrega')
    
    result = []
    for act in actividades:
        result.append({
            'id': act.id,
            'titulo': act.titulo,
            'fecha': act.fecha_entrega.strftime('%Y-%m-%d') if act.fecha_entrega else None,
            'tipo': act.tipo,
            'classroom': act.classroom_id,
            'materia': act.classroom.materia.nombre if act.classroom else None
        })
    
    return Response(result)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def entregas_view(request, actividad_id):
    """Get or create entregas for an actividad"""
    user_school = UserSchool.objects.filter(
        usuario=request.user,
        activo=True,
        rol='DOCENTE'
    ).first()
    
    if not user_school:
        return Response({'error': 'No eres docente'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get actividad and verify docente owns it
    actividad = Actividad.objects.filter(
        id=actividad_id,
        classroom__materia__docente=user_school
    ).first()
    
    if not actividad:
        return Response({'error': 'Actividad no encontrada'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        entregas = Entrega.objects.filter(
            actividad=actividad
        ).select_related('alumno')
        
        result = []
        for ent in entregas:
            result.append({
                'id': ent.id,
                'alumno_id': ent.alumno_id,
                'alumno_nombre': ent.alumno.nombre_completo if ent.alumno else None,
                'nota': float(ent.nota) if ent.nota else None,
                'comentario': ent.comentario,
                'created_at': ent.created_at.strftime('%Y-%m-%d %H:%M') if ent.created_at else None
            })
        
        return Response(result)
    
    elif request.method == 'POST':
        # Corregir entrega
        entrega_id = request.data.get('entrega_id')
        if not entrega_id:
            return Response({'error': 'entrega_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        entrega = Entrega.objects.filter(
            id=entrega_id,
            actividad=actividad
        ).first()
        
        if not entrega:
            return Response({'error': 'Entrega no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        
        entrega.nota = request.data.get('nota')
        entrega.observaciones = request.data.get('observaciones', '')
        entrega.save()
        
        serializer = EntregaSerializer(entrega)
        return Response(serializer.data)


# ===== AVISOS VIEW =====

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avisos_escuela_view(request):
    """Get avisos de la escuela del usuario"""
    from apps.academics.models import Aviso
    from apps.academics.serializers import AvisoSerializer
    
    # Get user's school
    user_schools = UserSchool.objects.filter(usuario=request.user, activo=True)
    
    if not user_schools.exists():
        return Response({'error': 'No tienes escuela asignada'}, status=status.HTTP_403_FORBIDDEN)
    
    school = user_schools.first().escuela
    
    # Get only important or recent avisos
    avisos = Aviso.objects.filter(escuela=school).select_related('autor')[:20]
    
    serializer = AvisoSerializer(avisos, many=True, context={'request': request})
    return Response(serializer.data)

class AvisoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar avisos escolares"""
    from apps.academics.models import Aviso
    from apps.academics.serializers import AvisoSerializer
    serializer_class = AvisoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        from apps.academics.models import Aviso
        user = self.request.user
        
        if user.is_superuser:
            return Aviso.objects.all().select_related('autor', 'escuela')
        
        # Get user's school
        user_schools = UserSchool.objects.filter(usuario=user, activo=True).select_related('escuela')
        
        if not user_schools.exists():
            return Aviso.objects.none()
        
        # Get school directly from user_school
        school = user_schools.first().escuela
        
        queryset = Aviso.objects.filter(escuela=school)
        
        # Optionally filter by importance
        if self.request.query_params.get('importante') == 'true':
            queryset = queryset.filter(importante=True)
        
        return queryset.select_related('autor', 'escuela')
    
    def perform_create(self, serializer):
        from apps.academics.models import Aviso
        user = self.request.user
        
        # Get user's UserSchool - must be DIRECTIVO
        user_school = UserSchool.objects.filter(
            usuario=user,
            activo=True,
            rol='DIRECTIVO'
        ).select_related('escuela').first()
        
        if not user_school:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Solo directivos pueden crear avisos')
        
        # Get school directly from user_school
        school = user_school.escuela
        
        # Handle 'importante' from FormData (comes as string 'true'/'false')
        importante = self.request.data.get('importante', 'false')
        if isinstance(importante, str):
            importante = importante.lower() == 'true'
        
        serializer.save(autor=user_school, escuela=school, importante=importante)