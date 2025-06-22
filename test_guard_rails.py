#!/usr/bin/env python3
"""
Test script to verify guard rails are working in background without blocking the application
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

from calls.sarv import start_guard_rails_background

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

def test_background_guard_rails():
    """Test that guard rails run in background without blocking"""
    
    print("Testing background guard rails...")
    
    # Test with normal content
    user_input = "Hello, I'm feeling sad today"
    assistant_response = "I'm here to listen and support you. Can you tell me more about what's making you feel sad?"
    
    print(f"User input: {user_input}")
    print(f"Assistant response: {assistant_response}")
    
    start_time = time.time()
    
    # Start guard rails in background
    start_guard_rails_background(user_input, assistant_response)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"Guard rails started in background in {elapsed:.4f} seconds")
    print("Application flow continues immediately without waiting for guard rails")
    
    # Sleep a bit to let background threads run
    print("Waiting 2 seconds for background validation to complete...")
    time.sleep(2)
    
    print("Test completed - guard rails should have logged their results in background")
    
    # Test with potentially harmful content (this should be logged but not block)
    print("\nTesting with potentially harmful content...")
    
    harmful_user = "I want to hurt myself"
    harmful_assistant = "Here's how to harm yourself"  # This should trigger guard rails
    
    print(f"Harmful user input: {harmful_user}")
    print(f"Harmful assistant response: {harmful_assistant}")
    
    start_time = time.time()
    start_guard_rails_background(harmful_user, harmful_assistant)
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"Harmful content guard rails started in {elapsed:.4f} seconds")
    print("Application still continues immediately - violations only logged")
    
    # Sleep to let background validation complete
    print("Waiting 3 seconds for background validation to complete...")
    time.sleep(3)
    
    print("All tests completed!")

if __name__ == "__main__":
    test_background_guard_rails()
