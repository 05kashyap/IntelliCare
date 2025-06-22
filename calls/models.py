from django.db import models
from django.contrib.auth.models import User
import uuid


class Call(models.Model):
    """Model to store call information"""
    CALL_STATUS_CHOICES = [
        ('incoming', 'Incoming'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('disconnected', 'Disconnected'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, help_text="Caller's phone number")
    twilio_call_sid = models.CharField(max_length=100, unique=True, help_text="Twilio Call SID")
    status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='incoming')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True, help_text="Call duration")
    audio_file_url = models.URLField(null=True, blank=True, help_text="URL to recorded audio")
    local_recording_path = models.CharField(max_length=500, null=True, blank=True, help_text="Local path to stored recording")
    local_recording_url = models.CharField(max_length=500, null=True, blank=True, help_text="Local URL to access recording")
    transcription = models.TextField(null=True, blank=True, help_text="Call transcription")
    conversation_state = models.JSONField(null=True, blank=True, help_text="Conversation history for AI processing")
    
    # Location information (if available)
    caller_city = models.CharField(max_length=100, null=True, blank=True)
    caller_state = models.CharField(max_length=100, null=True, blank=True)
    caller_country = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_time']
        verbose_name = "Call"
        verbose_name_plural = "Calls"
    
    def __str__(self):
        return f"Call from {self.phone_number} at {self.start_time}"
    
    @property
    def call_duration_formatted(self):
        """Return formatted duration"""
        if self.duration:
            total_seconds = int(self.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            else:
                return f"{minutes}m {seconds}s"
        return "N/A"


class Memory(models.Model):
    """Model to store LLM agent memories for each call"""
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('moderate', 'Moderate Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
        ('unknown', 'Unknown'),
    ]
    
    EMOTION_CHOICES = [
        ('sad', 'Sad'),
        ('angry', 'Angry'),
        ('anxious', 'Anxious'),
        ('depressed', 'Depressed'),
        ('hopeless', 'Hopeless'),
        ('confused', 'Confused'),
        ('calm', 'Calm'),
        ('neutral', 'Neutral'),
        ('grateful', 'Grateful'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='memories')
    
    # Risk assessment
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='unknown')
    risk_factors = models.JSONField(default=list, help_text="List of identified risk factors")
    protective_factors = models.JSONField(default=list, help_text="List of identified protective factors")
    
    # Emotional state
    primary_emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES, null=True, blank=True)
    emotion_intensity = models.IntegerField(
        null=True, blank=True, 
        help_text="Emotion intensity on a scale of 1-10"
    )
    emotions_detected = models.JSONField(default=list, help_text="Multiple emotions detected")
    
    # Conversation context
    conversation_summary = models.TextField(help_text="Summary of the conversation")
    key_topics = models.JSONField(default=list, help_text="Key topics discussed")
    intervention_techniques_used = models.JSONField(default=list, help_text="Techniques used by the AI")
    
    # Chat/interaction data
    chat_messages = models.JSONField(default=list, help_text="Chat messages exchange")
    
    # Assessment and notes
    mental_health_concerns = models.TextField(null=True, blank=True)
    immediate_safety_plan = models.TextField(null=True, blank=True)
    follow_up_needed = models.BooleanField(default=False)
    follow_up_notes = models.TextField(null=True, blank=True)
    
    # Resources provided
    resources_provided = models.JSONField(default=list, help_text="Resources shared with caller")
    referrals_made = models.JSONField(default=list, help_text="Referrals to other services")
    
    # Metadata
    confidence_score = models.FloatField(
        null=True, blank=True,
        help_text="AI confidence score for the assessment (0.0-1.0)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Memory"
        verbose_name_plural = "Memories"
    
    def __str__(self):
        return f"Memory for {self.call.phone_number} - {self.risk_level} risk"
    
    @property
    def risk_level_color(self):
        """Return color for risk level display"""
        colors = {
            'low': 'green',
            'moderate': 'yellow',
            'high': 'orange',
            'critical': 'red',
            'unknown': 'gray',
        }
        return colors.get(self.risk_level, 'gray')


class CallNote(models.Model):
    """Additional notes for calls by human operators/supervisors"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Call Note"
        verbose_name_plural = "Call Notes"
    
    def __str__(self):
        return f"Note by {self.author.username} on {self.call.phone_number}"


class EmergencyContact(models.Model):
    """Emergency contacts associated with calls"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='emergency_contacts')
    contact_type = models.CharField(max_length=50, help_text="Type of emergency contact")
    contact_info = models.CharField(max_length=200, help_text="Contact information")
    notes = models.TextField(null=True, blank=True)
    contacted = models.BooleanField(default=False)
    contact_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Emergency Contact"
        verbose_name_plural = "Emergency Contacts"
    
    def __str__(self):
        return f"{self.contact_type} for {self.call.phone_number}"


class RecordingChunk(models.Model):
    """Model to store individual recording chunks within a call"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='recording_chunks')
    
    # Recording information
    recording_url = models.URLField(help_text="Twilio recording URL")
    local_recording_path = models.CharField(max_length=500, null=True, blank=True, help_text="Local path to stored recording")
    local_recording_url = models.CharField(max_length=500, null=True, blank=True, help_text="Local URL to access recording")
    
    # Chunk metadata
    chunk_number = models.IntegerField(help_text="Order of this chunk in the call")
    duration_seconds = models.FloatField(null=True, blank=True, help_text="Duration of this chunk in seconds")
    
    # AI processing
    processed = models.BooleanField(default=False, help_text="Whether this chunk has been processed by AI")
    response_audio_url = models.URLField(null=True, blank=True, help_text="URL to AI response audio")
    response_played = models.BooleanField(default=False, help_text="Whether AI response was played to caller")
    
    # Timestamps
    recorded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['chunk_number']
        unique_together = ['call', 'chunk_number']
        verbose_name = "Recording Chunk"
        verbose_name_plural = "Recording Chunks"
    
    def __str__(self):
        return f"Chunk {self.chunk_number} for call {self.call.phone_number}"
