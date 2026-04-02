from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from voteapp.models import Election, Position, Candidate

class Command(BaseCommand):
    help = 'Creates a sample election with positions and candidates'

    def handle(self, *args, **kwargs):
        # Create Election
        self.stdout.write('Creating election...')
        
        # Set dates: starts now, ends in 7 days
        start_date = timezone.now()
        end_date = start_date + timedelta(days=7)
        
        election, created = Election.objects.get_or_create(
            title="Student Council Election 2026",
            defaults={
                'description': 'Annual election for student council representatives. Vote for your preferred candidates for each position.',
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created election: {election.title}'))
        else:
            self.stdout.write(self.style.WARNING(f'Election already exists: {election.title}'))
            election.is_active = True
            election.start_date = start_date
            election.end_date = end_date
            election.save()
            self.stdout.write(self.style.SUCCESS('✓ Updated election dates and activated'))
        
        # Create Positions and Candidates
        positions_data = [
            {
                'title': 'President',
                'description': 'Lead the student council and represent all students',
                'order': 1,
                'candidates': [
                    {
                        'name': 'Sarah Johnson',
                        'bio': 'Experienced leader with 3 years in student government. Committed to improving campus facilities and student welfare. Platform: Better cafeteria food, extended library hours, and more student events.'
                    },
                    {
                        'name': 'Michael Chen',
                        'bio': 'Former class representative with strong communication skills. Focused on bridging the gap between students and administration. Platform: Transparent governance, mental health support, and academic excellence programs.'
                    },
                    {
                        'name': 'Emily Rodriguez',
                        'bio': 'Active in multiple student organizations. Passionate about diversity and inclusion. Platform: Equal opportunities for all, cultural events, and sustainability initiatives on campus.'
                    }
                ]
            },
            {
                'title': 'Vice President',
                'description': 'Support the President and manage internal affairs',
                'order': 2,
                'candidates': [
                    {
                        'name': 'David Kim',
                        'bio': 'Organized and detail-oriented. Experience in event management and coordination. Will ensure smooth execution of all council activities and maintain strong communication channels.'
                    },
                    {
                        'name': 'Jessica Williams',
                        'bio': 'Strong administrative skills with background in project management. Committed to efficiency and accountability. Will streamline council operations and improve student engagement.'
                    }
                ]
            },
            {
                'title': 'Secretary',
                'description': 'Maintain records and handle communications',
                'order': 3,
                'candidates': [
                    {
                        'name': 'Amanda Taylor',
                        'bio': 'Excellent organizational and writing skills. Experience in documentation and record-keeping. Will ensure transparency through detailed meeting minutes and regular updates to students.'
                    },
                    {
                        'name': 'Robert Martinez',
                        'bio': 'Tech-savvy with strong communication abilities. Will modernize record-keeping systems and improve information accessibility. Committed to keeping students informed about council decisions.'
                    }
                ]
            },
            {
                'title': 'Treasurer',
                'description': 'Manage student council budget and finances',
                'order': 4,
                'candidates': [
                    {
                        'name': 'Lisa Anderson',
                        'bio': 'Accounting major with strong financial management skills. Experience in budgeting and financial planning. Will ensure responsible use of student funds and transparent financial reporting.'
                    },
                    {
                        'name': 'James Wilson',
                        'bio': 'Economics student with practical experience in financial analysis. Committed to maximizing value for student activities. Will implement cost-effective strategies and seek additional funding opportunities.'
                    }
                ]
            },
            {
                'title': 'Sports Coordinator',
                'description': 'Organize and promote sports activities',
                'order': 5,
                'candidates': [
                    {
                        'name': 'Chris Thompson',
                        'bio': 'Varsity athlete with passion for sports and fitness. Will organize inter-college tournaments, fitness programs, and promote healthy lifestyle. Platform: More sports facilities and inclusive athletic programs.'
                    },
                    {
                        'name': 'Maria Garcia',
                        'bio': 'Former team captain with leadership experience. Focused on making sports accessible to everyone. Will introduce new sports clubs, organize training sessions, and promote team spirit.'
                    }
                ]
            },
            {
                'title': 'Cultural Secretary',
                'description': 'Plan and execute cultural events and activities',
                'order': 6,
                'candidates': [
                    {
                        'name': 'Priya Patel',
                        'bio': 'Creative and enthusiastic about arts and culture. Experience in organizing cultural festivals and events. Will bring diverse cultural programs, talent shows, and celebrate various traditions on campus.'
                    },
                    {
                        'name': 'Alex Brown',
                        'bio': 'Passionate about music, drama, and arts. Will organize regular cultural events, open mic nights, and art exhibitions. Committed to showcasing student talent and fostering creative expression.'
                    }
                ]
            }
        ]
        
        for pos_data in positions_data:
            self.stdout.write(f'\nCreating position: {pos_data["title"]}')
            
            position, created = Position.objects.get_or_create(
                election=election,
                title=pos_data['title'],
                defaults={
                    'description': pos_data['description'],
                    'order': pos_data['order'],
                    'max_votes': 1
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created position: {position.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'  Position already exists: {position.title}'))
            
            # Create candidates
            for idx, cand_data in enumerate(pos_data['candidates'], 1):
                candidate, created = Candidate.objects.get_or_create(
                    position=position,
                    name=cand_data['name'],
                    defaults={
                        'bio': cand_data['bio'],
                        'order': idx
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Added candidate: {candidate.name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'    Candidate already exists: {candidate.name}'))
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ Sample election created successfully!'))
        self.stdout.write('='*60)
        self.stdout.write(f'\nElection: {election.title}')
        self.stdout.write(f'Status: {election.status()}')
        self.stdout.write(f'Positions: {election.positions.count()}')
        self.stdout.write(f'Total Candidates: {Candidate.objects.filter(position__election=election).count()}')
        self.stdout.write(f'\nVoting Period:')
        self.stdout.write(f'  Start: {election.start_date.strftime("%B %d, %Y at %I:%M %p")}')
        self.stdout.write(f'  End: {election.end_date.strftime("%B %d, %Y at %I:%M %p")}')
        self.stdout.write('\nYou can now vote at: http://127.0.0.1:8000/vote/')
