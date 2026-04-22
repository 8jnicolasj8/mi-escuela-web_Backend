from django.db import models
from django.utils import timezone
import uuid


class Anio(models.Model):
    """Año académico"""
    numero = models.PositiveIntegerField(verbose_name='Año')
    escuela = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='anios'
    )
    
    class Meta:
        verbose_name = 'Año Académico'
        verbose_name_plural = 'Años Académicos'
        unique_together = ['numero', 'escuela']
        ordering = ['numero']
    
    def __str__(self):
        return f"{self.numero} - {self.escuela.nombre}"


class Curso(models.Model):
    """Curso/Grado"""
    anio = models.ForeignKey(
        Anio,
        on_delete=models.CASCADE,
        related_name='cursos'
    )
    division = models.CharField(max_length=10, verbose_name='División (A, B, C...)')
    turno = models.CharField(
        max_length=20,
        choices=[
            ('MANIANA', 'Mañana'),
            ('TARDE', 'Tarde'),
            ('NOCHE', 'Noche'),
            ('COMPLETO', 'Jornada Completa'),
        ],
        verbose_name='Turno'
    )
    ciclo = models.CharField(
        max_length=20,
        choices=[
            ('PRIMARIO', 'Primario'),
            ('SECUNDARIO', 'Secundario'),
            ('TERCIARIO', 'Terciario'),
        ],
        verbose_name='Ciclo'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    anio_creacion = models.PositiveIntegerField(default=timezone.now().year, verbose_name='Año de creación')
    
    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        unique_together = ['anio', 'division', 'turno']
        ordering = ['anio__numero', 'division']
    
    def __str__(self):
        return f"{self.anio.numero}° '{self.division}' - {self.anio.escuela.nombre}"
    
    @property
    def nombre_completo(self):
        return f"{self.anio.numero}° {self.division}"


class Materia(models.Model):
    """Materia/Asignatura"""
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    nombre_corto = models.CharField(max_length=50, blank=True, verbose_name='Nombre corto')
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name='materias'
    )
    docente = models.ForeignKey(
        'users.UserSchool',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materias_dictadas',
        limit_choices_to={'rol': 'DOCENTE'}
    )
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden en el planilla')
    activa = models.BooleanField(default=True, verbose_name='Activa')
    
    class Meta:
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'
        ordering = ['orden', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.curso.nombre_completo}"
    
    @property
    def get_nombre_corto(self):
        return self.nombre_corto or self.nombre[:10]


class Alumno(models.Model):
    """Alumno inscripto en un curso"""
    usuario_escuela = models.ForeignKey(
        'users.UserSchool',
        on_delete=models.CASCADE,
        related_name='inscripciones'
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name='alumnos'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_inscripcion = models.DateField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'
        unique_together = ['usuario_escuela', 'curso']
        ordering = ['usuario_escuela__usuario__last_name', 'usuario_escuela__usuario__first_name']
    
    def __str__(self):
        return f"{self.usuario_escuela.nombre_completo} - {self.curso.nombre_completo}"


class Periodo(models.Model):
    """Período académico (trimestre, cuatrimestre, etc.)"""
    escuela = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='periodos'
    )
    anio = models.PositiveIntegerField(default=timezone.now().year, verbose_name='Año académico')
    numero = models.PositiveIntegerField(verbose_name='Número (1, 2, 3...)')
    nombre = models.CharField(max_length=50, verbose_name='Nombre (ej: 1er Trimestre)')
    
    fecha_inicio_notas = models.DateField(verbose_name='Fecha inicio carga de notas')
    fecha_fin_notas = models.DateField(verbose_name='Fecha fin carga de notas')
    
    fecha_inicio_boletin = models.DateField(null=True, blank=True, verbose_name='Fecha inicio boletin')
    fecha_fin_boletin = models.DateField(null=True, blank=True, verbose_name='Fecha fin boletin')
    
    activo = models.BooleanField(default=True, verbose_name='Activo')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Período Académico'
        verbose_name_plural = 'Períodos Académicos'
        unique_together = ['escuela', 'anio', 'numero']
        ordering = ['-anio', 'numero']
    
    def __str__(self):
        return f"{self.nombre} ({self.anio})"
    
    @property
    def estado(self):
        """Retorna el estado actual del período"""
        hoy = timezone.now().date()
        if self.fecha_inicio_notas <= hoy <= self.fecha_fin_notas:
            return 'CARGA_NOTAS'
        elif self.fecha_inicio_boletin and self.fecha_fin_boletin:
            if self.fecha_inicio_boletin <= hoy <= self.fecha_fin_boletin:
                return 'BOLETIN'
        return 'CERRADO'
    
    @property
    def puede_cargar_notas(self):
        """Verifica si actualmente se pueden cargar notas"""
        return self.estado == 'CARGA_NOTAS'
    
    @property
    def boletin_visible(self):
        """Verifica si el boletín está visible para alumnos"""
        return self.estado == 'BOLETIN'


