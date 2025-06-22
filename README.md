# Suicide Prevention Hotline Backend

A comprehensive Django-based backend system for managing a suicide prevention hotline with advanced AI agent integration, real-time call management, and intelligent memory storage for sophisticated risk assessment and emotional analysis.

## System Architecture

![image1](methodology.jpg)

## 🌟 Key Features

### 🎯 Core Functionality
- **Advanced Call Management**: Complete Twilio integration with real-time call handling and status tracking
- **AI-Powered Memory System**: Sophisticated AI agent memory storage with risk assessment and emotional analysis
- **Comprehensive Admin Dashboard**: Full-featured admin interface with statistics, risk visualization, and call management
- **RESTful API**: Complete API ecosystem for frontend integration
- **Real-time Analytics**: Live dashboard with statistics, trends, and historical data

### 🔧 Advanced Features
- **Continuous Recording System**: Intelligent 30-second dynamic chunk recording with automatic AI processing
- **Multi-Language Support**: Built-in support for multilingual conversations
- **Audio Processing Pipeline**: Automated audio download, processing, and response generation
- **Local Storage Management**: Sophisticated local recording storage with integrity verification
- **Memory Integration**: Advanced conversation memory using mem0 and vector databases
- **Fallback Mechanisms**: Robust error handling with fallback responses

## 🏗️ Project Architecture

### 📁 Directory Structure
```
suicide_hotline/
├── calls/                          # Main Django app
│   ├── models.py                   # Core data models
│   ├── admin.py                    # Admin interface configuration
│   ├── views.py                    # API views and webhooks
│   ├── ai_service.py               # AI integration and Twilio service
│   ├── sarv.py                     # Sarvam AI integration
│   ├── memory_integration.py       # Memory system integration
│   ├── serializers.py              # DRF serializers
│   ├── urls.py                     # URL routing
│   ├── middleware.py               # Custom middleware
│   ├── migrations/                 # Database migrations
│   └── management/
│       └── commands/
│           └── create_sample_data.py  # Sample data generator
├── hotline_backend/                # Django project configuration
│   ├── settings.py                 # Project settings
│   ├── urls.py                     # Main URL configuration
│   ├── wsgi.py                     # WSGI configuration
│   └── asgi.py                     # ASGI configuration
├── templates/                      # HTML templates
│   ├── dashboard.html              # Main dashboard interface
│   ├── test.html                   # Testing interface
│   └── debug.html                  # Debug interface
├── media/                          # Media files
│   ├── outputs/                    # AI response audio files
│   ├── recordings/                 # Call recordings storage
│   └── processing/                 # Temporary processing files
├── audio_files/                    # Audio processing directories
│   ├── input/                      # Input audio files
│   └── output/                     # Output audio files
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── TWILIO_INTEGRATION.md          # Twilio integration documentation
├── CONTINUOUS_RECORDING_IMPLEMENTATION.md  # Recording system docs
├── LICENSE                         # License file
└── manage.py                       # Django management script
```

## 🗄️ Database Models

### 📞 Call Model
**Core call information and status tracking**
```python
class Call(models.Model):
    id = UUIDField(primary_key=True)           # Unique call identifier
    phone_number = CharField(max_length=20)     # Caller's phone number
    twilio_call_sid = CharField(unique=True)    # Twilio Call SID
    status = CharField(choices=STATUS_CHOICES)  # Call status
    start_time = DateTimeField()               # Call start timestamp
    end_time = DateTimeField(nullable=True)    # Call end timestamp
    duration = DurationField(nullable=True)    # Call duration
    audio_file_url = URLField(nullable=True)   # Twilio recording URL
    local_recording_path = CharField()         # Local storage path
    local_recording_url = CharField()          # Local access URL
    transcription = TextField(nullable=True)   # Call transcription
    conversation_state = JSONField()           # AI conversation history
    caller_city = CharField(nullable=True)     # Caller location
    caller_state = CharField(nullable=True)    # Caller state/region
    caller_country = CharField(nullable=True)  # Caller country
```

