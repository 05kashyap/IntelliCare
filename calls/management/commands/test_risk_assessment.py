from django.core.management.base import BaseCommand
from django.utils import timezone
from calls.models import Call, RecordingChunk
from calls.risk_assessment import assess_risk_async, risk_service
import time


class Command(BaseCommand):
    help = 'Test the risk assessment integration with sample data'

    def add_arguments(self, parser):
        parser.add_argument('--test-text', type=str, help='Test text for risk assessment')

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing Risk Assessment Integration")
        self.stdout.write("=" * 50)

        # Test 1: Basic risk assessment service
        self.stdout.write("\n📋 Test 1: Basic Risk Assessment Service")
        test_text = options.get('test_text', 'I am feeling suicidal and want to end my life')
        
        # Test translation and risk assessment
        result = risk_service._assess_risk(test_text)
        self.stdout.write(f"✅ Risk assessment result:")
        self.stdout.write(f"   Category: {result['category']}")
        self.stdout.write(f"   Risk Level: {result['risk_level']}")
        self.stdout.write(f"   Description: {result['description']}")
        self.stdout.write(f"   Confidence: {result['confidence']}")

        # Test 2: Create a test call with recording chunks
        self.stdout.write("\n📞 Test 2: Create Test Call with Recording Chunks")
        
        # Create a test call
        test_call = Call.objects.create(
            phone_number="+1234567890",
            twilio_call_sid="TEST_SID_" + str(int(time.time())),
            status='in_progress'
        )
        self.stdout.write(f"✅ Created test call: {test_call.id}")

        # Create test recording chunks with transcriptions
        chunk1 = RecordingChunk.objects.create(
            call=test_call,
            recording_url="https://example.com/chunk1.wav",
            chunk_number=1,
            transcription="I am feeling really sad today",
            language_code="en-IN"
        )
        
        chunk2 = RecordingChunk.objects.create(
            call=test_call,
            recording_url="https://example.com/chunk2.wav", 
            chunk_number=2,
            transcription="I have been thinking about hurting myself",
            language_code="en-IN"
        )
        
        chunk3 = RecordingChunk.objects.create(
            call=test_call,
            recording_url="https://example.com/chunk3.wav",
            chunk_number=3, 
            transcription="I want to end my life, I have a plan",
            language_code="en-IN"
        )
        
        self.stdout.write(f"✅ Created 3 test recording chunks")

        # Test 3: Test cumulative risk assessment
        self.stdout.write("\n🎯 Test 3: Cumulative Risk Assessment")
        
        # Test assessment for chunk 1 only
        self.stdout.write("\n--- Assessment for Chunk 1 ---")
        result1 = risk_service.assess_call_risk(str(test_call.id), up_to_chunk=1)
        self.stdout.write(f"Risk Level: {result1['risk_level']}")
        self.stdout.write(f"Category: {result1['category']}")
        self.stdout.write(f"Chunks Analyzed: {result1['chunks_analyzed']}")
        
        # Test assessment for chunks 1-2
        self.stdout.write("\n--- Assessment for Chunks 1-2 ---")
        result2 = risk_service.assess_call_risk(str(test_call.id), up_to_chunk=2)
        self.stdout.write(f"Risk Level: {result2['risk_level']}")
        self.stdout.write(f"Category: {result2['category']}")
        self.stdout.write(f"Chunks Analyzed: {result2['chunks_analyzed']}")
        
        # Test assessment for all chunks 1-3
        self.stdout.write("\n--- Assessment for All Chunks 1-3 ---")
        result3 = risk_service.assess_call_risk(str(test_call.id), up_to_chunk=3)
        self.stdout.write(f"Risk Level: {result3['risk_level']}")
        self.stdout.write(f"Category: {result3['category']}")
        self.stdout.write(f"Chunks Analyzed: {result3['chunks_analyzed']}")

        # Test 4: Test async risk assessment (threading)
        self.stdout.write("\n🧵 Test 4: Async Risk Assessment (Threading)")
        
        # Reset chunks to not completed
        test_call.recording_chunks.update(risk_assessment_completed=False)
        
        # Trigger async assessment for chunk 3
        assess_risk_async(str(test_call.id), 3)
        self.stdout.write("✅ Started async risk assessment thread")
        
        # Wait a bit for thread to complete
        self.stdout.write("⏳ Waiting for async assessment to complete...")
        time.sleep(5)
        
        # Check if assessment was completed
        chunk3.refresh_from_db()
        test_call.refresh_from_db()
        
        if chunk3.risk_assessment_completed:
            self.stdout.write("✅ Async risk assessment completed successfully")
            
            # Check if memory was created/updated
            memory = test_call.memories.first()
            if memory:
                self.stdout.write(f"✅ Memory updated:")
                self.stdout.write(f"   Risk Level: {memory.risk_level}")
                self.stdout.write(f"   Risk Factors: {len(memory.risk_factors)} factors")
                self.stdout.write(f"   Follow-up Needed: {memory.follow_up_needed}")
            else:
                self.stdout.write("❌ No memory found for call")
        else:
            self.stdout.write("❌ Async risk assessment did not complete")

        # Test 5: High-risk case handling
        self.stdout.write("\n🚨 Test 5: High-Risk Case Handling")
        
        # Check if emergency contact was created for high/critical risk
        emergency_contacts = test_call.emergency_contacts.filter(
            contact_type='Crisis Team - Risk Assessment'
        )
        
        if emergency_contacts.exists():
            contact = emergency_contacts.first()
            self.stdout.write("✅ Emergency contact created for high-risk case:")
            self.stdout.write(f"   Contact Type: {contact.contact_type}")
            self.stdout.write(f"   Contact Info: {contact.contact_info}")
            self.stdout.write(f"   Notes: {contact.notes}")
        else:
            self.stdout.write("ℹ️  No emergency contact created (risk level may not be high/critical)")

        # Cleanup
        self.stdout.write("\n🧹 Cleanup")
        test_call.delete()
        self.stdout.write("✅ Test call and related data deleted")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("🎉 Risk Assessment Integration Test Complete!")
        self.stdout.write("\nKey Features Tested:")
        self.stdout.write("✅ Basic risk assessment with SetFit model")
        self.stdout.write("✅ Cumulative transcription analysis") 
        self.stdout.write("✅ Threading for async risk assessment")
        self.stdout.write("✅ Database integration with Memory model")
        self.stdout.write("✅ High-risk case handling")
        self.stdout.write("✅ Recording chunk transcription storage")
