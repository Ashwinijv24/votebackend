from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create admin superuser'

    def handle(self, *args, **kwargs):
        username = 'admin'
        email = 'admin@voteexpress.com'
        password = 'admin123'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Admin user "{username}" already exists!'))
            
            # Update password
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Password updated for admin user!'))
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Admin user created successfully!'))
        
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Admin Credentials:'))
        self.stdout.write(self.style.SUCCESS(f'Username: {username}'))
        self.stdout.write(self.style.SUCCESS(f'Password: {password}'))
        self.stdout.write(self.style.SUCCESS(f'Admin URL: http://127.0.0.1:8000/admin/'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
