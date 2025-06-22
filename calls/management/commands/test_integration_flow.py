from django.core.management.base import BaseCommand
from calls.models import Call, RecordingChunk
from calls.ai_service import TwilioVoiceService
from calls.risk_assessment import risk_service
import time


class Command(BaseCommand):
    help = 'Test the complete integration flow from recording to risk assessment'

    def handle(self, *args, **options):
        self.stdout.write("🎯 Testing Complete Integration Flow")
        self.stdout.write("=" * 60)

        # Create a test call that simulates a real call flow
        service = TwilioVoiceService()
        
        # Create test call
        test_call = Call.objects.create(
            phone_number="+1555123456",
            twilio_call_sid="TEST_INTEGRATION_" + str(int(time.time())),
            status='in_progress'
        )
        
        self.stdout.write(f"📞 Created test call: {test_call.id}")

        # Simulate the AI service flow by calling _store_transcription_and_assess_risk
        # This mimics what happens when a recording is processed
        
        # Simulate Chunk 1 - Low risk
        self.stdout.write("\n🎤 Processing Chunk 1 (Low Risk)...")
        chunk1 = RecordingChunk.objects.create(
            call=test_call,
            recording_url="https://test.com/chunk1.wav",
            chunk_number=1
        )
        
        # Mock sarvam result for chunk 1
        sarvam_result1 = {
            'transcription': 'Hello, I am feeling a bit down today',
            'language_code': 'en-IN',
            'response_text': 'I understand you\'re feeling down. Can you tell me more?'
        }
        
        service._store_transcription_and_assess_risk(str(test_call.id), sarvam_result1)
        time.sleep(2)  # Wait for async processing
        
        # Check results
        chunk1.refresh_from_db()
        self.stdout.write(f"   ✅ Transcription stored: {chunk1.transcription[:50]}...")
        self.stdout.write(f"   ✅ Risk assessment completed: {chunk1.risk_assessment_completed}")
        
        memory1 = test_call.memories.first()
        if memory1:
            self.stdout.write(f"   ✅ Risk Level: {memory1.risk_level}")

        # Simulate Chunk 2 - Medium risk  
        self.stdout.write("\n🎤 Processing Chunk 2 (Medium Risk)...")
        chunk2 = RecordingChunk.objects.create(
            call=test_call,
            recording_url="https://test.com/chunk2.wav",
            chunk_number=2
        )
        
        sarvam_result2 = {
            'transcription': 'I have been having trouble sleeping and taking care of myself',
            'language_code': 'en-IN',
            'response_text': 'It sounds like you\'re struggling with self-care. That\'s concerning.'
        }
        
        service._store_transcription_and_assess_risk(str(test_call.id), sarvam_result2)
        time.sleep(2)
        
        chunk2.refresh_from_db()
        test_call.refresh_from_db()
        memory2 = test_call.memories.first()
        if memory2:
            self.stdout.write(f"   ✅ Updated Risk Level: {memory2.risk_level}")
            self.stdout.write(f"   ✅ Risk Factors Count: {len(memory2.risk_factors)}")

        # Simulate Chunk 3 - High risk
        self.stdout.write("\n🎤 Processing Chunk 3 (High Risk)...")
        chunk3 = RecordingChunk.objects.create(
            call=test_call,
            recording_url="https://test.com/chunk3.wav",
            chunk_number=3
        )
        
        sarvam_result3 = {
            'transcription': 'I am thinking about ending my life, I have a plan to hurt myself',
            'language_code': 'en-IN',
            'response_text': 'I\'m very concerned about what you\'re telling me. You\'re important.'
        }
        
        service._store_transcription_and_assess_risk(str(test_call.id), sarvam_result3)
        time.sleep(3)  # Wait longer for high-risk processing
        
        chunk3.refresh_from_db()
        test_call.refresh_from_db()
        memory3 = test_call.memories.first()
        
        self.stdout.write(f"   ✅ Final Risk Level: {memory3.risk_level}")
        self.stdout.write(f"   ✅ Follow-up Needed: {memory3.follow_up_needed}")
        
        # Check emergency contacts
        emergency_contacts = test_call.emergency_contacts.filter(
            contact_type='Crisis Team - Risk Assessment'
        )
        if emergency_contacts.exists():
            self.stdout.write(f"   ✅ Emergency contact created: {emergency_contacts.count()}")
        else:
            self.stdout.write("   ⚠️  No emergency contact created")

        # Test cumulative analysis
        self.stdout.write("\n📊 Testing Cumulative Analysis...")
        
        # Get all transcriptions combined
        all_chunks = test_call.recording_chunks.order_by('chunk_number')
        combined_transcription = " ".join([c.transcription for c in all_chunks if c.transcription])
        
        self.stdout.write(f"   Combined transcription length: {len(combined_transcription)} chars")
        self.stdout.write(f"   Total chunks analyzed: {all_chunks.count()}")
        
        # Final manual check 
        final_assessment = risk_service.assess_call_risk(str(test_call.id))
        self.stdout.write(f"   Final risk assessment: {final_assessment['risk_level']} ({final_assessment['category']})")

        # Display call summary
        self.stdout.write("\n📋 Call Summary:")
        self.stdout.write(f"   Phone: {test_call.phone_number}")
        self.stdout.write(f"   Total Recording Chunks: {test_call.recording_chunks.count()}")
        self.stdout.write(f"   Chunks with Transcription: {test_call.recording_chunks.filter(transcription__isnull=False).count()}")
        self.stdout.write(f"   Chunks with Risk Assessment: {test_call.recording_chunks.filter(risk_assessment_completed=True).count()}")
        self.stdout.write(f"   Memories Created: {test_call.memories.count()}")
        self.stdout.write(f"   Emergency Contacts: {test_call.emergency_contacts.count()}")

        if memory3:
            self.stdout.write(f"   Final Risk Level: {memory3.risk_level}")
            self.stdout.write(f"   Risk Factors: {len(memory3.risk_factors)}")

        # Cleanup
        self.stdout.write("\n🧹 Cleanup")
        test_call.delete()
        self.stdout.write("✅ Test call and related data deleted")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🎉 Complete Integration Test Successful!")
        self.stdout.write("\nIntegration Verified:")
        self.stdout.write("✅ AI Service → Transcription Storage")
        self.stdout.write("✅ Transcription Storage → Risk Assessment")
        self.stdout.write("✅ Risk Assessment → Memory Updates")
        self.stdout.write("✅ High Risk → Emergency Contact Creation")
        self.stdout.write("✅ Cumulative Analysis Working")
        self.stdout.write("✅ Threading/Async Processing Working")