**Status Options**: `incoming`, `in_progress`, `completed`, `disconnected`, `failed`

### 🧠 Memory Model
**AI agent memory and assessment storage**
```python
class Memory(models.Model):
    id = UUIDField(primary_key=True)
    call = ForeignKey(Call)                    # Associated call
    
    # Risk Assessment
    risk_level = CharField(choices=RISK_CHOICES)      # Risk level assessment
    risk_factors = JSONField(default=list)           # Identified risk factors
    protective_factors = JSONField(default=list)     # Protective factors
    
    # Emotional Analysis
    primary_emotion = CharField(choices=EMOTION_CHOICES)  # Primary emotion
    emotion_intensity = IntegerField(1-10)                # Emotion intensity
    emotions_detected = JSONField(default=list)          # Multiple emotions
    
    # Conversation Analysis
    conversation_summary = TextField()                    # AI-generated summary
    key_topics = JSONField(default=list)                 # Discussed topics
    intervention_techniques_used = JSONField()           # AI techniques used
    chat_messages = JSONField(default=list)              # Full conversation
    
    # Clinical Assessment
    mental_health_concerns = TextField()                  # Clinical concerns
    immediate_safety_plan = TextField()                  # Safety planning
    follow_up_needed = BooleanField()                    # Follow-up required
    follow_up_notes = TextField()                        # Follow-up details
    
    # Resources and Referrals
    resources_provided = JSONField(default=list)         # Shared resources
    referrals_made = JSONField(default=list)             # External referrals
    
    # AI Metadata
    confidence_score = FloatField(0.0-1.0)               # AI confidence
```

**Risk Levels**: `low`, `moderate`, `high`, `critical`, `unknown`
**Emotions**: `sad`, `angry`, `anxious`, `depressed`, `hopeless`, `confused`, `calm`, `neutral`, `grateful`, `other`

### 🎵 RecordingChunk Model
**Individual recording segments within calls**
```python
class RecordingChunk(models.Model):
    id = UUIDField(primary_key=True)
    call = ForeignKey(Call)                    # Parent call
    recording_url = URLField()                 # Twilio recording URL
    local_recording_path = CharField()         # Local storage path
    local_recording_url = CharField()          # Local access URL
    chunk_number = IntegerField()              # Sequence number
    duration_seconds = FloatField()            # Chunk duration
    processed = BooleanField()                 # AI processing status
    response_audio_url = URLField()            # AI response URL
    response_played = BooleanField()           # Response delivery status
    recorded_at = DateTimeField()              # Recording timestamp
    processed_at = DateTimeField()             # Processing timestamp
```


## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- Django 5.2.3
- PostgreSQL (recommended for production)
- Twilio Account
- Sarvam AI API Key (optional)

### 1. Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd suicide_hotline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Create `.env` file in project root:
```env
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database Configuration (SQLite default, PostgreSQL recommended)
DATABASE_URL=postgresql://username:password@localhost:5432/hotline_db

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# AI Configuration (Optional)
SARVAM_API_KEY=your_sarvam_api_key

# Security Settings
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# CORS Settings
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Database Setup
```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 4. Start Development Server
```bash
python manage.py runserver
```

Access the application:
- **Main Dashboard**: http://127.0.0.1:8000/
- **Admin Interface**: http://127.0.0.1:8000/admin/
- **API Root**: http://127.0.0.1:8000/api/

## 🎛️ Admin Dashboard

### 🔑 Access Credentials
- **Username**: `admin`
- **Password**: `admin123`

### 📊 Dashboard Features

#### Call Management Interface
- **Call List View**: Comprehensive call listing with filtering and search
- **Status Indicators**: Real-time call status with color coding
- **Risk Level Display**: Visual risk assessment indicators
- **Duration Tracking**: Call duration with formatted display
- **Location Information**: Caller geographic data
- **Audio Playback**: Integrated audio player for call recordings
- **Inline Editing**: Direct editing of call properties

