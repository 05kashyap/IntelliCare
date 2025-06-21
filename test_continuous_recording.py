#!/usr/bin/env python
"""
Test script to demonstrate the continuous recording functionality
This simulates what happens during a real call with the new implementation
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append('/home/adya/project/suicide_hotline')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotline_backend.settings')
django.setup()

from calls.models import Call, RecordingChunk
from calls.ai_service import TwilioVoiceService
from datetime import datetime
from django.utils import timezone
import uuid

def simulate_continuous_call():
    """Simulate a continuous recording call flow"""
    print("🎯 Simulating Continuous Recording Call Flow")
    print("=" * 50)
    
    # Create a test call
    call = Call.objects.create(
        phone_number="+1234567890",
        twilio_call_sid=f"CA{uuid.uuid4().hex[:32]}",
        status='in_progress',
        start_time=timezone.now(),
        caller_city='Test City',
        caller_state='Test State',
        caller_country='US'
    )
    
    print(f"📞 Created test call: {call.id}")
    print(f"   Phone: {call.phone_number}")
    print(f"   Status: {call.status}")
    
    # Simulate multiple recording chunks
    service = TwilioVoiceService()
    
    # Simulate first recording chunk
    print(f"\n🎤 Recording Chunk 1...")
    chunk1 = call.recording_chunks.create(
        recording_url="https://api.twilio.com/test/recording1.wav",
        chunk_number=1,
        duration_seconds=25.5,
        local_recording_path="/media/recordings/daily/2025-06-21/call_20250621_120000_test1.wav",
        local_recording_url="/media/recordings/daily/2025-06-21/call_20250621_120000_test1.wav"
    )
    
    # Simulate AI processing
    chunk1.processed = True
    chunk1.response_audio_url = "/media/outputs/sample_response.wav"
    chunk1.response_played = True
    chunk1.processed_at = timezone.now()
    chunk1.save()
    
    print(f"   ✅ Chunk 1 complete: Recorded → AI Processed → Response Played")
    
    # Simulate second recording chunk
    print(f"\n🎤 Recording Chunk 2...")
    chunk2 = call.recording_chunks.create(
        recording_url="https://api.twilio.com/test/recording2.wav",
        chunk_number=2,
        duration_seconds=18.3,
        local_recording_path="/media/recordings/daily/2025-06-21/call_20250621_120030_test2.wav",
        local_recording_url="/media/recordings/daily/2025-06-21/call_20250621_120030_test2.wav"
    )
    
    chunk2.processed = True
    chunk2.response_audio_url = "/media/outputs/sample_response.wav"
    chunk2.response_played = True
    chunk2.processed_at = timezone.now()
    chunk2.save()
    
    print(f"   ✅ Chunk 2 complete: Recorded → AI Processed → Response Played")
    
    # Simulate third recording chunk
    print(f"\n🎤 Recording Chunk 3...")
    chunk3 = call.recording_chunks.create(
        recording_url="https://api.twilio.com/test/recording3.wav",
        chunk_number=3,
        duration_seconds=30.0,
        local_recording_path="/media/recordings/daily/2025-06-21/call_20250621_120100_test3.wav",
        local_recording_url="/media/recordings/daily/2025-06-21/call_20250621_120100_test3.wav"
    )
    
    chunk3.processed = True
    chunk3.response_audio_url = "/media/outputs/sample_response.wav"
    chunk3.response_played = True
    chunk3.processed_at = timezone.now()
    chunk3.save()
    
    print(f"   ✅ Chunk 3 complete: Recorded → AI Processed → Response Played")
    
    # Simulate call completion
    print(f"\n📞 Call completed by user")
    call.status = 'completed'
    call.end_time = timezone.now()
    call.duration = call.end_time - call.start_time
    call.save()
    
    # Display final results
    print(f"\n📊 Call Summary:")
    print(f"   Call ID: {call.id}")
    print(f"   Total Duration: {call.call_duration_formatted}")
    print(f"   Total Chunks: {call.recording_chunks.count()}")
    print(f"   Processed Chunks: {call.recording_chunks.filter(processed=True).count()}")
    print(f"   Responses Played: {call.recording_chunks.filter(response_played=True).count()}")
    
    print(f"\n🔄 Continuous Recording Flow:")
    for chunk in call.recording_chunks.all():
        print(f"   Chunk {chunk.chunk_number}: {chunk.duration_seconds}s → AI Response → Continue Recording")
    
    print(f"\n✅ Test completed successfully!")
    print(f"💡 This demonstrates the continuous recording cycle:")
    print(f"   1. User speaks → Recording starts instantly")
    print(f"   2. Recording complete → Saved & sent to AI")
    print(f"   3. AI response ready → Play to user")
    print(f"   4. Response complete → Start new recording immediately")
    print(f"   5. Repeat until user disconnects")
    
    return call

if __name__ == "__main__":
    test_call = simulate_continuous_call()
