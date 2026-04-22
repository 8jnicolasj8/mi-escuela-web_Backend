from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es requerido')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de Usuario - Base de autenticación
    """
    email = models.EmailField(unique=True, verbose_name='Email')
    first_name = models.CharField(max_length=150, blank=True, verbose_name='Nombre')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='Apellido')
    
    # Datos personales adicionales
    dni = models.CharField(max_length=20, blank=True, verbose_name='DNI')
    provincia = models.CharField(max_length=100, blank=True, verbose_name='Provincia')
    localidad = models.CharField(max_length=100, blank=True, verbose_name='Localidad')
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    is_staff = models.BooleanField(default=False, verbose_name='Staff admin')
    is_superuser = models.BooleanField(default=False, verbose_name='Super usuario')
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['email']
    
    def __str__(self):
        return self.email
    
    @property
    def get_full_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.email
    
    @property
    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]


class UserSchool(models.Model):
    """
    Modelo que relaciona Usuario con Escuela - Define el rol en cada escuela
    """
    ROLES = [
        ('SUPERADMIN', 'Super Administrador'),
        ('DIRECTIVO', 'Directivo'),
        ('DOCENTE', 'Docente'),
        ('ALUMNO', 'Alumno'),
        ('APODERADO', 'Apoderado'),
    ]
    
    ESTADO_SOLICITUD = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='escuelas'
    )
    escuela = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='usuarios'
    )
    rol = models.CharField(max_length=20, choices=ROLES, verbose_name='Rol')
    activo = models.BooleanField(default=True, verbose_name='Activo en esta escuela')
    tutor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tutorados',
        verbose_name='Apoderado/Tutor'
    )
    codigo_vinculacion = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Código de Vinculación'
    )
    foto_perfil = models.ImageField(
        upload_to='perfiles/',
        null=True,
        blank=True,
        verbose_name='Foto de Perfil'
    )
    
    # Campos para solicitudes de ingreso
    estado_solicitud = models.CharField(
        max_length=20, 
        choices=ESTADO_SOLICITUD, 
        default='APROBADO',
        verbose_name='Estado de Solicitud'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Usuario por Escuela'
        verbose_name_plural = 'Usuarios por Escuela'
        unique_together = ['usuario', 'escuela']
        ordering = ['escuela', 'usuario']
    
    def __str__(self):
        return f"{self.usuario.email} - {self.escuela.nombre} ({self.get_rol_display()})"
    
    @property
    def nombre_completo(self):
        return self.usuario.get_full_name or self.usuario.email
    
    @property
    def es_directivo(self):
        return self.rol == 'DIRECTIVO'
    
    @property
    def es_docente(self):
        return self.rol == 'DOCENTE'
    
    @property
    def es_alumno(self):
        return self.rol == 'ALUMNO'
    
    @property
    def es_apoderado(self):
        return self.rol == 'APODERADO'
    
    def generar_codigo_vinculacion(self):
        import secrets
        import string
        # Generate unique 6 char code
        caracteres = string.ascii_uppercase + string.digits
        while True:
            random_part = ''.join(secrets.choice(caracteres) for _ in range(6))
            # Check it's unique
            if not UserSchool.objects.filter(codigo_vinculacion=random_part).exists():
                self.codigo_vinculacion = random_part
                self.save()
                return random_part