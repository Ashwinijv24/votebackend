from django.core.management.base import BaseCommand
from django.utils import timezone
from voteapp.models import Election, Position, Candidate, Vote, Voter

class Command(BaseCommand):
    help = 'Display complete election information'

    def handle(self, *args, **kwargs):
        election = Election.objects.first()
        
        if not election:
            self.stdout.write(self.style.ERROR('No election found!'))
            return
        
        now = timezone.now()
        
        # Election Info
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🗳️  VOTEEXPRESS - ELECTION INFORMATION'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS(f'📋 Election: {election.title}'))
        self.stdout.write(self.style.SUCCESS(f'📝 Description: {election.description}'))
        self.stdout.write('')
        
        # Dates
        self.stdout.write(self.style.WARNING('📅 DATES:'))
        self.stdout.write(f'   Start: {election.start_date.strftime("%B %d, %Y at %I:%M %p")}')
        self.stdout.write(f'   End:   {election.end_date.strftime("%B %d, %Y at %I:%M %p")}')
        self.stdout.write(f'   Now:   {now.strftime("%B %d, %Y at %I:%M %p")}')
        self.stdout.write('')
        
        # Status
        status = election.status()
        is_ongoing = election.is_ongoing()
        
        if is_ongoing:
            self.stdout.write(self.style.SUCCESS(f'✅ Status: {status} - VOTING IS OPEN'))
        elif now < election.start_date:
            self.stdout.write(self.style.WARNING(f'⏳ Status: {status} - NOT STARTED YET'))
        else:
            self.stdout.write(self.style.ERROR(f'🔒 Status: {status} - VOTING CLOSED'))
        self.stdout.write('')
        
        # Positions and Candidates
        positions = Position.objects.filter(election=election)
        total_candidates = Candidate.objects.filter(position__election=election).count()
        
        self.stdout.write(self.style.WARNING(f'📊 POSITIONS & CANDIDATES:'))
        self.stdout.write(f'   Total Positions: {positions.count()}')
        self.stdout.write(f'   Total Candidates: {total_candidates}')
        self.stdout.write('')
        
        for position in positions:
            candidates = Candidate.objects.filter(position=position)
            self.stdout.write(f'   {position.title}: {candidates.count()} candidates')
            for candidate in candidates:
                party = f' ({candidate.party})' if candidate.party else ''
                self.stdout.write(f'      - {candidate.name}{party}')
        self.stdout.write('')
        
        # Voting Statistics
        total_voters = Voter.objects.filter(is_verified=True, verification_status='APPROVED').count()
        total_votes_cast = Vote.objects.filter(election=election).values('voter').distinct().count()
        participation_rate = (total_votes_cast / total_voters * 100) if total_voters > 0 else 0
        
        self.stdout.write(self.style.WARNING('📈 VOTING STATISTICS:'))
        self.stdout.write(f'   Registered Voters: {total_voters}')
        self.stdout.write(f'   Voters Participated: {total_votes_cast}')
        self.stdout.write(f'   Participation Rate: {participation_rate:.1f}%')
        self.stdout.write(f'   Total Votes: {Vote.objects.filter(election=election).count()}')
        self.stdout.write('')
        
        # URLs
        self.stdout.write(self.style.WARNING('🌐 ACCESS URLS:'))
        self.stdout.write('   Home: http://127.0.0.1:8000/')
        self.stdout.write('   Register: http://127.0.0.1:8000/register/')
        self.stdout.write('   Login: http://127.0.0.1:8000/login/')
        self.stdout.write('   Vote: http://127.0.0.1:8000/vote/')
        self.stdout.write('   Results (Voter): http://127.0.0.1:8000/results/')
        self.stdout.write('   Results (Admin): http://127.0.0.1:8000/admin-results/')
        self.stdout.write('   Admin Panel: http://127.0.0.1:8000/admin/')
        self.stdout.write('')
        
        # Admin Credentials
        self.stdout.write(self.style.WARNING('🔐 ADMIN CREDENTIALS:'))
        self.stdout.write('   Username: admin')
        self.stdout.write('   Password: admin123')
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
