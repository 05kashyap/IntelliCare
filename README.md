# Suicide Prevention Hotline Backend

A Django-based backend system for managing a suicide prevention hotline with AI agent integration, call management, and memory storage for risk assessment and emotional analysis.

---

## System Architecture

![image1](image1)

The system integrates the following major components:
- **Twilio API** for telephony, call recording, and playback.
- **SARVAM API** for language detection, audio transcription, and text-to-speech (TTS).
- **mem0** for memory retrieval, storage, and update.
- **SARVAM-M** for conversational AI, risk and emotion assessment, and safety guard rails.
- Real-time danger assessment and escalation to alert authorities if needed.

The call flow:
1. Caller audio is recorded via Twilio and passed to SARVAM API for transcription and language detection.
2. Guard rails are checked for safety and compliance.
3. SARVAM-M (AI agent) processes conversation, retrieves and updates memory, assesses risk, and generates a response.
4. If risk exceeds a threshold, authorities can be automatically alerted.
5. AI-generated response is converted to audio by the SARVAM API and played back to the caller.

---

## Features

- **Call Management**: Track incoming calls with Twilio integration.
- **Memory System**: Store AI agent memories including risk levels, emotions, and conversation data.
- **Admin Dashboard**: Comprehensive admin interface for managing calls and memories.
- **Risk Assessment**: Track risk levels (low, moderate, high, critical) with color-coded display.
- **Emergency Contacts**: Manage emergency contacts for high-risk cases.
- **Call Notes**: Add notes to calls by human operators/supervisors.
- **API Endpoints**: RESTful API for integration with frontend applications.
- **Dashboard Statistics**: Get real-time statistics and analytics.
- **Guard Rails and Escalation**: Automated guard rails check conversations for safety, with escalation to authorities if danger is above threshold.

---

## Project Structure

```
suicide_hotline/
├── calls/                          # Main app for call and memory management
│   ├── models.py                   # Database models (Call, Memory, CallNote, EmergencyContact)
│   ├── admin.py                    # Admin interface configuration
│   ├── views.py                    # API views and Twilio webhooks
│   ├── serializers.py              # Django REST Framework serializers
│   ├── urls.py                     # URL routing
│   └── management/commands/        # Management commands
│       └── create_sample_data.py   # Create sample data for testing
├── hotline_backend/                # Django project settings
│   ├── settings.py                 # Main settings
│   └── urls.py                     # Main URL configuration
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables
└── manage.py                       # Django management script
```

---

## Installation & Setup

### 1. Clone and Setup Environment

```bash
cd /path/to/your/project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Update the `.env` file with your configuration:

```env
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True

# Twilio Configuration (get these from your Twilio Console)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Security Settings
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# CORS Settings (add your frontend domains)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Sample Data (Optional)

```bash
python manage.py create_sample_data --calls 20
```

This creates:
- An admin user (username: `admin`, password: `admin123`)
- 20 sample calls with memories, notes, and emergency contacts
- Various risk levels and emotional states for testing

### 5. Run the Server

```bash
python manage.py runserver
```

---

## Admin Dashboard

Access the admin dashboard at `http://127.0.0.1:8000/admin/`

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`

### Admin Features

1. **Calls Management**
   - View all calls with status, duration, and risk levels
   - Filter by status, risk level, location
   - Search by phone number or transcription
   - Color-coded risk level indicators
   - Audio player for call recordings
   - Inline editing of memories and notes

2. **Memories Management**
   - View AI agent memories with risk assessments
   - Filter by risk level, emotion, follow-up needed
   - Detailed view of conversation summaries and intervention techniques
   - Clinical assessment data

3. **Call Notes**
   - Add notes to calls
   - Mark urgent notes
   - Track note authors

4. **Emergency Contacts**
   - Manage emergency contacts for high-risk cases
   - Track contact status and times

---

## API Endpoints

### Call Management
- `GET /api/calls/` - List all calls
- `GET /api/calls/{id}/` - Get specific call
- `GET /api/calls/{id}/memories/` - Get memories for a call
- `POST /api/calls/{id}/add_note/` - Add note to a call

### Memory Management
- `GET /api/memories/` - List all memories
- `GET /api/memories/risk_summary/` - Get risk level summary
- `POST /api/memories/` - Create new memory

### Dashboard
- `GET /api/dashboard/stats/` - Get dashboard statistics

### Twilio Webhooks
- `POST /twilio/voice/` - Handle incoming calls
- `POST /twilio/recording/{call_id}/` - Handle recording completion
- `POST /twilio/status/` - Handle call status updates

---

## Database Models

### Call Model
- Stores basic call information (phone number, duration, status)
- Twilio integration data (Call SID, recordings)
- Location information (city, state, country)
- Call transcription

### Memory Model
- AI agent memories and assessments
- Risk level tracking (low, moderate, high, critical)
- Emotional analysis (primary emotion, intensity)
- Conversation data (summary, key topics, chat messages)
- Intervention techniques used
- Safety planning and follow-up information
- Resources and referrals provided

### CallNote Model
- Additional notes by human operators
- Urgent flag for critical notes
- Author tracking

### EmergencyContact Model
- Emergency contacts for high-risk cases
- Contact tracking and notes

---

## Twilio & AI Integration

### Webhook Setup

In your Twilio Console, configure these webhooks:

1. **Voice URL**: `https://yourdomain.com/twilio/voice/`
2. **Status Callback URL**: `https://yourdomain.com/twilio/status/`
3. **Recording Status Callback**: `https://yourdomain.com/twilio/recording/{call_id}/`

