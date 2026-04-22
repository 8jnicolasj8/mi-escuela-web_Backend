from rest_framework import serializers
from apps.users.models import User, UserSchool
from apps.schools.models import School


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    short_name = serializers.CharField(source='get_short_name', read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'dni',
            'provincia', 'localidad',
            'full_name', 'short_name', 'is_active', 'is_superuser',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserSchoolSerializer(serializers.ModelSerializer):
    usuario = UserSerializer(read_only=True)
    nombre_completo = serializers.CharField(read_only=True)
    nombre_escuela = serializers.CharField(source='escuela.nombre', read_only=True)
    foto_perfil_url = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSchool
        fields = [
            'id', 'usuario', 'escuela', 'nombre_escuela', 
            'rol', 'activo', 'nombre_completo', 'estado_solicitud',
            'foto_perfil', 'foto_perfil_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_foto_perfil_url(self, obj):
        if obj.foto_perfil:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.foto_perfil.url)
            return obj.foto_perfil.url
        return None


class UserSchoolCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    dni = serializers.CharField(required=False, allow_blank=True)
    provincia = serializers.CharField(required=False, allow_blank=True)
    localidad = serializers.CharField(required=False, allow_blank=True)
    escuela = serializers.UUIDField(write_only=True, required=True)
    rol = serializers.CharField(required=False, default='ALUMNO')
    
    class Meta:
        model = UserSchool
        fields = [
            'email', 'password', 'escuela', 'rol', 'activo',
            'first_name', 'last_name', 'dni', 'provincia', 'localidad'
        ]
    
    def create(self, validated_data):
        from apps.schools.models import School
        
        email = validated_data.pop('email')
        password = validated_data.pop('password', None)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        dni = validated_data.pop('dni', '')
        provincia = validated_data.pop('provincia', '')
        localidad = validated_data.pop('localidad', '')
        
        escuela_id = validated_data.pop('escuela')
        rol = validated_data.pop('rol', 'ALUMNO')
        
        try:
            if isinstance(escuela_id, str):
                import uuid
                escuela_id = uuid.UUID(escuela_id)
            escuela = School.objects.get(id=escuela_id)
        except School.DoesNotExist:
            raise serializers.ValidationError({'escuela': 'Escuela no encontrada'})
        except ValueError:
            raise serializers.ValidationError({'escuela': 'ID de escuela inválido'})
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'dni': dni,
                'provincia': provincia,
                'localidad': localidad
            }
        )
        
        if created:
            if password:
                user.set_password(password)
            else:
                user.set_password('password123')
            user.save()
        
        # Verificar si ya existe la relación usuario-escuela
        existing = UserSchool.objects.filter(usuario=user, escuela=escuela).first()
        if existing:
            raise serializers.ValidationError({
                'escuela': f'El usuario ya está asociado a esta escuela como {existing.rol}'
            })
        
        user_school = UserSchool.objects.create(
            usuario=user,
            escuela=escuela,
            estado_solicitud='APROBADO',
            activo=True,
            rol=rol or 'ALUMNO'
        )
        
        return user_school


class SolicitudRegistroSerializer(serializers.ModelSerializer):
    """Serializer para crear solicitudes de registro (usuarios pendientes)"""
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    dni = serializers.CharField(required=False, allow_blank=True)
    provincia = serializers.CharField(required=False, allow_blank=True)
    localidad = serializers.CharField(required=False, allow_blank=True)
    escuela_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = UserSchool
        fields = [
            'email', 'password', 'escuela_id',
            'first_name', 'last_name', 'dni', 'provincia', 'localidad'
        ]
    
    def validate_escuela_id(self, value):
        try:
            school = School.objects.get(id=value, activa=True)
        except School.DoesNotExist:
            raise serializers.ValidationError("Escuela no encontrada o inactiva")
        return school
    
    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password', 'password123')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        dni = validated_data.pop('dni', '')
        provincia = validated_data.pop('provincia', '')
        localidad = validated_data.pop('localidad', '')
        escuela = validated_data.pop('escuela_id')
        
        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            dni=dni,
            provincia=provincia,
            localidad=localidad
        )
        user.set_password(password)
        user.save()
        
        user_school = UserSchool.objects.create(
            usuario=user,
            escuela=escuela,
            rol='ALUMNO',
            activo=False,
            estado_solicitud='PENDIENTE'
        )
        
        return user_school