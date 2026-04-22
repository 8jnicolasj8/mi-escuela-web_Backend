from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import User, UserSchool


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


@admin.register(UserSchool)
class UserSchoolAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'escuela', 'rol', 'activo']
    list_filter = ['rol', 'activo', 'escuela']
    search_fields = ['usuario__email', 'escuela__nombre']
    raw_id_fields = ['usuario', 'escuela']