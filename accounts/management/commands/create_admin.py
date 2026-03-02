from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from decouple import config

User = get_user_model()

class Command(BaseCommand):
    help = 'Create an admin user for the dropshipping platform'

    def handle(self, *args, **options):
        email = config('ADMIN_EMAIL', default='admin@example.com')
        password = config('ADMIN_PASSWORD', default='admin123')
        first_name = config('ADMIN_FIRST_NAME', default='Admin')
        last_name = config('ADMIN_LAST_NAME', default='User')
        
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            self.stdout.write(self.style.WARNING('Admin user already exists'))
            self.stdout.write(self.style.SUCCESS(f'Admin user: {email}'))
            return
        
        # Create admin user
        admin_user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='admin'
        )
        
        # Create user profile (signals should handle this, but let's be safe)
        profile, created = UserProfile.objects.get_or_create(user=admin_user)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {email}'))
        self.stdout.write(self.style.WARNING('Admin password was set from environment variables.'))
