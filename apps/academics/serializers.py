from rest_framework import serializers
from apps.academics.models import (
    Anio, Curso, Materia, Alumno, Classroom, Publicacion,
    Periodo, Nota, EscalaEvaluacion, BloqueHorario, Horario, Actividad, Entrega, DIAS_SEMANA
)
from apps.users.serializers import UserSchoolSerializer


class AnioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anio
        fields = ['id', 'numero', 'escuela']
        read_only_fields = ['id']
    
    def validate_escuela(self, value):
        if not value:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                from apps.users.models import UserSchool
                user_school = UserSchool.objects.filter(
                    usuario=request.user,
                    activo=True
                ).first()
                if user_school:
                    return user_school.escuela
        return value


class AlumnoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    
    class Meta:
        model = Alumno
        fields = ['id', 'usuario_escuela', 'curso', 'activo', 'fecha_inscripcion', 'nombre_completo']
        read_only_fields = ['id', 'fecha_inscripcion']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.usuario_escuela:
            data['usuario_info'] = {
                'id': str(instance.usuario_escuela.id),
                'nombre_completo': instance.usuario_escuela.nombre_completo,
                'usuario': {
                    'dni': instance.usuario_escuela.usuario.dni if instance.usuario_escuela.usuario else None
                }
            }
        return data


class MateriaSerializer(serializers.ModelSerializer):
    nombre_corto_display = serializers.CharField(read_only=True)
    docente_info = UserSchoolSerializer(read_only=True, source='docente')
    
    class Meta:
        model = Materia
        fields = [
            'id', 'nombre', 'nombre_corto', 'nombre_corto_display',
            'curso', 'docente', 'docente_info', 'orden', 'activa'
        ]
        read_only_fields = ['id']


class CursoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    anio_numero = serializers.IntegerField(source='anio.numero', read_only=True)
    alumnos = AlumnoSerializer(many=True, read_only=True)
    materias = MateriaSerializer(many=True, read_only=True)
    
    class Meta:
        model = Curso
        fields = [
            'id', 'anio', 'anio_numero', 'division', 'turno', 
            'ciclo', 'activo', 'anio_creacion', 'nombre_completo', 
            'alumnos', 'materias'
        ]
        read_only_fields = ['id', 'anio_creacion']


class PeriodoSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(read_only=True)
    puede_cargar_notas = serializers.BooleanField(read_only=True)
    boletin_visible = serializers.BooleanField(read_only=True)
    escuela_nombre = serializers.CharField(source='escuela.nombre', read_only=True)
    
    class Meta:
        model = Periodo
        fields = [
            'id', 'escuela', 'escuela_nombre', 'anio', 'numero', 'nombre',
            'fecha_inicio_notas', 'fecha_fin_notas',
            'fecha_inicio_boletin', 'fecha_fin_boletin',
            'activo', 'observaciones',
            'estado', 'puede_cargar_notas', 'boletin_visible',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'escuela': {'required': False},
        }
    
    def to_internal_value(self, data):
        # Manejar caso donde escuela no está en los datos
        if 'escuela' not in data:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                from apps.users.models import UserSchool
                user_school = UserSchool.objects.filter(
                    usuario=request.user,
                    activo=True
                ).first()
                if user_school:
                    data['escuela'] = user_school.escuela_id
        return super().to_internal_value(data)
    
    def create(self, validated_data):
        request = self.context.get('request')
        if 'escuela' not in validated_data:
            from apps.users.models import UserSchool
            user_school = UserSchool.objects.filter(
                usuario=request.user,
                activo=True
            ).first()
            if user_school:
                validated_data['escuela'] = user_school.escuela
        return super().create(validated_data)


class NotaSerializer(serializers.ModelSerializer):
    estado_nota = serializers.CharField(read_only=True)
    nombre_alumno = serializers.CharField(source='alumno.usuario_escuela.nombre_completo', read_only=True)
    nombre_materia = serializers.CharField(source='materia.nombre', read_only=True)
    
    class Meta:
        model = Nota
        fields = [
            'id', 'periodo', 'materia', 'alumno',
            'nombre_alumno', 'nombre_materia',
            'valor', 'observaciones', 'ausencias',
            'estado_nota', 'fecha_carga', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_carga', 'fecha_actualizacion']


class EscalaEvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalaEvaluacion
        fields = ['id', 'escuela', 'limite_desaprobado', 'escala_json', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClassroomSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='materia.curso.nombre_completo', read_only=True)
    
    class Meta:
        model = Classroom
        fields = [
            'id', 'materia', 'materia_nombre', 'curso_nombre',
            'descripcion', 'codigo_acceso', 
            'permite_publicaciones', 'permite_tareas', 'permite_recursos',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'codigo_acceso', 'created_at', 'updated_at']


class PublicacionSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre_completo', read_only=True)
    
    class Meta:
        model = Publicacion
        fields = [
            'id', 'classroom', 'autor', 'autor_nombre',
            'tipo', 'titulo', 'contenido', 'adjuntos',
            'published', 'fecha_publicacion',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BloqueHorarioSerializer(serializers.ModelSerializer):
    hora_inicio = serializers.TimeField(format='%H:%M')
    hora_fin = serializers.TimeField(format='%H:%M')
    
    class Meta:
        model = BloqueHorario
        fields = ['id', 'escuela', 'hora_inicio', 'hora_fin', 'orden']
        read_only_fields = ['id', 'escuela']
    
    def to_internal_value(self, data):
        data = data.copy()
        data.pop('escuela', None)
        return super().to_internal_value(data)


class HorarioSerializer(serializers.ModelSerializer):
    materia_info = serializers.SerializerMethodField()
    dia_nombre = serializers.SerializerMethodField()
    bloque_horario = serializers.CharField(source='bloque.__str__', read_only=True)
    
    class Meta:
        model = Horario
        fields = ['id', 'curso', 'dia_semana', 'dia_nombre', 'bloque', 'bloque_horario', 'materia', 'materia_info']
        read_only_fields = ['id']
    
    def get_dia_nombre(self, obj):
        return DIAS_SEMANA[obj.dia_semana][1] if obj.dia_semana < len(DIAS_SEMANA) else ''
    
    def get_materia_info(self, obj):
        return None


class ActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actividad
        fields = ['id', 'classroom', 'titulo', 'tipo', 'descripcion', 'fecha_entrega', 'creado_por', 'created_at']
        read_only_fields = ['id', 'created_at']


class EntregaSerializer(serializers.ModelSerializer):
    nombre_alumno = serializers.CharField(source='alumno.nombre_completo', read_only=True)
    
    class Meta:
        model = Entrega
        fields = ['id', 'actividad', 'alumno', 'nombre_alumno', 'archivo', 'texto', 'nota', 'comentario', 'created_at']
        read_only_fields = ['id', 'created_at']


class HorarioGridSerializer(serializers.SerializerMethodField):
    """Serializer para devolver el horario en formato grid"""
    grid = serializers.DictField()
    
    def to_representation(self, instance):
        return instance


class AvisoSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre_completo', read_only=True)
    imagen_url = serializers.SerializerMethodField()
    
    class Meta:
        from apps.academics.models import Aviso
        model = Aviso
        fields = ['id', 'titulo', 'mensaje', 'imagen', 'imagen_url', 'autor', 'autor_nombre', 'escuela', 'importante', 'fecha_creacion', 'actualizado']
        read_only_fields = ['id', 'autor', 'escuela', 'fecha_creacion', 'actualizado']
    
    def get_imagen_url(self, obj):
        if obj.imagen:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None