class Nota(models.Model):
    """Nota de un alumno en una materia para un período específico"""
    periodo = models.ForeignKey(
        Periodo,
        on_delete=models.CASCADE,
        related_name='notas'
    )
    materia = models.ForeignKey(
        Materia,
        on_delete=models.CASCADE,
        related_name='notas'
    )
    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='notas'
    )
    valor = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Nota'
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    ausencias = models.PositiveIntegerField(default=0, verbose_name='Ausencias')
    
    fecha_carga = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
        unique_together = ['periodo', 'materia', 'alumno']
    
    def __str__(self):
        return f"{self.alumno.usuario_escuela.nombre_completo} - {self.materia.nombre}: {self.valor}"
    
    @property
    def estado_nota(self):
        """Retorna APROBADO o DESAPROBADO según la escala"""
        if self.valor is None:
            return 'PENDIENTE'
        return 'APROBADO' if self.valor >= 7 else 'DESAPROBADO'


class EscalaEvaluacion(models.Model):
    """Escala de evaluación configurable por escuela"""
    escuela = models.OneToOneField(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='escala_evaluacion'
    )
    limite_desaprobado = models.PositiveIntegerField(
        default=6,
        verbose_name='Límite desaprobado (notas menores a este valor son desaprobadas)'
    )
    
    # Si la escuela quiere una escala más detallada
    escala_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Escala personalizada (opcional)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Escala de Evaluación'
        verbose_name_plural = 'Escalas de Evaluación'
    
    def __str__(self):
        return f"Escala {self.escuela.nombre}: 1-{self.limite_desaprobado} = DESAPROBADO, {self.limite_desaprobado}+10 = APROBADO"
    
    def get_estado(self, valor):
        """Retorna el estado según la nota"""
        if valor is None:
            return 'PENDIENTE'
        return 'APROBADO' if valor >= self.limite_desaprobado else 'DESAPROBADO'


class Classroom(models.Model):
    """Aula virtual - espacio de una materia"""
    materia = models.OneToOneField(
        Materia,
        on_delete=models.CASCADE,
        related_name='classroom'
    )
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    codigo_acceso = models.CharField(max_length=20, unique=True)
    permite_publicaciones = models.BooleanField(default=True)
    permite_tareas = models.BooleanField(default=True)
    permite_recursos = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Aula Virtual'
        verbose_name_plural = 'Aulas Virtuales'
    
    def __str__(self):
        return f"Aula: {self.materia.nombre}"
    
    def save(self, *args, **kwargs):
        if not self.codigo_acceso:
            self.codigo_acceso = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)


class Actividad(models.Model):
    """Actividad/Tarea/Examen creado por el docente"""
    TIPOS = [
        ('EXAMEN', 'Examen'),
        ('TRABAJO', 'Trabajo Práctico'),
        ('TAREA', 'Tarea'),
    ]
    
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='actividades'
    )
    titulo = models.CharField(max_length=200, verbose_name='Título')
    tipo = models.CharField(max_length=20, choices=TIPOS, verbose_name='Tipo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    fecha_entrega = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de entrega')
    creado_por = models.ForeignKey(
        'users.UserSchool',
        on_delete=models.SET_NULL,
        null=True,
        related_name='actividades_creadas'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tipo}: {self.titulo}"


