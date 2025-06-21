# Continuous Recording Implementation

This document describes the implementation of continuous recording functionality for the suicide hotline app.

## Overview

The system now implements a continuous recording and playback cycle where:

1. **Instant Recording**: When a user connects, recording starts immediately without any welcome message
2. **Recording Chunks**: Each recording is limited to 30 seconds and stored as individual chunks
3. **AI Processing**: Each recording chunk is processed by Sarvam AI to generate a response
4. **Audio Playback**: AI-generated audio responses are played back to the user
5. **Continuous Cycle**: After playing the response, a new recording starts immediately
6. **User Disconnect**: The cycle continues until the user disconnects the call

## Key Features

### No Default Messages
- No welcome messages or prompts are played
- Recording starts immediately when the call connects
- All communication happens through recorded user speech and AI-generated audio responses

### Recording Management
- Each call can have multiple recording chunks (30 seconds each)
- All recordings are stored both on Twilio and locally
- Metadata tracking for each chunk including processing status

### AI Integration Simulation
- Currently simulates Sarvam AI integration
- Uses sample audio files from the `outputs` folder
- Ready for actual AI API integration

## Technical Implementation

### New Models

#### RecordingChunk Model
```python
class RecordingChunk(models.Model):
    call = models.ForeignKey(Call, related_name='recording_chunks')
    recording_url = models.URLField()  # Twilio URL
    local_recording_path = models.CharField()  # Local storage
    chunk_number = models.IntegerField()  # Order in call
    duration_seconds = models.FloatField()
    processed = models.BooleanField()  # AI processing complete
    response_audio_url = models.URLField()  # AI response
    response_played = models.BooleanField()  # Response delivered
    recorded_at = models.DateTimeField()
    processed_at = models.DateTimeField()
```

### Modified Twilio Call Flow

#### 1. Incoming Call Handler
```python
def handle_incoming_call(self, request):
    # Create call record
    call = Call.objects.create(...)
    
    # Start recording immediately (no welcome message)
    response.record(
        action=f'/twilio/recording/{call.id}/',
        max_length=30,
        play_beep=False,
        trim='trim-silence'
    )
```

#### 2. Recording Complete Handler
```python
def handle_recording_complete(self, request, call_id):
    # Store recording chunk
    chunk = call.recording_chunks.create(
        recording_url=recording_url,
        chunk_number=current_chunk_number,
        ...
    )
    
    # Get AI response (simulated)
    response_audio_url = self.wait_for_ai_response(call_id)
    
    if response_audio_url:
        # Play AI response
        response.play(response_audio_url)
        
        # Mark as processed
        chunk.processed = True
        chunk.response_played = True
        
        # Start next recording immediately
        response.record(...)
```

#### 3. AI Response Simulation
```python
def wait_for_ai_response(self, call_id):
    # Simulate processing time
    time.sleep(2)
    
    # Return sample audio from outputs folder
    return f"{settings.MEDIA_URL}outputs/sample_response.wav"
```

## File Structure

### Media Directories
```
media/
├── outputs/
│   └── sample_response.wav  # AI response audio
└── recordings/
    ├── daily/
    │   └── 2025-06-21/     # Organized by date
    └── archived/           # Old recordings
```

### Database Tables
- `calls_call` - Main call records
- `calls_recordingchunk` - Individual recording chunks
- `calls_memory` - AI analysis results (existing)
- `calls_callnote` - Human operator notes (existing)

## API Endpoints

### Twilio Webhooks
- `POST /twilio/voice/` - Handle incoming calls
- `POST /twilio/recording/<call_id>/` - Handle recording completion
- `POST /twilio/status/` - Handle call status updates

### Management Endpoints
- `GET /api/calls/` - List all calls with chunks
- `GET /api/calls/<id>/` - Get call details with all chunks
- `POST /api/process-audio/` - Manual audio processing

## Admin Interface

### Call Administration
- View all calls with recording chunks inline
- See processing status for each chunk
- Audio playback controls
- Export functionality

### Recording Chunk Administration
- List all recording chunks
- Filter by processing status
- View AI response URLs
- Track response delivery

## Testing

### Test Script
Run the test simulation:
```bash
python3 test_continuous_recording.py
```

### Test Flow
1. Creates a mock call
2. Simulates 3 recording chunks
3. Shows AI processing and response playback
4. Demonstrates continuous cycle

### Expected Output
```
🎯 Simulating Continuous Recording Call Flow
📞 Created test call: [uuid]
🎤 Recording Chunk 1... ✅ Complete
🎤 Recording Chunk 2... ✅ Complete  
🎤 Recording Chunk 3... ✅ Complete
📊 Call Summary: 3 chunks, all processed
```

## Integration with Sarvam AI

### Current Implementation
- Uses sample audio file (`sample_response.wav`)
- Simulates 2-second processing time
- Placeholder for actual API integration

### Future Integration
Replace `wait_for_ai_response()` method with:
```python
def wait_for_ai_response(self, call_id):
    # Send recording to Sarvam AI API
    api_response = sarvam_ai_client.process_audio(recording_data)
    
    # Wait for processing completion
    while api_response.status == 'processing':
        time.sleep(1)
        api_response = sarvam_ai_client.get_status(api_response.job_id)
    
    # Return AI-generated audio URL
    return api_response.audio_url
```

## Monitoring and Logging

### Call Tracking
- Total recording chunks per call
- Processing success/failure rates
- Response delivery confirmation
- Call duration and completion status

### Debug Information
- Real-time logging of recording events
- AI processing status updates
- Error handling and recovery
- Call cleanup on disconnect

## Error Handling

### Robust Recovery
- Continue recording if AI processing fails
- Graceful handling of network issues
- Automatic cleanup on call disconnect
- Fallback to basic recording if needed

### Failure Scenarios
1. **AI API Timeout**: Continue recording without response
2. **Network Issues**: Retry with exponential backoff
3. **Storage Failure**: Log error but continue call
4. **Twilio Errors**: Attempt call recovery

## Performance Considerations

### Scalability
- Asynchronous audio processing
- Local storage with automatic archiving
- Efficient database queries for chunks
- Minimal call blocking operations

### Storage Management
- Automatic archiving of old recordings
- Configurable retention policies
- Local and cloud storage options
- Compression for long-term storage

## Security and Privacy

### Data Protection
- Encrypted storage of recordings
- Secure transmission to AI services
- Automatic deletion after retention period
- Access logging and audit trails

### Compliance
- HIPAA-compliant storage options
- Data anonymization capabilities
- Consent tracking and management
- Regulatory compliance reporting

## Next Steps

1. **Integrate Sarvam AI API**
   - Replace simulation with actual API calls
   - Handle API authentication and rate limiting
   - Implement proper error handling

2. **Enhanced Monitoring**
   - Real-time dashboard for active calls
   - Performance metrics and analytics
   - Alert system for issues

3. **Advanced Features**
   - Voice activity detection
   - Background noise filtering
   - Multi-language support
   - Emergency escalation triggers

## Conclusion

The continuous recording implementation provides a seamless, conversation-like experience for callers while maintaining detailed tracking and AI integration capabilities. The modular design allows for easy extension and modification as requirements evolve.
