"""
Example service for integrating with LLM agent and processing audio
This file shows how you would integrate your AI agent with the Django backend
"""
import requests
import json
import asyncio
import threading
import shutil
import hashlib
import time
import traceback
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Play, Record
from twilio.rest import Client
from .models import Call, Memory, RecordingChunk
from .sarv import transcribe_input, query_llm, convert_to_audio_and_save, system_prompt
import os
from datetime import datetime, timedelta
import uuid

class LocalRecordingStorage:
    """Handle local storage of call recordings"""
    
    def __init__(self):
        self.recordings_dir = os.path.join(settings.MEDIA_ROOT, 'recordings')
        # Create recordings directory if it doesn't exist
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        # Create subdirectories for better organization
        self.daily_dir = os.path.join(self.recordings_dir, 'daily')
        self.archived_dir = os.path.join(self.recordings_dir, 'archived')
        os.makedirs(self.daily_dir, exist_ok=True)
        os.makedirs(self.archived_dir, exist_ok=True)
    
    def store_recording_locally(self, recording_url, call_id, call_sid=None):
        """
        Download recording from Twilio and store locally
        Returns local file path and URL
        """
        try:
            # Download audio from Twilio
            audio_response = requests.get(recording_url, auth=(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            ))
            
            if audio_response.status_code == 200:
                # Generate filename with timestamp and call info
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_extension = self._get_file_extension(audio_response.headers.get('content-type', 'audio/wav'))
                
                # Create filename: call_YYYYMMDD_HHMMSS_callid.ext
                filename = f"call_{timestamp}_{str(call_id)[:8]}{file_extension}"
                
                # Store in daily directory (organize by date)
                date_dir = os.path.join(self.daily_dir, datetime.now().strftime('%Y-%m-%d'))
                os.makedirs(date_dir, exist_ok=True)
                
                file_path = os.path.join(date_dir, filename)
                
                # Write audio file
                with open(file_path, 'wb') as f:
                    f.write(audio_response.content)
                
                # Generate MD5 hash for integrity verification
                audio_hash = hashlib.md5(audio_response.content).hexdigest()
                
                # Create relative path for URL
                relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                local_url = f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                
                # Store metadata
                metadata = {
                    'original_url': recording_url,
                    'local_path': file_path,
                    'local_url': local_url,
                    'filename': filename,
                    'file_size': len(audio_response.content),
                    'content_type': audio_response.headers.get('content-type', 'audio/wav'),
                    'md5_hash': audio_hash,
                    'stored_at': datetime.now().isoformat(),
                    'call_id': str(call_id),
                    'call_sid': call_sid
                }
                
                # Save metadata file
                metadata_path = file_path + '.meta.json'
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                print(f"Recording stored locally: {file_path}")
                return metadata
                
            else:
                print(f"Failed to download recording: HTTP {audio_response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error storing recording locally: {e}")
            return None
    
    def _get_file_extension(self, content_type):
        """Get appropriate file extension based on content type"""
        content_type_map = {
            'audio/wav': '.wav',
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/x-wav': '.wav',
            'audio/wave': '.wav'
        }
        return content_type_map.get(content_type, '.wav')
    
    def get_local_recording_path(self, call_id):
        """Get local recording path for a call"""
        try:
            call = Call.objects.get(id=call_id)
            if hasattr(call, 'local_recording_path') and call.local_recording_path:
                return call.local_recording_path
        except Call.DoesNotExist:
            pass
        return None
    
    def verify_recording_integrity(self, file_path):
        """Verify recording file integrity using stored MD5 hash"""
        try:
            metadata_path = file_path + '.meta.json'
            
            if os.path.exists(file_path) and os.path.exists(metadata_path):
                # Read metadata
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Calculate current file hash
                with open(file_path, 'rb') as f:
                    current_hash = hashlib.md5(f.read()).hexdigest()
                
                return current_hash == metadata.get('md5_hash')
            
            return False
            
        except Exception as e:
            print(f"Error verifying recording integrity: {e}")
            return False
    
    def archive_old_recordings(self, days_old=30):
        """Move recordings older than specified days to archive"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            archived_count = 0
            
            for root, dirs, files in os.walk(self.daily_dir):
                for file in files:
                    if file.endswith('.wav') or file.endswith('.mp3'):
                        file_path = os.path.join(root, file)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_mtime < cutoff_date:
                            # Move to archive
                            archive_subdir = os.path.join(self.archived_dir, file_mtime.strftime('%Y-%m'))
                            os.makedirs(archive_subdir, exist_ok=True)
                            
                            archive_path = os.path.join(archive_subdir, file)
                            shutil.move(file_path, archive_path)
                            
                            # Move metadata file too
                            metadata_file = file_path + '.meta.json'
                            if os.path.exists(metadata_file):
                                shutil.move(metadata_file, archive_path + '.meta.json')
                            
                            archived_count += 1
            
            print(f"Archived {archived_count} old recordings")
            return archived_count
            
        except Exception as e:
            print(f"Error archiving recordings: {e}")
            return 0
    
    def get_storage_stats(self):
        """Get storage statistics for recordings"""
        try:
            stats = {
                'daily_recordings': 0,
                'archived_recordings': 0,
                'total_size_mb': 0,
                'daily_size_mb': 0,
                'archived_size_mb': 0
            }
            
            # Count daily recordings
            for root, dirs, files in os.walk(self.daily_dir):
                for file in files:
                    if file.endswith(('.wav', '.mp3')):
                        stats['daily_recordings'] += 1
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        stats['daily_size_mb'] += file_size / (1024 * 1024)
            
            # Count archived recordings
            for root, dirs, files in os.walk(self.archived_dir):
                for file in files:
                    if file.endswith(('.wav', '.mp3')):
                        stats['archived_recordings'] += 1
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        stats['archived_size_mb'] += file_size / (1024 * 1024)
            
            stats['total_size_mb'] = stats['daily_size_mb'] + stats['archived_size_mb']
            
            # Round to 2 decimal places
            for key in ['total_size_mb', 'daily_size_mb', 'archived_size_mb']:
                stats[key] = round(stats[key], 2)
            
            return stats
            
        except Exception as e:
            print(f"Error getting storage stats: {e}")
            return None


# Global instance for local recording storage
local_storage = LocalRecordingStorage()


class AIAgentService:
    """Service for interacting with AI agent"""
    
    def __init__(self):
        self.agent_api_url = getattr(settings, 'AI_AGENT_API_URL', 'http://localhost:5000')
    
    def process_call_audio(self, call_id):
        """
        Process audio from a call and create memory record
        This would be called after a recording is completed
        """
        try:
            call = Call.objects.get(id=call_id)
            
            # Step 1: Send audio to AI agent for processing
            agent_response = self._send_audio_to_agent(call.audio_file_url)
            
            # Step 2: Create memory record from agent response
            memory = self._create_memory_from_response(call, agent_response)
            
            # Step 3: Update call with transcription if provided
            if agent_response.get('transcription'):
                call.transcription = agent_response['transcription']
                call.save()
            
            return memory
            
        except Call.DoesNotExist:
            raise ValueError(f"Call {call_id} not found")
        except Exception as e:
            print(f"Error processing call audio: {e}")
            raise
    
    def _send_audio_to_agent(self, audio_url):
        """
        Send audio URL to AI agent for processing
        Replace this with your actual AI agent API call
        """
        payload = {
            'audio_url': audio_url,
            'task': 'crisis_intervention_analysis'
        }
        
        # This is a mock response - replace with actual API call
        # response = requests.post(f"{self.agent_api_url}/process_audio", json=payload)
        # return response.json()
        
        # Mock response for demonstration
        return {
        }

# Example usage in your Django views or Celery tasks
def process_call_audio_task(call_id):
    """
    This could be a Celery task that processes audio after recording completion
    """
    agent_service = AIAgentService()
    try:
        memory = agent_service.process_call_audio(call_id)
        print(f"Created memory {memory.id} for call {call_id}")
        
        # If high risk, trigger additional actions
        if memory.risk_level in ['high', 'critical']:
            # Send alerts, create emergency contacts, etc.
            handle_high_risk_case(memory)
            
    except Exception as e:
        print(f"Error processing call {call_id}: {e}")


def handle_high_risk_case(memory):
    """Handle high-risk cases with additional actions"""
    from .models import EmergencyContact
    
    # Create emergency contact record
    EmergencyContact.objects.create(
        call=memory.call,
        contact_type='Crisis Team',
        contact_info='Emergency services contacted',
        notes=f'High risk case - {memory.risk_level} level',
        contacted=True
    )
    
    # Here you could also:
    # - Send notifications to supervisors
    # - Trigger automatic follow-up calls
    # - Create urgent alerts in the system
    # - Contact emergency services if critical


# Example API integration endpoint
def webhook_ai_agent_update(request):
    """
    Webhook endpoint for AI agent to send updates
    Your AI agent can call this endpoint to update memories in real-time
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        call_id = data.get('call_id')
        
        try:
            call = Call.objects.get(id=call_id)
            memory = call.memories.first()
            
            if memory:
                # Update memory with new analysis
                if 'risk_level' in data:
                    memory.risk_level = data['risk_level']
                if 'emotional_state' in data:
                    memory.primary_emotion = data['emotional_state']
                if 'conversation_update' in data:
                    memory.conversation_summary += f"\n\nUpdate: {data['conversation_update']}"
                
                memory.save()
                
                return JsonResponse({'success': True})
            
        except Call.DoesNotExist:
            return JsonResponse({'error': 'Call not found'}, status=404)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@require_http_methods(["POST"])
