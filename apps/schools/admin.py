from django.contrib import admin
from apps.schools.models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'slug', 'localidad', 'provincia', 'activa']
    list_filter = ['activa', 'provincia']
    search_fields = ['nombre', 'slug', 'localidad']
    prepopulated_fields = {'slug': ('nombre',)}