#### Memory Management System
- **Risk Assessment Dashboard**: Visual risk level distribution
- **Emotional Analysis**: Emotion tracking and intensity visualization
- **Conversation Summaries**: AI-generated conversation analysis
- **Intervention Tracking**: Techniques used by AI agents
- **Follow-up Management**: Cases requiring human intervention
- **Resource Tracking**: Resources provided to callers

#### Recording Management
- **Chunk Visualization**: Individual recording segments
- **Processing Status**: AI processing pipeline status
- **Response Tracking**: AI response delivery confirmation
- **Storage Management**: Local and remote storage status
- **Integrity Verification**: Recording file integrity checks

#### Analytics and Reporting
- **Call Volume Trends**: Historical call data visualization
- **Risk Distribution**: Risk level statistics and trends
- **Response Time Analysis**: AI processing performance metrics
- **Geographic Distribution**: Caller location analytics
- **Operator Performance**: Human intervention tracking

## 🔌 API Endpoints

### 🌐 RESTful API Structure

#### Call Management
```http
GET    /api/calls/                    # List all calls
POST   /api/calls/                    # Create new call
GET    /api/calls/{id}/               # Get specific call
PUT    /api/calls/{id}/               # Update call
DELETE /api/calls/{id}/               # Delete call
GET    /api/calls/{id}/memories/      # Get call memories
POST   /api/calls/{id}/add_note/      # Add operator note
```

#### Memory Management
```http
GET    /api/memories/                 # List all memories
POST   /api/memories/                 # Create new memory
GET    /api/memories/{id}/            # Get specific memory
PUT    /api/memories/{id}/            # Update memory
DELETE /api/memories/{id}/            # Delete memory
GET    /api/memories/risk_summary/    # Risk level summary
```

#### Dashboard Analytics
```http
GET    /api/dashboard/stats/          # Dashboard statistics
GET    /api/dashboard/calls/          # Public call data
```

#### Twilio Webhooks
```http
POST   /twilio/voice/                 # Incoming call handler
POST   /twilio/recording/{call_id}/   # Recording completion
POST   /twilio/continue/{call_id}/    # Continue conversation
POST   /twilio/user-choice/{call_id}/ # User choice handler
POST   /twilio/status/               # Call status updates
```

#### Audio Processing
```http
POST   /api/process-audio/           # Manual audio processing
POST   /api/test-call/               # Test call initiation
GET    /api/recordings/              # Recording management
POST   /api/recordings/              # Recording operations
```

### 📝 API Response Formats

#### Call Response Example
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+1234567890",
  "status": "completed",
  "start_time": "2025-06-22T10:30:00Z",
  "duration": "00:05:30",
  "latest_risk_level": {
    "level": "moderate",
    "display": "Moderate Risk",
    "color": "yellow"
  },
  "memories": [...],
  "recording_chunks": [...],
  "total_chunks": 3
}
```

#### Memory Response Example
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "call": "550e8400-e29b-41d4-a716-446655440000",
  "risk_level": "moderate",
  "risk_factors": ["social isolation", "recent loss"],
  "protective_factors": ["family support"],
  "primary_emotion": "sad",
  "emotion_intensity": 7,
  "conversation_summary": "Caller expressed feelings of sadness...",
  "intervention_techniques_used": ["active listening", "validation"],
  "follow_up_needed": true,
  "confidence_score": 0.85
}
```

## 📞 Twilio Integration

### 🔧 Webhook Configuration

Configure these webhooks in your Twilio Console:

1. **Voice URL**: `https://yourdomain.com/twilio/voice/`
2. **Status Callback URL**: `https://yourdomain.com/twilio/status/`
3. **Recording Status Callback**: `https://yourdomain.com/twilio/recording/{call_id}/`

### 📋 Call Flow Process

