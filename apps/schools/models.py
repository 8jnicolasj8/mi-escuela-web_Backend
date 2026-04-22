from django.db import models
from django.utils.text import slugify
import uuid


class School(models.Model):
    """
    Modelo de Escuela - Tenant base del sistema
    Cada escuela es un tenant independiente
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200, verbose_name='Nombre de la escuela')
    slug = models.SlugField(unique=True, verbose_name='Identificador URL')
    logo = models.ImageField(upload_to='schools/logos/', blank=True, null=True)
    
    cue = models.CharField(max_length=20, blank=True, verbose_name='CUE (Código Único de Establecimiento)')
    provincia = models.CharField(max_length=100, blank=True, verbose_name='Provincia')
    localidad = models.CharField(max_length=100, blank=True, verbose_name='Localidad')
    direccion = models.TextField(blank=True, verbose_name='Dirección')
    
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    activa = models.BooleanField(default=True, verbose_name='Activa')
    habilita_boletin_pdf = models.BooleanField(default=False, verbose_name='Habilitar boletín PDF')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Escuela'
        verbose_name_plural = 'Escuelas'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre)
            self.slug = base_slug
            
            counter = 1
            while School.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} - {self.localidad}"
    
    def get_usuarios_activos(self):
        from apps.users.models import UserSchool
        return UserSchool.objects.filter(
            escuela=self,
            activo=True
        ).select_related('usuario')
    
    def get_directivos(self):
        return self.get_usuarios_activos().filter(rol='DIRECTIVO')
    
    def get_docentes(self):
        return self.get_usuarios_activos().filter(rol='DOCENTE')
    
    def get_alumnos(self):
        return self.get_usuarios_activos().filter(rol='ALUMNO')


PROVINCIAS = [
    ('Buenos Aires', 'Buenos Aires'),
    ('CABA', 'Ciudad Autónoma de Buenos Aires'),
    ('Catamarca', 'Catamarca'),
    ('Chaco', 'Chaco'),
    ('Chubut', 'Chubut'),
    ('Córdoba', 'Córdoba'),
    ('Corrientes', 'Corrientes'),
    ('Entre Ríos', 'Entre Ríos'),
    ('Formosa', 'Formosa'),
    ('Jujuy', 'Jujuy'),
    ('La Pampa', 'La Pampa'),
    ('La Rioja', 'La Rioja'),
    ('Mendoza', 'Mendoza'),
    ('Misiones', 'Misiones'),
    ('Neuquén', 'Neuquén'),
    ('Río Negro', 'Río Negro'),
    ('Salta', 'Salta'),
    ('San Juan', 'San Juan'),
    ('San Luis', 'San Luis'),
    ('Santa Cruz', 'Santa Cruz'),
    ('Santa Fe', 'Santa Fe'),
    ('Santiago del Estero', 'Santiago del Estero'),
    ('Tierra del Fuego', 'Tierra del Fuego'),
    ('Tucumán', 'Tucumán'),
]