def handle_twilio_voice_request(request):
    """
    Handle incoming voice calls from Twilio
    This will initiate the call processing workflow
    """
    try:
        # Extract Twilio parameters
        from_number = request.POST.get('From')
        to_number = request.POST.get('To')
        call_sid = request.POST.get('CallSid')
        recording_url = request.POST.get('RecordingUrl')
        transcription_text = request.POST.get('TranscriptionText', '')
        
        # Log the incoming call
        print(f"Incoming call from {from_number} to {to_number}, SID: {call_sid}")
        
        # Create or update the Call record in the database
        call, created = Call.objects.get_or_create(
            call_sid=call_sid,
            defaults={
                'from_number': from_number,
                'to_number': to_number,
                'status': 'completed' if recording_url else 'in_progress',
                'recording_url': recording_url,
                'transcription': transcription_text,
                'start_time': datetime.utcnow(),
                'end_time': datetime.utcnow() + timedelta(seconds=30),  # Estimate end time
                'duration': 30,  # Placeholder duration
            }
        )
        
        if not created:
            # Update existing call record with new information
            call.recording_url = recording_url
            call.transcription = transcription_text
            call.status = 'completed' if recording_url else 'in_progress'
            call.end_time = datetime.utcnow()
            call.duration = (call.end_time - call.start_time).seconds
            call.save()
        
        # If recording is available, process the audio
        if recording_url:
            # Start the audio processing in a separate thread
            threading.Thread(target=process_call_audio_task, args=(call.id,)).start()
        
        # Respond to Twilio with a simple message
        response = VoiceResponse()
        response.say("Thank you for your call. We are processing your information.", voice="alice")
        return HttpResponse(str(response), content_type='text/xml')
    
    except Exception as e:
        print(f"Error handling Twilio request: {e}")
        return HttpResponse(status=500)


