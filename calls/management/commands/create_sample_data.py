from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from calls.models import Call, Memory, CallNote, EmergencyContact
from datetime import datetime, timedelta
import random
import uuid


class Command(BaseCommand):
    help = 'Create sample data for testing the hotline system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--calls',
            type=int,
            default=10,
            help='Number of sample calls to create'
        )
    
    def handle(self, *args, **options):
        num_calls = options['calls']
        
        # Create a sample user if it doesn't exist
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created admin user: admin/admin123')
            )
        
        # Sample data
        phone_numbers = [
            '+1234567890', '+1987654321', '+1555123456', '+1444567890',
            '+1333456789', '+1222345678', '+1111234567', '+1666789012'
        ]
        
        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia']
        states = ['NY', 'CA', 'IL', 'TX', 'AZ', 'PA']
        
        risk_levels = ['low', 'moderate', 'high', 'critical']
        emotions = ['sad', 'angry', 'anxious', 'depressed', 'hopeless', 'confused', 'calm']
        statuses = ['completed', 'in_progress', 'disconnected']
        
        risk_factors_options = [
            ['Recent loss', 'Social isolation'],
            ['Financial stress', 'Relationship problems'],
            ['Mental health history', 'Substance abuse'],
            ['Chronic illness', 'Family conflict'],
            ['Job loss', 'Academic pressure']
        ]
        
        protective_factors_options = [
            ['Strong family support', 'Religious beliefs'],
            ['Access to mental health care', 'Stable housing'],
            ['Good coping skills', 'Social connections'],
            ['Employment', 'Physical health'],
            ['Future plans', 'Therapy engagement']
        ]
        
        conversation_summaries = [
            "Caller expressed feelings of hopelessness due to recent job loss. Discussed coping strategies and local job resources.",
            "Individual dealing with relationship breakdown and thoughts of self-harm. Safety plan developed.",
            "Young person struggling with academic pressure and family expectations. Explored stress management techniques.",
            "Elderly caller feeling isolated after spouse's death. Connected with grief support groups.",
            "Person with history of depression experiencing worsening symptoms. Encouraged to contact psychiatrist.",
            "Individual in crisis due to financial difficulties. Discussed immediate safety and available resources.",
            "Caller with substance abuse issues expressing suicidal ideation. Emergency services contacted.",
            "Parent worried about teenager's behavior. Provided family counseling resources."
        ]
        
        self.stdout.write(f'Creating {num_calls} sample calls...')
        
        for i in range(num_calls):
            # Create call - spread across the last 7 days with more calls on recent days
            days_back = random.choices(
                range(7),  # 0-6 days back
                weights=[5, 4, 3, 2, 2, 1, 1],  # More weight on recent days
                k=1
            )[0]
            
            # Random hour and minute for realistic spread
            base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = base_date - timedelta(days=days_back)
            start_time = start_time.replace(
                hour=random.randint(6, 23),  # Calls between 6 AM and 11 PM
                minute=random.randint(0, 59)
            )
            
            duration = timedelta(minutes=random.randint(5, 60))
            
            call = Call.objects.create(
                phone_number=random.choice(phone_numbers),
                twilio_call_sid=f'CA{uuid.uuid4().hex}',
                status=random.choice(statuses),
                start_time=start_time,
                end_time=start_time + duration,
                duration=duration,
                caller_city=random.choice(cities),
                caller_state=random.choice(states),
                caller_country='USA',
                transcription=f"Sample transcription for call {i+1}. This would contain the actual conversation text.",
                audio_file_url=f"https://example.com/recordings/call_{i+1}.mp3"
            )
            
            # Create memory for the call
            risk_level = random.choice(risk_levels)
            primary_emotion = random.choice(emotions)
            
            memory = Memory.objects.create(
                call=call,
                risk_level=risk_level,
                risk_factors=random.choice(risk_factors_options),
                protective_factors=random.choice(protective_factors_options),
                primary_emotion=primary_emotion,
                emotion_intensity=random.randint(1, 10),
                emotions_detected=[primary_emotion, random.choice(emotions)],
                conversation_summary=random.choice(conversation_summaries),
                key_topics=['crisis intervention', 'safety planning', 'resource referral'],
                intervention_techniques_used=['active listening', 'empathy', 'safety assessment'],
                chat_messages=[
                    {"role": "caller", "message": "I'm feeling really hopeless"},
                    {"role": "ai", "message": "I hear that you're in pain. Can you tell me more about what's happening?"},
                    {"role": "caller", "message": "Everything seems to be falling apart"},
                    {"role": "ai", "message": "That sounds overwhelming. Let's talk about what support you have available."}
                ],
                mental_health_concerns="Depression, anxiety, potential risk factors identified",
                immediate_safety_plan="Remove means, contact support person, utilize coping strategies",
                follow_up_needed=risk_level in ['high', 'critical'],
                follow_up_notes="Schedule check-in within 24 hours" if risk_level in ['high', 'critical'] else "",
                resources_provided=['National Suicide Prevention Lifeline', 'Local crisis center', 'Mental health services'],
                referrals_made=['Emergency services'] if risk_level == 'critical' else ['Outpatient therapy'],
                confidence_score=random.uniform(0.7, 0.95)
            )
            
            # Create some call notes
            if random.choice([True, False]):
                CallNote.objects.create(
                    call=call,
                    author=user,
                    note=f"Follow-up note for call {i+1}. Caller seemed responsive to intervention.",
                    is_urgent=risk_level in ['high', 'critical']
                )
            
            # Create emergency contact if high risk
            if risk_level in ['high', 'critical']:
                EmergencyContact.objects.create(
                    call=call,
                    contact_type='Emergency Services',
                    contact_info='911',
                    notes='Contacted due to imminent risk',
                    contacted=True,
                    contact_time=start_time + timedelta(minutes=random.randint(1, 10))
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {num_calls} sample calls with memories and notes')
        )
        
        # Print some statistics
        total_calls = Call.objects.count()
        total_memories = Memory.objects.count()
        high_risk = Memory.objects.filter(risk_level__in=['high', 'critical']).count()
        
        self.stdout.write(f'Database now contains:')
        self.stdout.write(f'  - {total_calls} calls')
        self.stdout.write(f'  - {total_memories} memories')
        self.stdout.write(f'  - {high_risk} high/critical risk cases')