class Entrega(models.Model):
    """Entrega de un alumno para una actividad"""
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name='entregas'
    )
    alumno = models.ForeignKey(
        'users.UserSchool',
        on_delete=models.CASCADE,
        related_name='entregas'
    )
    archivo = models.FileField(upload_to='entregas/', blank=True, null=True)
    texto = models.TextField(blank=True)
    nota = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='Nota')
    comentario = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fecha_calificacion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Entrega'
        verbose_name_plural = 'Entregas'
        unique_together = ['actividad', 'alumno']
    
    def __str__(self):
        return f"{self.alumno.nombre_completo} - {self.actividad.titulo}"


class Publicacion(models.Model):
    """Publicación en el aula virtual"""
    TIPOS = [
        ('AVISO', 'Aviso/Anuncio'),
        ('TAREA', 'Tarea'),
        ('RECURSO', 'Recurso/Material'),
        ('PREGUNTA', 'Pregunta'),
    ]
    
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='publicaciones'
    )
    autor = models.ForeignKey(
        'users.UserSchool',
        on_delete=models.CASCADE,
        related_name='publicaciones'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS, verbose_name='Tipo')
    titulo = models.CharField(max_length=200, verbose_name='Título')
    contenido = models.TextField(verbose_name='Contenido')
    adjuntos = models.JSONField(default=list, blank=True, verbose_name='Adjuntos (urls)')
    
    publicado = models.BooleanField(default=False, verbose_name='Publicado')
    fecha_publicacion = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Publicación'
        verbose_name_plural = 'Publicaciones'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tipo}: {self.titulo}"


class BloqueHorario(models.Model):
    """Bloque de horario de la escuela (ej: 7:00-8:00, 8:05-9:05)"""
    escuela = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='bloques_horarios'
    )
    hora_inicio = models.TimeField(verbose_name='Hora de inicio')
    hora_fin = models.TimeField(verbose_name='Hora de fin')
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden')
    
    class Meta:
        verbose_name = 'Bloque de Horario'
        verbose_name_plural = 'Bloques de Horario'
        unique_together = ['escuela', 'hora_inicio']
        ordering = ['orden', 'hora_inicio']
    
    def __str__(self):
        return f"{self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')}"


DIAS_SEMANA = [
    (0, 'Lunes'),
    (1, 'Martes'),
    (2, 'Miércoles'),
    (3, 'Jueves'),
    (4, 'Viernes'),
]


class Horario(models.Model):
    """Horario de un curso - relaciona curso + día + bloque + materia"""
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name='horarios'
    )
    dia_semana = models.PositiveIntegerField(
        choices=DIAS_SEMANA,
        verbose_name='Día de la semana'
    )
    bloque = models.ForeignKey(
        BloqueHorario,
        on_delete=models.CASCADE,
        related_name='horarios'
    )
    materia = models.ForeignKey(
        Materia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='horarios',
        verbose_name='Materia'
    )
    
    class Meta:
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'
        unique_together = ['curso', 'dia_semana', 'bloque']
        ordering = ['dia_semana', 'bloque__orden']
    
    def __str__(self):
        return f"{self.curso.nombre_completo} - {DIAS_SEMANA[self.dia_semana][1]} - {self.bloque}"


class Aviso(models.Model):
    """Avisos/Anuncios escolares"""
    titulo = models.CharField(max_length=200, verbose_name='Titulo')
    mensaje = models.TextField(verbose_name='Mensaje')
    imagen = models.ImageField(
        upload_to='avisos/',
        null=True,
        blank=True,
        verbose_name='Imagen adjunta (opcional)'
    )
    autor = models.ForeignKey(
        'users.UserSchool',
        on_delete=models.SET_NULL,
        null=True,
        related_name='avisos_creados',
        verbose_name='Autor/Directivo'
    )
    escuela = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='avisos',
        verbose_name='Escuela'
    )
    importante = models.BooleanField(default=False, verbose_name='Marcar como importante')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Aviso'
        verbose_name_plural = 'Avisos'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return self.titulo