class TwilioVoiceService:
    """Service for handling Twilio voice calls with async audio processing"""
    
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.phone_number = settings.TWILIO_PHONE_NUMBER
        self.active_calls = {}  # Store active call states
        
    def handle_incoming_call(self, request):
        """Handle incoming Twilio voice call"""
        response = VoiceResponse()
        
        # Get caller info
        caller_number = request.POST.get('From', '')
        call_sid = request.POST.get('CallSid', '')
        
        # Create call record
        call = Call.objects.create(
            phone_number=caller_number,
            twilio_call_sid=call_sid,
            status='in_progress',
            start_time=datetime.now(),
            caller_city=request.POST.get('FromCity', ''),
            caller_state=request.POST.get('FromState', ''),
            caller_country=request.POST.get('FromCountry', '')
        )
        
        # Store call state
        self.active_calls[call_sid] = {
            'call_id': str(call.id),
            'status': 'listening',
            'audio_chunks': [],
            'recording_count': 0
        }
        
        # Start recording immediately without any welcome message
        response.record(
            action=f'/twilio/recording/{call.id}/',
            method='POST',
            max_length=30,  # 30 seconds max per recording
            play_beep=False,
            trim='trim-silence',
            recording_status_callback=f'/twilio/recording-status/{call.id}/',
            recording_status_callback_method='POST'
        )
        
        return HttpResponse(str(response), content_type='text/xml')
    
    def handle_recording_complete(self, request, call_id):
        """Handle when recording is complete and process audio"""
        recording_url = request.POST.get('RecordingUrl', '')
        recording_sid = request.POST.get('RecordingSid', '')
        call_sid = request.POST.get('CallSid', '')
        
        response = VoiceResponse()
        
        try:
            call = Call.objects.get(id=call_id)
            
            # Get current chunk number
            chunk_number = call.recording_chunks.count() + 1
            
            # Store recording information
            recording_chunk = None
            if recording_url:
                # Store recording locally
                local_metadata = local_storage.store_recording_locally(
                    recording_url, call_id, call_sid
                )
                
                # Create recording chunk record
                recording_chunk = call.recording_chunks.create(
                    recording_url=recording_url,
                    chunk_number=chunk_number,
                    local_recording_path=local_metadata['local_path'] if local_metadata else None,
                    local_recording_url=local_metadata['local_url'] if local_metadata else None
                )
                
                # Update main call record with latest recording URL (for backward compatibility)
                call.audio_file_url = recording_url
                if local_metadata:
                    call.local_recording_path = local_metadata['local_path']
                    call.local_recording_url = local_metadata['local_url']
                    
                call.save()
                print(f"Recording chunk {chunk_number} stored for call {call_id}")
            
            # Update active call tracking
            if call_sid in self.active_calls:
                self.active_calls[call_sid]['recording_count'] = chunk_number
                self.active_calls[call_sid]['audio_chunks'].append({
                    'recording_url': recording_url,
                    'chunk_id': str(recording_chunk.id) if recording_chunk else None,
                    'chunk_number': chunk_number,
                    'local_path': recording_chunk.local_recording_path if recording_chunk else None,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Wait for Sarvam AI response - pass recording URL for processing
            response_audio_url = self.wait_for_ai_response(call_id, recording_url)
            
            if response_audio_url:
                # Update recording chunk with response info
                if recording_chunk:
                    recording_chunk.response_audio_url = response_audio_url
                    recording_chunk.processed = True
                    recording_chunk.processed_at = datetime.now()
                    recording_chunk.save()
                
                # Play the AI response audio file
                response.play(response_audio_url)
                
                # Mark response as played
                if recording_chunk:
                    recording_chunk.response_played = True
                    recording_chunk.save()
                
                # After playing response, start recording again for continuous conversation
                response.record(
                    action=f'/twilio/recording/{call.id}/',
                    method='POST',
                    max_length=30,
                    play_beep=False,
                    trim='trim-silence',
                    recording_status_callback=f'/twilio/recording-status/{call.id}/',
                    recording_status_callback_method='POST'
                )
            else:
                # If no response available, continue recording anyway
                response.record(
                    action=f'/twilio/recording/{call.id}/',
                    method='POST',
                    max_length=30,
                    play_beep=False,
                    trim='trim-silence',
                    recording_status_callback=f'/twilio/recording-status/{call.id}/',
                    recording_status_callback_method='POST'
                )
        
        except Call.DoesNotExist:
            # If call not found, just continue recording
            response.record(
                action=f'/twilio/recording/{call_id}/',
                method='POST',
                max_length=30,
                play_beep=False,
                trim='trim-silence'
            )
        except Exception as e:
            print(f"Error in handle_recording_complete: {e}")
            # Continue recording on error
            response.record(
                action=f'/twilio/recording/{call_id}/',
                method='POST',
                max_length=30,
                play_beep=False,
                trim='trim-silence'
            )
        
        return HttpResponse(str(response), content_type='text/xml')
    
    def wait_for_ai_response(self, call_id, recording_url=None):
        """
        Process audio with Sarvam AI and return the audio file URL
        """
        print(f"=== Starting AI processing for call {call_id} ===")
        print(f"Recording URL: {recording_url}")
        
        try:
            # If we have a recording URL, download it first
            if recording_url:
                local_audio_path = self._download_audio_for_processing(recording_url, call_id)
                if not local_audio_path:
                    print(f"FALLBACK TRIGGERED: Failed to download audio for call {call_id}")
                    return self._get_fallback_response()
            else:
                print(f"FALLBACK TRIGGERED: No recording URL provided for call {call_id}")
                return self._get_fallback_response()
            
            # Process with Sarvam AI
            print(f"Processing audio with Sarvam AI...")
            response_audio_path = self._process_with_sarvam_ai(local_audio_path, call_id)
            
            if response_audio_path and os.path.exists(response_audio_path):
                print(f"Sarvam AI processing completed successfully")
                # Move response to media/outputs directory and return URL
                response_url = self._save_response_to_media(response_audio_path, call_id)
                if response_url:
                    print(f"=== AI processing SUCCESS for call {call_id} ===")
                    print(f"Response URL: {response_url}")
                    return response_url
                else:
                    print(f"FALLBACK TRIGGERED: Failed to save response to media for call {call_id}")
                    return self._get_fallback_response()
            else:
                print(f"FALLBACK TRIGGERED: Sarvam AI processing failed for call {call_id}")
                print(f"Response path: {response_audio_path}")
                print(f"Path exists: {os.path.exists(response_audio_path) if response_audio_path else 'N/A'}")
                return self._get_fallback_response()
                
        except Exception as e:
            print(f"FALLBACK TRIGGERED: Error processing audio with Sarvam AI: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_response()
    
    def _download_audio_for_processing(self, recording_url, call_id):
        """Download audio from Twilio for Sarvam AI processing"""
        try:
            print(f"Downloading audio from Twilio for call {call_id}")
            print(f"Recording URL: {recording_url}")
            
            # Download audio from Twilio
            audio_response = requests.get(recording_url, auth=(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            ))
            
            print(f"Twilio response status: {audio_response.status_code}")
            
            if audio_response.status_code == 200:
                # Create temporary file for processing
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"input_{timestamp}_{str(call_id)[:8]}.wav"
                
                # Save to a processing directory
                processing_dir = os.path.join(settings.MEDIA_ROOT, 'processing')
                os.makedirs(processing_dir, exist_ok=True)
                
                input_file_path = os.path.join(processing_dir, filename)
                
                with open(input_file_path, 'wb') as f:
                    f.write(audio_response.content)
                
                file_size = len(audio_response.content)
                print(f"Downloaded audio for processing: {input_file_path} (size: {file_size} bytes)")
                
                # Verify file was created
                if os.path.exists(input_file_path):
                    actual_size = os.path.getsize(input_file_path)
                    print(f"File verification: {input_file_path} exists (size: {actual_size} bytes)")
                    return input_file_path
                else:
                    print(f"ERROR: Downloaded file not found: {input_file_path}")
                    return None
            else:
                print(f"Failed to download audio: HTTP {audio_response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error downloading audio for processing: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _process_with_sarvam_ai(self, input_audio_path, call_id):
        """Process audio using Sarvam AI functions"""
        try:
            print(f"Processing audio with Sarvam AI for call {call_id}")
            print(f"Input audio path: {input_audio_path}")
            
            # Verify input file exists
            if not os.path.exists(input_audio_path):
                print(f"Input audio file does not exist: {input_audio_path}")
                return None
            
            # Get conversation state for this call
            conversation = self._get_conversation_state(call_id)
            
            # Generate output file path with call ID for matching
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"response_{timestamp}_{str(call_id)[:8]}.wav"
            
            # Save to processing directory first
            processing_dir = os.path.join(settings.MEDIA_ROOT, 'processing')
            os.makedirs(processing_dir, exist_ok=True)
            response_path = os.path.join(processing_dir, output_filename)
            
            print(f"Expected output path: {response_path}")
            
            # Process with Sarvam AI
            from .sarv import process_single_audio_input
            print(f"Calling Sarvam AI with input: {input_audio_path}, output: {response_path}")
            result = process_single_audio_input(input_audio_path, response_path, conversation)
            
            print(f"Sarvam AI result: {result}")
            
            if result["success"]:
                # Wait for the output file to be created (async file creation)
                file_created = self._wait_for_file_creation(response_path, timeout=30)
                if not file_created:
                    print(f"ERROR: Sarvam AI reported success but output file not created within timeout: {response_path}")
                    return None
                
                file_size = os.path.getsize(response_path)
                print(f"Output file created successfully: {response_path} (size: {file_size} bytes)")
                
                # Save updated conversation state
                self._save_conversation_state(call_id, result["conversation_history"])
                
                print(f"Sarvam AI processing successful for call {call_id}")
                print(f"Transcription: {result['transcription']}")
                print(f"Response: {result['response_text']}")
                
                # Check if conversation should end
                if result["should_end"]:
                    print(f"Conversation ending for call {call_id}")
                    # You might want to handle call ending here
                
                return response_path
            else:
                print(f"Sarvam AI processing failed for call {call_id}: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"Error processing with Sarvam AI: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_conversation_state(self, call_id):
        """Get conversation state for a call"""
        try:
            call = Call.objects.get(id=call_id)
            
            # Get existing conversation from conversation_state field
            if call.conversation_state:
                return call.conversation_state
            else:
                return [{"role": "system", "content": system_prompt}]
                
        except Call.DoesNotExist:
            return [{"role": "system", "content": system_prompt}]
        except Exception as e:
            print(f"Error getting conversation state: {e}")
            return [{"role": "system", "content": system_prompt}]
    
    def _save_conversation_state(self, call_id, conversation):
        """Save conversation state for a call"""
        try:
            call = Call.objects.get(id=call_id)
            # Save conversation state in the new field
            call.conversation_state = conversation
            
            # Also update transcription field with the last user message for backward compatibility
            if conversation:
                last_user_message = ""
                for msg in reversed(conversation):
                    if msg.get("role") == "user":
                        last_user_message = msg.get("content", "")
                        break
                
                if last_user_message:
                    if call.transcription:
                        call.transcription += f"\n{last_user_message}"
                    else:
                        call.transcription = last_user_message
            
            call.save()
                    
        except Call.DoesNotExist:
            pass
        except Exception as e:
            print(f"Error saving conversation state: {e}")
    
    def _wait_for_file_creation(self, file_path, timeout=30, poll_interval=0.5):
        """
        Wait for a file to be created, with timeout
        Returns True if file is created, False if timeout reached
        """
        print(f"Waiting for file creation: {file_path} (timeout: {timeout}s)")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if os.path.exists(file_path):
                # File exists, but let's also check if it has content
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > 0:
                        print(f"File created successfully: {file_path} (size: {file_size} bytes, waited: {time.time() - start_time:.1f}s)")
                        return True
                    else:
                        # File exists but is empty, wait a bit more
                        print(f"File exists but is empty, waiting... ({time.time() - start_time:.1f}s)")
                except OSError:
                    # File might be being written to, wait a bit more
                    pass
            
            time.sleep(poll_interval)
        
        print(f"Timeout waiting for file creation: {file_path} (waited: {timeout}s)")
        return False
    
    def _save_response_to_media(self, response_path, call_id):
        """Save response audio to media/outputs directory and return URL"""
        try:
            print(f"Saving response to media for call {call_id}")
            print(f"Source path: {response_path}")
            
            # Verify source file exists
            if not os.path.exists(response_path):
                print(f"ERROR: Source response file does not exist: {response_path}")
                return None
            
            outputs_dir = os.path.join(settings.MEDIA_ROOT, 'outputs')
            os.makedirs(outputs_dir, exist_ok=True)
            
            # Create unique filename for this response with call ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"response_{timestamp}_{str(call_id)[:8]}.wav"
            media_path = os.path.join(outputs_dir, filename)
            
            print(f"Destination path: {media_path}")
            
            # Copy the file to media directory
            shutil.copy2(response_path, media_path)
            
            # Verify the file was copied successfully
            if os.path.exists(media_path):
                file_size = os.path.getsize(media_path)
                print(f"File copied successfully to: {media_path} (size: {file_size} bytes)")
                
                # Return the media URL
                response_url = f"{settings.MEDIA_URL}outputs/{filename}"
                print(f"Generated response URL: {response_url}")
                return response_url
            else:
                print(f"ERROR: File copy failed - destination file not found: {media_path}")
                return None
            
        except Exception as e:
            print(f"Error saving response to media: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_fallback_response(self):
        """Get fallback response when Sarvam AI processing fails"""
        print("=== USING FALLBACK RESPONSE ===")
        
        # Check if sample response file exists
        outputs_dir = os.path.join(settings.MEDIA_ROOT, 'outputs')
        sample_response = os.path.join(outputs_dir, 'sample_response.wav')
        
        if os.path.exists(sample_response):
            response_url = f"{settings.MEDIA_URL}outputs/sample_response.wav"
            print(f"Using existing fallback response: {response_url}")
            return response_url
        
        # If no sample file in media, check the main outputs directory
        main_outputs_dir = os.path.join(settings.BASE_DIR, 'outputs')
        main_sample_response = os.path.join(main_outputs_dir, 'sample_response.wav')
        
        if os.path.exists(main_sample_response):
            try:
                os.makedirs(outputs_dir, exist_ok=True)
                shutil.copy2(main_sample_response, sample_response)
                response_url = f"{settings.MEDIA_URL}outputs/sample_response.wav"
                print(f"Using fallback response (copied from {main_sample_response}): {response_url}")
                return response_url
            except Exception as e:
                print(f"Error copying fallback file: {e}")
        
        print(f"ERROR: No fallback response available")
        return None
    
    def continue_conversation(self, request, call_id):
        """Continue conversation - simplified since we handle everything in recording complete"""
        response = VoiceResponse()
        
        # Since we're using continuous recording cycle, just start recording again
        response.record(
            action=f'/twilio/recording/{call_id}/',
            method='POST',
            max_length=30,
            play_beep=False,
            trim='trim-silence',
            recording_status_callback=f'/twilio/recording-status/{call_id}/',
            recording_status_callback_method='POST'
        )
        
        return HttpResponse(str(response), content_type='text/xml')
    
    def handle_user_choice(self, request, call_id):
        """Handle user's choice to continue or end - simplified for continuous recording"""
        response = VoiceResponse()
        
        # Since we're doing continuous recording, just continue with recording
        response.record(
            action=f'/twilio/recording/{call_id}/',
            method='POST',
            max_length=30,
            play_beep=False,
            trim='trim-silence',
            recording_status_callback=f'/twilio/recording-status/{call_id}/',
            recording_status_callback_method='POST'
        )
        
        return HttpResponse(str(response), content_type='text/xml')
    
    def get_audio_for_processing(self, recording_url):
        """
        Extract audio data from Twilio recording URL for further processing
        Returns audio data that can be sent to AI processing
        """
        try:
            # Download the audio file
            audio_response = requests.get(recording_url, auth=(
                settings.TWILIO_ACCOUNT_SID, 
                settings.TWILIO_AUTH_TOKEN
            ))
            
            if audio_response.status_code == 200:
                # Return audio data for processing
                return {
                    'audio_data': audio_response.content,
                    'audio_url': recording_url,
                    'content_type': audio_response.headers.get('content-type', 'audio/wav'),
                    'size': len(audio_response.content)
                }
            else:
                print(f"Failed to download audio: {audio_response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return None
    
    def play_audio_to_caller(self, call_sid, audio_file_url):
        """
        Play an audio file to the caller during an active call
        """
        try:
            # Update the call to play audio
            call = self.client.calls(call_sid).update(
                twiml=f'<Response><Play>{audio_file_url}</Play></Response>'
            )
            return True
        except Exception as e:
            print(f"Error playing audio to caller: {e}")
            return False
    
    def end_call(self, call_sid):
        """End an active call"""
        try:
            call = self.client.calls(call_sid).update(status='completed')
            
            # Clean up tracking
            if call_sid in self.active_calls:
                del self.active_calls[call_sid]
                
            return True
        except Exception as e:
            print(f"Error ending call: {e}")
            return False


# Webhook view functions for Twilio
@csrf_exempt
@require_http_methods(["POST"])
def twilio_voice_webhook(request):
    """Webhook for incoming Twilio voice calls"""
    service = TwilioVoiceService()
    return service.handle_incoming_call(request)


@csrf_exempt
@require_http_methods(["POST"])  
def twilio_recording_webhook(request, call_id):
    """Webhook for when recording is completed"""
    service = TwilioVoiceService()
    return service.handle_recording_complete(request, call_id)


@csrf_exempt
@require_http_methods(["POST"])
def twilio_continue_webhook(request, call_id):
    """Webhook to continue conversation"""
    service = TwilioVoiceService()
    return service.continue_conversation(request, call_id)


@csrf_exempt
@require_http_methods(["POST"])
def twilio_user_choice_webhook(request, call_id):
    """Webhook for handling user's choice"""
    service = TwilioVoiceService()
    return service.handle_user_choice(request, call_id)


@csrf_exempt
@require_http_methods(["POST"])
def twilio_status_webhook(request):
    """Webhook for call status updates"""
    call_sid = request.POST.get('CallSid', '')
    call_status = request.POST.get('CallStatus', '')
    
    print(f"Call status update: {call_sid} - {call_status}")
    
    # Update call status in database
    try:
        call = Call.objects.get(twilio_call_sid=call_sid)
        
        if call_status == 'completed':
            call.status = 'completed'
            call.end_time = datetime.now()
            if call.start_time:
                call.duration = call.end_time - call.start_time
            
            # Log recording chunks info
            total_chunks = call.recording_chunks.count()
            processed_chunks = call.recording_chunks.filter(processed=True).count()
            responses_played = call.recording_chunks.filter(response_played=True).count()
            
            print(f"Call {call_sid} completed. Total chunks: {total_chunks}, Processed: {processed_chunks}, Responses played: {responses_played}")
            
        elif call_status == 'failed':
            call.status = 'failed'
        elif call_status == 'busy':
            call.status = 'failed'
        elif call_status == 'no-answer':
            call.status = 'failed'
        elif call_status == 'canceled':
            call.status = 'failed'
            
        call.save()
        
        # Clean up active call tracking
        service = TwilioVoiceService()
        if call_sid in service.active_calls:
            active_call_data = service.active_calls[call_sid]
            print(f"Cleaning up call {call_sid}. Total audio chunks tracked: {len(active_call_data.get('audio_chunks', []))}")
            del service.active_calls[call_sid]
        
    except Call.DoesNotExist:
        print(f"Call {call_sid} not found in database")
        pass
    except Exception as e:
        print(f"Error updating call status: {e}")
    
    return HttpResponse('OK')


# Utility functions for audio processing
async def process_audio_async(audio_data, call_id):
    """
    Asynchronously process audio data
    This function can be called to process audio without blocking the call
    """
    def process_in_thread():
        try:
            # Your AI processing logic here
            # This could call your AI service to analyze the audio
            agent_service = AIAgentService()
            
            # Simulate processing time
            import time
            time.sleep(2)  # Remove this in production
            
            # Process the audio (implement your actual AI logic here)
            result = {
                'call_id': call_id,
                'processed': True,
                'response_audio_url': None,  # URL to generated response audio
                'analysis': 'Audio processed successfully'
            }
            
            return result
            
        except Exception as e:
            print(f"Error in async processing: {e}")
            return None
    
    # Run in thread to avoid blocking
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    result = await loop.run_in_executor(None, process_in_thread)
    return result

# API endpoint for manual audio processing (useful for testing)
@csrf_exempt
@require_http_methods(["POST"])
def process_audio_endpoint(request):
    """
    API endpoint to manually process audio files
    Useful for testing and batch processing
    """
    try:
        data = json.loads(request.body)
        audio_url = data.get('audio_url')
        call_id = data.get('call_id')
        
        if not audio_url or not call_id:
            return JsonResponse({'error': 'audio_url and call_id are required'}, status=400)
        
        # Get audio data for processing
        audio_data = get_recording_for_processing(audio_url, prefer_local=False)
        
        if audio_data:
            # Process audio with Sarvam AI
            try:
                service = TwilioVoiceService()
                # The audio processing is now handled in wait_for_ai_response method
                # which uses Sarvam AI functions
                response_url = service.wait_for_ai_response(call_id, audio_url)
                
                if response_url:
                    return JsonResponse({
                        'success': True,
                        'response_audio_url': response_url,
                        'message': 'Audio processed successfully with Sarvam AI'
                    })
                else:
                    return JsonResponse({'error': 'Failed to process audio with Sarvam AI'}, status=500)
            except Exception as e:
                return JsonResponse({'error': f'Processing error: {str(e)}'}, status=500)
        else:
            return JsonResponse({'error': 'Failed to download audio'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Testing endpoint for Twilio integration
@csrf_exempt
@require_http_methods(["GET", "POST"])
def test_twilio_call(request):
    """
    Test endpoint to initiate a call (for testing purposes)
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            to_number = data.get('to_number')
            
            if not to_number:
                return JsonResponse({'error': 'to_number is required'}, status=400)
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            call = client.calls.create(
                to=to_number,
                from_=settings.TWILIO_PHONE_NUMBER,
                url=request.build_absolute_uri('/twilio/voice/'),
                method='POST'
            )
            
            return JsonResponse({
                'success': True,
                'call_sid': call.sid,
                'status': call.status
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request returns test form
    return JsonResponse({
        'message': 'Send POST request with to_number to initiate test call',
        'example': {'to_number': '+1234567890'}
    })


# API endpoint for managing local recordings
@csrf_exempt
@require_http_methods(["GET", "POST"])
def recording_management_endpoint(request):
    """
    API endpoint for managing local recordings
    GET: Get recording statistics and list recordings
    POST: Perform actions like archive, verify integrity, etc.
    """
    if request.method == 'GET':
        try:
            # Get query parameters
            action = request.GET.get('action', 'stats')
            call_id = request.GET.get('call_id')
            
            if action == 'stats':
                # Get storage statistics
                stats = local_storage.get_storage_stats()
                return JsonResponse({
                    'success': True,
                    'storage_stats': stats
                })
            
            elif action == 'list' and call_id:
                # Get recording info for specific call
                try:
                    call = Call.objects.get(id=call_id)
                    recording_info = {
                        'call_id': str(call.id),
                        'twilio_url': call.audio_file_url,
                        'local_path': call.local_recording_path,
                        'local_url': call.local_recording_url,
                        'has_local_copy': bool(call.local_recording_path and 
                                             os.path.exists(call.local_recording_path)),
                        'call_duration': str(call.duration) if call.duration else None,
                        'call_date': call.start_time.isoformat() if call.start_time else None
                    }
                    
                    # Check file integrity if local file exists
                    if recording_info['has_local_copy']:
                        recording_info['integrity_verified'] = local_storage.verify_recording_integrity(
                            call.local_recording_path
                        )
                    
                    return JsonResponse({
                        'success': True,
                        'recording_info': recording_info
                    })
                    
                except Call.DoesNotExist:
                    return JsonResponse({'error': 'Call not found'}, status=404)
            
            elif action == 'list':
                # List recent recordings
                limit = int(request.GET.get('limit', 20))
                calls_with_recordings = Call.objects.filter(
                    audio_file_url__isnull=False
                ).order_by('-start_time')[:limit]
                
                recordings = []
                for call in calls_with_recordings:
                    recordings.append({
                        'call_id': str(call.id),
                        'phone_number': call.phone_number,
                        'start_time': call.start_time.isoformat() if call.start_time else None,
                        'duration': str(call.duration) if call.duration else None,
                        'has_twilio_recording': bool(call.audio_file_url),
                        'has_local_recording': bool(call.local_recording_path and 
                                                  os.path.exists(call.local_recording_path)),
                        'local_url': call.local_recording_url,
                        'status': call.status
                    })
                
                return JsonResponse({
                    'success': True,
                    'recordings': recordings,
                    'count': len(recordings)
                })
            
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'archive_old':
                # Archive old recordings
                days_old = data.get('days_old', 30)
                archived_count = local_storage.archive_old_recordings(days_old)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Archived {archived_count} recordings older than {days_old} days'
                })
            
            elif action == 'store_existing':
                # Store an existing Twilio recording locally
                call_id = data.get('call_id')
                
                if not call_id:
                    return JsonResponse({'error': 'call_id is required'}, status=400)
                
                try:
                    call = Call.objects.get(id=call_id)
                    
                    if not call.audio_file_url:
                        return JsonResponse({'error': 'No Twilio recording URL found'}, status=400)
                    
                    if call.local_recording_path and os.path.exists(call.local_recording_path):
                        return JsonResponse({'error': 'Local recording already exists'}, status=400)
                    
                    # Store recording locally
                    local_metadata = local_storage.store_recording_locally(
                        call.audio_file_url, call_id, call.twilio_call_sid
                    )
                    
                    if local_metadata:
                        call.local_recording_path = local_metadata['local_path']
                        call.local_recording_url = local_metadata['local_url']
                        call.save()
                        
                        return JsonResponse({
                            'success': True,
                            'message': 'Recording stored locally',
                            'local_url': local_metadata['local_url']
                        })
                    else:
                        return JsonResponse({'error': 'Failed to store recording locally'}, status=500)
                        
                except Call.DoesNotExist:
                    return JsonResponse({'error': 'Call not found'}, status=404)
            
            elif action == 'verify_integrity':
                # Verify integrity of local recordings
                call_id = data.get('call_id')
                
                if call_id:
                    # Verify specific recording
                    try:
                        call = Call.objects.get(id=call_id)
                        
                        if not call.local_recording_path:
                            return JsonResponse({'error': 'No local recording found'}, status=404)
                        
                        is_valid = local_storage.verify_recording_integrity(call.local_recording_path)
                        
                        return JsonResponse({
                            'success': True,
                            'call_id': str(call.id),
                            'integrity_verified': is_valid
                        })
                        
                    except Call.DoesNotExist:
                        return JsonResponse({'error': 'Call not found'}, status=404)
                else:
                    # Verify all recordings (this could be slow for many files)
                    return JsonResponse({'error': 'Bulk verification not implemented yet'}, status=501)
            
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_recording_for_processing(recording_url_or_call_id, prefer_local=True):
    """
    Get recording audio data for processing, preferring local storage
    Can accept either a Twilio recording URL or a call ID
    """
    try:
        audio_data = None
        source = None
        
        # If it's a call ID, try to get local recording first
        if isinstance(recording_url_or_call_id, str) and not recording_url_or_call_id.startswith('http'):
            try:
                call = Call.objects.get(id=recording_url_or_call_id)
                
                # Try local recording first if preferred
                if prefer_local and call.local_recording_path and os.path.exists(call.local_recording_path):
                    with open(call.local_recording_path, 'rb') as f:
                        audio_content = f.read()
                    
                    # Read metadata
                    metadata_path = call.local_recording_path + '.meta.json'
                    metadata = {}
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    
                    audio_data = {
                        'audio_data': audio_content,
                        'audio_url': call.local_recording_url,
                        'local_path': call.local_recording_path,
                        'content_type': metadata.get('content_type', 'audio/wav'),
                        'size': len(audio_content),
                        'source': 'local'
                    }
                    source = 'local'
                
                # Fallback to Twilio if no local recording or prefer_local is False
                if not audio_data and call.audio_file_url:
                    service = TwilioVoiceService()
                    audio_data = service.get_audio_for_processing(call.audio_file_url)
                    if audio_data:
                        audio_data['source'] = 'twilio'
                        source = 'twilio'
                
            except Call.DoesNotExist:
                pass
        
        # If it's a URL, download from Twilio
        elif isinstance(recording_url_or_call_id, str) and recording_url_or_call_id.startswith('http'):
            service = TwilioVoiceService()
            audio_data = service.get_audio_for_processing(recording_url_or_call_id)
            if audio_data:
                audio_data['source'] = 'twilio'
                source = 'twilio'
        
        if audio_data:
            print(f"Retrieved audio from {source} source")
        
        return audio_data
        
    except Exception as e:
        print(f"Error getting recording for processing: {e}")
        return None


# Function to extract user voice from call (as requested)
def extract_user_voice_from_call(call_id_or_recording_url, prefer_local=True):
    """
    Function to extract voice/audio from call recording
    This is the main function that gives you the user's voice as output
    
    Args:
        call_id_or_recording_url: Either a call ID or Twilio recording URL
        prefer_local: Whether to prefer local storage over Twilio
        
    Returns:
        dict: Audio data including file path, content, and metadata
    """
    return get_recording_for_processing(call_id_or_recording_url, prefer_local)


# Function to play audio file to caller (as requested)
def play_audio_file_to_caller(call_sid, audio_file_path_or_url):
    """
    Function to play an audio file to the user during an active call
    Supports both local file paths and URLs
    
    Args:
        call_sid (str): Twilio call SID
        audio_file_path_or_url (str): Path to local audio file or URL
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        service = TwilioVoiceService()
        
        # If it's a local file path, we need to convert it to a publicly accessible URL
        if not audio_file_path_or_url.startswith('http'):
            # For local files, you'd need to serve them through Django's media handling
            # or upload to a CDN/cloud storage for Twilio to access
            
            # Convert local path to media URL if it's in the media directory
            if audio_file_path_or_url.startswith(settings.MEDIA_ROOT):
                relative_path = os.path.relpath(audio_file_path_or_url, settings.MEDIA_ROOT)
                audio_url = f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                
                # You'd need to ensure your server can serve this URL publicly
                # For production, consider uploading to S3 or similar
                return service.play_audio_to_caller(call_sid, audio_url)
            else:
                print("Error: Local file path must be in media directory for serving")
                return False
        else:
            # It's already a URL
            return service.play_audio_to_caller(call_sid, audio_file_path_or_url)
            
    except Exception as e:
        print(f"Error playing audio to caller: {e}")
        return False