#### 1. Incoming Call Handler
```python
def handle_incoming_call(request):
    # Extract caller information
    caller_number = request.POST.get('From')
    call_sid = request.POST.get('CallSid')
    
    # Create call record
    call = Call.objects.create(
        phone_number=caller_number,
        twilio_call_sid=call_sid,
        status='in_progress',
        caller_city=request.POST.get('FromCity'),
        caller_state=request.POST.get('FromState'),
        caller_country=request.POST.get('FromCountry')
    )
    
    # Start immediate recording (no welcome message)
    response.record(
        action=f'/twilio/recording/{call.id}/',
        max_length=30,  # 30-second chunks
        timeout=3,      # 3 seconds silence timeout
        play_beep=True,
        trim='trim-silence'
    )
```

#### 2. Recording Processing
```python
def handle_recording_complete(request, call_id):
    # Store recording chunk
    recording_chunk = call.recording_chunks.create(
        recording_url=request.POST.get('RecordingUrl'),
        chunk_number=current_chunk_number,
        duration_seconds=float(request.POST.get('RecordingDuration'))
    )
    
    # Process with AI
    ai_response = process_with_sarvam_ai(recording_url, call_id)
    
    if ai_response.get('should_end'):
        # End conversation
        response.hangup()
    elif ai_response.get('url'):
        # Play AI response and continue recording
        response.play(ai_response['url'])
        response.record(...)  # Continue cycle
```

#### 3. Continuous Recording Cycle
- **30-second chunks**: Each recording limited to 30 seconds
- **Dynamic record stopping**: After 3 seconds of silence, end the recording and send to server
- **Immediate processing**: AI processes each chunk in real-time
- **Seamless playback**: AI responses played back immediately
- **Automatic continuation**: Recording resumes after each response
- **Smart termination**: AI determines when to end conversation

## 🤖 AI Integration

### 🧠 Sarvam AI Integration

#### Audio Processing Pipeline
```python
def process_single_audio_input(input_path, output_path, conversation):
    """
    Process audio input with Sarvam AI
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output audio file
        conversation: Conversation history list
    
    Returns:
        dict: Processing result with success status
    """
    try:
        # Speech-to-text conversion
        transcript = client.speech_to_text(input_path)
        
        # Add to conversation context
        conversation.append({
            "role": "user",
            "content": transcript
        })
        
        # Generate AI response
        response = client.chat_completion(
            messages=conversation,
            model="sarvam-m"
        )
        
        # Text-to-speech conversion
        audio_response = client.text_to_speech(
            text=response.content,
            voice="meera",
            language="en-IN"
        )
        
        # Save audio response
        save(audio_response, output_path)
        
        return {
            "success": True,
            "transcript": transcript,
            "response": response.content,
            "should_end": detect_conversation_end(response.content)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "should_end": False
        }
```

#### Memory Integration
```python
def update_conversation_memory(call_id, conversation):
    """Update conversation memory using mem0"""
    if memory:
        # Extract key information
        memory_data = {
            "user_id": f"call_{call_id}",
            "messages": conversation,
            "metadata": {
                "call_id": call_id,
                "timestamp": timezone.now().isoformat()
            }
        }
        
        # Store in memory system
        memory.add(
            messages=conversation,
            user_id=f"call_{call_id}",
            metadata=memory_data["metadata"]
        )
```

### 🎯 AI System Prompt
```python
system_prompt = """
You are a compassionate, patient, and multilingual suicide prevention hotline worker. 
Your role is to gently support people in emotional distress.

Your tone must always be calm, kind, and reassuring. Avoid sounding robotic or overly clinical. 
Use simple, friendly language.

Your goals in the conversation:
1. Greet the user warmly. Ask their name and where they are from.
2. Invite them to share. Ask how they're feeling and what's been on their mind lately.
3. Validate their emotions. Say things like "That sounds really tough" or "You're not alone in this."
4. Encourage small steps. Suggest talking to a friend, taking a short walk, or breathing exercises.
5. Offer consistent support. Avoid judgment or unsolicited advice.
6. Check how they're feeling now.
7. End softly if they're okay. If calm or grateful, you may say goodbye with <end conversation>.

Avoid:
- "Cheer up", "It's not a big deal", or "I understand exactly how you feel".

Example responses:
- "That must feel overwhelming. You're not alone."
- "Take your time. You don't have to share everything at once."
"""
```

