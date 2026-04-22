from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User, UserSchool
from apps.schools.models import School


class Command(BaseCommand):
    help = 'Creates superadmin user and binds to a school'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='superadmin@campus.local', help='Email for superadmin')
        parser.add_argument('--password', type=str, default='1234', help='Password for superadmin')
        parser.add_argument('--school-name', type=str, default='Escuela Secundaria N°4', help='School name')
        parser.add_argument('--school-location', type=str, default='General Pinto', help='School location')
        parser.add_argument('--school-cue', type=str, default='', help='CUE code')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        school_name = options['school_name']
        school_location = options['school_location']
        school_cue = options['school_cue']
        
        # Create or get school
        school, created = School.objects.get_or_create(
            slug='escuela-secundaria-n-4',
            defaults={
                'nombre': school_name,
                'cue': school_cue,
                'localidad': school_location,
                'provincia': 'Buenos Aires',
                'activa': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created school: {school.nombre}'))
        else:
            self.stdout.write(f'School already exists: {school.nombre}')
        
        # Create or get superadmin user
        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'first_name': 'Super',
                'last_name': 'Admin',
            }
        )
        
        if user_created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created superadmin user: {user.email}'))
        else:
            self.stdout.write(f'User already exists: {user.email}')
        
        # Create user-school relationship
        user_school, us_created = UserSchool.objects.get_or_create(
            usuario=user,
            escuela=school,
            defaults={
                'rol': 'SUPERADMIN',
                'activo': True,
            }
        )
        
        if us_created:
            self.stdout.write(self.style.SUCCESS(f'Bound {user.email} to {school.nombre} as SUPERADMIN'))
        else:
            self.stdout.write(f'User-school relationship already exists')
        
        self.stdout.write(self.style.SUCCESS('\n=== Superadmin Created Successfully ==='))
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'School: {school.nombre} ({school.slug})')
        self.stdout.write('==========================================')