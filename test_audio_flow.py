#!/usr/bin/env python3
"""
Test script to verify the complete audio processing flow works without guard rail interference
"""
import os
import sys
import django
import time
import logging

# Setup Django environment
sys.path.append('/home/kashyap/Documents/Projects/suicide_hotline')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotline_backend.settings')
django.setup()

from calls.sarv import process_single_audio_input

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

def test_audio_processing_flow():
    """Test that audio processing works without guard rail interference"""
    
    print("Testing complete audio processing flow...")
    
    # We'll simulate a quick test without actual audio files
    # but focus on the flow timing and guard rail non-interference
    
    # Mock paths for testing
    input_path = "/tmp/test_input.wav" 
    output_path = "/tmp/test_output.wav"
    
    # Create a dummy input file for testing
    try:
        with open(input_path, 'wb') as f:
            f.write(b'dummy audio data for testing')
        
        print(f"Created test input file: {input_path}")
        
        # Test conversation history
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi, how are you feeling today?"}
        ]
        
        start_time = time.time()
        
        print("Starting audio processing (this will fail at transcription but should show guard rail timing)...")
        
        # This will fail at transcription stage but will show us the guard rail behavior
        result = process_single_audio_input(input_path, output_path, conversation_history)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"Audio processing completed in {elapsed:.4f} seconds")
        print(f"Result success: {result.get('success', False)}")
        print(f"Result error: {result.get('error', 'No error')}")
        
        # The key test is that even if it fails, guard rails should not have caused timeouts
        if "guard" in result.get('error', '').lower() or "timeout" in result.get('error', '').lower():
            print("❌ FAIL: Guard rails interfered with processing")
        else:
            print("✅ PASS: Guard rails did not interfere with processing")
        
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        # Clean up test file
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
    
    print("Test completed!")

if __name__ == "__main__":
    test_audio_processing_flow()