## 💾 Storage Management

### 📁 Local Recording Storage

#### Storage Organization
```
media/
├── recordings/
│   ├── daily/
│   │   ├── 2025-06-21/           # Date-organized storage
│   │   ├── 2025-06-22/
│   │   └── ...
│   └── archived/                 # Archived recordings
├── outputs/
│   ├── sample_response.wav       # Fallback responses
│   └── response_*.wav            # AI-generated responses
└── processing/
    ├── input_*.wav               # Temporary input files
    └── response_*.wav            # Temporary processing files
```

#### Storage Management Features
```python
class LocalRecordingStorage:
    """Advanced local storage management"""
    
    def store_recording_locally(self, recording_url, call_id, call_sid):
        """Download and store recording locally"""
        
    def verify_recording_integrity(self, file_path):
        """Verify file integrity using checksums"""
        
    def archive_old_recordings(self, days_old=30):
        """Archive recordings older than specified days"""
        
    def get_storage_stats(self):
        """Get storage usage statistics"""
        
    def cleanup_temp_files(self):
        """Clean up temporary processing files"""
```

## 🔒 Security Features

### 🛡️ Authentication & Authorization
- **Admin Authentication**: Secure admin panel access
- **API Authentication**: Session and token-based authentication
- **Dashboard Access**: Public dashboard with restricted data
- **CORS Configuration**: Proper cross-origin resource sharing

### 🔐 Data Protection
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Django ORM protection
- **XSS Prevention**: Template auto-escaping
- **CSRF Protection**: Cross-site request forgery prevention

### 🌐 Production Security Checklist
```env
# Production Environment Variables
SECRET_KEY=secure-production-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database Security
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_SSL_REQUIRE=True

# HTTPS Configuration
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True

# Session Security
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 📊 Monitoring & Analytics

### 📈 Dashboard Statistics
```python
def dashboard_stats():
    """Generate comprehensive dashboard statistics"""
    return {
        'total_calls': Call.objects.count(),
        'calls_today': Call.objects.filter(start_time__date=today).count(),
        'calls_this_week': Call.objects.filter(start_time__gte=week_ago).count(),
        'high_risk_calls': Memory.objects.filter(
            risk_level__in=['high', 'critical'],
            follow_up_needed=True
        ).count(),
        'avg_call_duration': Call.objects.aggregate(
            avg_duration=Avg('duration')
        )['avg_duration'],
        'risk_distribution': Memory.objects.values('risk_level').annotate(
            count=Count('risk_level')
        ),
        'emotion_trends': Memory.objects.values('primary_emotion').annotate(
            count=Count('primary_emotion')
        )
    }
```

### 🎯 API Testing Examples
```bash
# Test call creation
curl -X POST http://localhost:8000/api/calls/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "status": "in_progress"
  }'

# Test Twilio webhook
curl -X POST http://localhost:8000/twilio/voice/ \
  -d "From=+1234567890&CallSid=test_call_sid"

# Test dashboard statistics
curl http://localhost:8000/api/dashboard/stats/
```

### 🏗️ Integration Testing
```python
# Test continuous recording flow
def test_continuous_recording():
    # Create test call
    call = Call.objects.create(
        phone_number="+1234567890",
        twilio_call_sid="test_sid"
    )
    
    # Simulate recording chunks
    for i in range(3):
        chunk = call.recording_chunks.create(
            recording_url=f"test_url_{i}",
            chunk_number=i+1
        )
        
        # Test AI processing
        result = process_with_sarvam_ai(test_audio_path, call.id)
        assert result['success'] == True
