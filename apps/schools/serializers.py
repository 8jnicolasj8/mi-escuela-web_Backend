from rest_framework import serializers
from apps.schools.models import School


class SchoolSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    
    class Meta:
        model = School
        fields = [
            'id', 'nombre', 'slug', 'logo', 'cue', 
            'provincia', 'localidad', 'direccion',
            'telefono', 'email', 'website',
            'activa', 'habilita_boletin_pdf',
            'nombre_completo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']