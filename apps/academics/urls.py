from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.academics.views import (
    AnioViewSet, CursoViewSet, MateriaViewSet,
    AlumnoViewSet, ClassroomViewSet, PublicacionViewSet,
    PeriodoViewSet, NotaViewSet, EscalaEvaluacionViewSet,
    BloqueHorarioViewSet, HorarioViewSet, AvisoViewSet,
    mis_cursos_view, mis_alumnos_view, mis_horarios_view, mis_classrooms_view,
    actividades_view, calendario_view, entregas_view,
    mis_actividades_alumno_view, entregas_alumno_view, mis_notas_view, mis_hijos_view,
    notas_hijo_view, avisos_escuela_view
)

router = DefaultRouter()
router.register(r'anios', AnioViewSet, basename='anio')
router.register(r'cursos', CursoViewSet, basename='curso')
router.register(r'materias', MateriaViewSet, basename='materia')
router.register(r'alumnos', AlumnoViewSet, basename='alumno')
router.register(r'classrooms', ClassroomViewSet, basename='classroom')
router.register(r'publicaciones', PublicacionViewSet, basename='publicacion')
router.register(r'periodos', PeriodoViewSet, basename='periodo')
router.register(r'notas', NotaViewSet, basename='nota')
router.register(r'escala', EscalaEvaluacionViewSet, basename='escala')
router.register(r'bloques-horario', BloqueHorarioViewSet, basename='bloques-horario')
router.register(r'horarios', HorarioViewSet, basename='horarios')
router.register(r'avisos', AvisoViewSet, basename='aviso')

urlpatterns = [
    path('', include(router.urls)),
    path('mis-cursos/', mis_cursos_view, name='mis-cursos'),
    path('mis-alumnos/', mis_alumnos_view, name='mis-alumnos'),
    path('mis-horarios/', mis_horarios_view, name='mis-horarios'),
    path('mis-classrooms/', mis_classrooms_view, name='mis-classrooms'),
    path('actividades/', actividades_view, name='actividades'),
    path('actividades-alumno/', mis_actividades_alumno_view, name='actividades-alumno'),
    path('entregas-alumno/', entregas_alumno_view, name='entregas-alumno'),
    path('calendario/', calendario_view, name='calendario'),
    path('entregas/<int:actividad_id>', entregas_view, name='entregas'),
    path('mis-notas/', mis_notas_view, name='mis-notas'),
    path('mis-hijos/', mis_hijos_view, name='mis-hijos'),
    path('notas-hijo/<int:hijо_id>', notas_hijo_view, name='notas-hijo'),
    path('avisos-escuela/', avisos_escuela_view, name='avisos-escuela'),
]