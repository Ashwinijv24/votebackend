from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from voteapp.models import Election

class Command(BaseCommand):
    help = 'Update election dates to current time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days the election should run (default: 7)'
        )

    def handle(self, *args, **kwargs):
        days = kwargs['days']
        
        # Get the first election
        election = Election.objects.first()
        
        if not election:
            self.stdout.write(self.style.ERROR('No election found!'))
            return
        
        # Update dates
        now = timezone.now()
        election.start_date = now
        election.end_date = now + timedelta(days=days)
        election.is_active = True
        election.save()
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Election Dates Updated Successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Election: {election.title}'))
        self.stdout.write(self.style.SUCCESS(f'Start Date: {election.start_date.strftime("%B %d, %Y at %I:%M %p")}'))
        self.stdout.write(self.style.SUCCESS(f'End Date: {election.end_date.strftime("%B %d, %Y at %I:%M %p")}'))
        self.stdout.write(self.style.SUCCESS(f'Duration: {days} days'))
        self.stdout.write(self.style.SUCCESS(f'Status: ACTIVE & ONGOING'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
