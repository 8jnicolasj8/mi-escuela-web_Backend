from django.contrib import admin
from apps.academics.models import Anio, Curso, Materia, Alumno, Classroom, Publicacion


@admin.register(Anio)
class AnioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'escuela']
    list_filter = ['escuela']


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['anio', 'division', 'turno', 'ciclo', 'activo']
    list_filter = ['ciclo', 'turno', 'activo', 'anio__escuela']
    search_fields = ['division']


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'curso', 'docente', 'activa', 'orden']
    list_filter = ['activa', 'curso']
    search_fields = ['nombre']


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ['usuario_escuela', 'curso', 'activo', 'fecha_inscripcion']
    list_filter = ['activo', 'curso']
    raw_id_fields = ['usuario_escuela', 'curso']


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['materia', 'codigo_acceso', 'permite_publicaciones', 'permite_tareas']
    search_fields = ['materia__nombre', 'codigo_acceso']


@admin.register(Publicacion)
class PublicacionAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'classroom', 'publicado', 'created_at']
    list_filter = ['tipo', 'publicado', 'classroom']
    search_fields = ['titulo', 'contenido']