```

## 🚀 Development with Ngrok

### 🌐 Ngrok Setup for Webhook Testing

Ngrok allows you to expose your local Django development server to the internet, making it perfect for testing webhooks from services like Twilio without deploying to production.

#### Prerequisites
- Python 3.9+ installed
- Django project set up locally
- Ngrok account (free tier available)

#### Installation

1. **Install Ngrok**
   ```bash
   # Download from https://ngrok.com/download
   # Or use package managers:
   
   # macOS (Homebrew)
   brew install ngrok/ngrok/ngrok
   
   # Windows (Chocolatey)
   choco install ngrok
   
   # Linux (Snap)
   sudo snap install ngrok
   ```

2. **Authenticate Ngrok**
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```
   *Get your authtoken from [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)*

#### 🏃‍♂️ Running the Application

1. **Start Django Development Server**
   ```bash
   # In your project directory
   python manage.py runserver 8000
   ```

2. **Expose Local Server with Ngrok**
   ```bash
   # In a new terminal window
   ngrok http 8000
   ```

3. **Note the Public URL**
   ```
   ngrok by @inconshreveable
   
   Session Status                online
   Account                       your-email@example.com
   Version                       3.1.0
   Region                        United States (us)
   Forwarding                    https://abc123.ngrok.io -> http://localhost:8000
   ```

#### ⚙️ Django Configuration for Ngrok

Update your `settings.py` for ngrok development:

```python
# settings.py
import os

# Allow ngrok host
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '*.ngrok.io',  # Allow all ngrok subdomains
    '.ngrok-free.app',  # For free ngrok domains
]

# Webhook URLs for external services
NGROK_URL = os.environ.get('NGROK_URL', 'https://your-ngrok-url.ngrok.io')

# Twilio webhook configuration
TWILIO_WEBHOOK_URL = f"{NGROK_URL}/api/webhooks/twilio/"

# CSRF settings for webhooks
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok.io',
    'https://*.ngrok-free.app',
]
```

#### 🔗 Webhook Configuration

**For Twilio Webhooks:**
```bash
# Set your ngrok URL as the webhook endpoint
# Voice webhook: https://your-ngrok-url.ngrok.io/api/webhooks/twilio/voice/
# SMS webhook: https://your-ngrok-url.ngrok.io/api/webhooks/twilio/sms/
```

#### 📝 Environment Variables

Create a `.env` file for local development:

```bash
# .env
DEBUG=True
SECRET_KEY=your-local-secret-key
DATABASE_URL=sqlite:///db.sqlite3
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
NGROK_URL=https://your-ngrok-url.ngrok.io
```

## 📋 Maintenance

### 🧹 Regular Maintenance Tasks
```bash
# Database maintenance
python manage.py clearsessions          # Clear expired sessions
python manage.py cleanup_temp_files     # Clean temporary files
python manage.py archive_old_recordings # Archive old recordings

# Performance optimization
python manage.py collectstatic --noinput  # Collect static files
python manage.py compress                  # Compress static files

# Health checks
python manage.py check --deploy          # Deployment checks
python manage.py system_check            # System health check
```

### 📊 Performance Monitoring
- **Database query optimization**
- **Memory usage tracking**
- **API response time monitoring**
- **Audio processing performance**
- **Storage usage analytics**

### 🔄 Development Workflow
```bash
# Set up development environment
git clone <repository>
cd suicide_hotline
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create feature branch
git checkout -b feature/new-feature

# Make changes and test
python manage.py test
python manage.py runserver

# Submit pull request
git push origin feature/new-feature
```

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🆘 Support

### 📞 contact details
- Adya N A - adyaneechadi@gmail.com
- Aryan Kashyap - aryankashyapnaveen@gmail.com
- Deepak C Nayak - deepakachu5114@gmail.com
- Ragha Sai - raghasaiblore@gmail.com

### 💬 Technical Support
- **Documentation**: Comprehensive API and integration docs
- **Issues**: GitHub issue tracker for bug reports
- **Discussions**: Community discussions for questions
- **Email**: Contact development team for urgent issues

---

**Note**: This system is designed to support mental health professionals and should not replace professional crisis intervention training. Always ensure proper human oversight for high-risk cases.