### Call Flow

1. Incoming call hits voice webhook and records audio until silence.
2. SARVAM API detects language and transcribes audio.
3. Guard rails check for content safety.
4. SARVAM-M AI analyzes the conversation, retrieves memories, and assesses risk.
5. If risk/danger is above a threshold, authorities are flagged automatically.
6. Response is generated, converted to speech, and played back to the caller.

---

## Integration with AI Agent

The system is designed to integrate with your LLM agent that processes audio and generates memories. Key integration points:

1. **Audio Processing**: When a recording is completed, trigger your audio processing pipeline.
2. **Memory Creation**: Your AI agent should create Memory records with:
   - Risk assessment
   - Emotional analysis
   - Conversation summary
   - Intervention techniques used
   - Safety planning

### Example Memory Creation

```python
from calls.models import Memory

# After processing audio with your AI agent
memory = Memory.objects.create(
    call=call,
    risk_level='high',
    risk_factors=['social isolation', 'recent loss'],
    protective_factors=['family support', 'therapy engagement'],
    primary_emotion='sad',
    emotion_intensity=8,
    conversation_summary="Caller expressed feelings of hopelessness...",
    key_topics=['grief', 'suicide ideation', 'safety planning'],
    intervention_techniques_used=['active listening', 'safety assessment'],
    chat_messages=[
        {"role": "caller", "message": "I don't see any way out"},
        {"role": "ai", "message": "I hear your pain. Let's talk about what support you have available."}
    ],
    follow_up_needed=True,
    resources_provided=['National Suicide Prevention Lifeline', 'Local crisis center']
)
```

---

## Production Deployment

### Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Set DEBUG=False
- [ ] Configure proper ALLOWED_HOSTS
- [ ] Use PostgreSQL or another production database
- [ ] Set up proper logging
- [ ] Configure HTTPS
- [ ] Set up proper backup strategy
- [ ] Configure Twilio webhooks with HTTPS

### Environment Variables for Production

```env
SECRET_KEY=your-secure-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://username:password@localhost:5432/hotline_db
TWILIO_ACCOUNT_SID=your_production_twilio_sid
TWILIO_AUTH_TOKEN=your_production_twilio_token
TWILIO_PHONE_NUMBER=your_production_phone_number
```

---

## Development

### Adding New Features

1. Create new models in `calls/models.py`
2. Create migrations: `python manage.py makemigrations`
3. Apply migrations: `python manage.py migrate`
4. Add admin configuration in `calls/admin.py`
5. Create serializers in `calls/serializers.py`
6. Add views in `calls/views.py`
7. Update URLs in `calls/urls.py`

### Testing

Create test data:
```bash
python manage.py create_sample_data --calls 50
```

### API Testing

Use tools like Postman or curl to test API endpoints:

```bash
# Get all calls
curl -H "Accept: application/json" http://127.0.0.1:8000/api/calls/

# Get dashboard stats
curl -H "Accept: application/json" http://127.0.0.1:8000/api/dashboard/stats/
```

---

## Support & Contributing

This system provides a robust foundation for a suicide prevention hotline with AI integration. The admin dashboard gives you comprehensive visibility into calls, risk assessments, and memories stored by your AI agent.

For questions or contributions, please refer to the project documentation or contact the development team.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
