from rest_framework import serializers
from .models import Call, Memory, CallNote, EmergencyContact, RecordingChunk, RecordingChunk


class MemorySerializer(serializers.ModelSerializer):
    """Serializer for Memory model"""
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    primary_emotion_display = serializers.CharField(source='get_primary_emotion_display', read_only=True)
    risk_level_color = serializers.CharField(read_only=True)
    
    class Meta:
        model = Memory
        fields = [
            'id', 'call', 'risk_level', 'risk_level_display', 'risk_level_color',
            'risk_factors', 'protective_factors', 'primary_emotion', 
            'primary_emotion_display', 'emotion_intensity', 'emotions_detected',
            'conversation_summary', 'key_topics', 'intervention_techniques_used',
            'chat_messages', 'mental_health_concerns', 'immediate_safety_plan',
            'follow_up_needed', 'follow_up_notes', 'resources_provided',
            'referrals_made', 'confidence_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CallNoteSerializer(serializers.ModelSerializer):
    """Serializer for CallNote model"""
    author_name = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = CallNote
        fields = [
            'id', 'call', 'author', 'author_name', 'note', 'is_urgent',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class EmergencyContactSerializer(serializers.ModelSerializer):
    """Serializer for EmergencyContact model"""
    
    class Meta:
        model = EmergencyContact
        fields = [
            'id', 'call', 'contact_type', 'contact_info', 'notes',
            'contacted', 'contact_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RecordingChunkSerializer(serializers.ModelSerializer):
    """Serializer for RecordingChunk model"""
    
    class Meta:
        model = RecordingChunk
        fields = [
            'id', 'call', 'recording_url', 'local_recording_path', 
            'local_recording_url', 'chunk_number', 'duration_seconds',
            'processed', 'response_audio_url', 'response_played',
            'transcription', 'language_code', 'risk_assessment_completed',
            'recorded_at', 'processed_at'
        ]
        read_only_fields = ['id', 'recorded_at', 'processed_at']


class CallSerializer(serializers.ModelSerializer):
    """Serializer for Call model"""
    memories = MemorySerializer(many=True, read_only=True)
    notes = CallNoteSerializer(many=True, read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    recording_chunks = RecordingChunkSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    call_duration_formatted = serializers.CharField(read_only=True)
    
    # Risk level from the latest memory
    latest_risk_level = serializers.SerializerMethodField()
    latest_emotion = serializers.SerializerMethodField()
    total_chunks = serializers.SerializerMethodField()
    
    class Meta:
        model = Call
        fields = [
            'id', 'phone_number', 'twilio_call_sid', 'status', 'status_display',
            'start_time', 'end_time', 'duration', 'call_duration_formatted',
            'audio_file_url', 'transcription', 'caller_city', 'caller_state',
            'caller_country', 'created_at', 'updated_at', 'memories', 'notes',
            'emergency_contacts', 'recording_chunks', 'latest_risk_level', 'latest_emotion', 'total_chunks'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'call_duration_formatted',
            'latest_risk_level', 'latest_emotion', 'total_chunks'
        ]
    
    def get_latest_risk_level(self, obj):
        """Get the risk level from the most recent memory"""
        latest_memory = obj.memories.first()
        if latest_memory:
            return {
                'level': latest_memory.risk_level,
                'display': latest_memory.get_risk_level_display(),
                'color': latest_memory.risk_level_color
            }
        return None
    
    def get_latest_emotion(self, obj):
        """Get the primary emotion from the most recent memory"""
        latest_memory = obj.memories.first()
        if latest_memory and latest_memory.primary_emotion:
            return {
                'emotion': latest_memory.primary_emotion,
                'display': latest_memory.get_primary_emotion_display(),
                'intensity': latest_memory.emotion_intensity
            }
        return None
    
    def get_total_chunks(self, obj):
        """Get total number of recording chunks"""
        return obj.recording_chunks.count()


class CallSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for call summaries/lists"""
    latest_risk_level = serializers.SerializerMethodField()
    memory_count = serializers.SerializerMethodField()
    note_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Call
        fields = [
            'id', 'phone_number', 'status', 'start_time', 'end_time',
            'call_duration_formatted', 'caller_city', 'caller_state',
            'caller_country', 'latest_risk_level', 'memory_count', 'note_count'
        ]
    
    def get_latest_risk_level(self, obj):
        """Get the risk level from the most recent memory"""
        latest_memory = obj.memories.first()
        if latest_memory:
            return latest_memory.risk_level
        return None
    
    def get_memory_count(self, obj):
        """Get count of memories for this call"""
        return obj.memories.count()
    
    def get_note_count(self, obj):
        """Get count of notes for this call"""
        return obj.notes.count()


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_calls = serializers.IntegerField()
    calls_today = serializers.IntegerField()
    calls_this_week = serializers.IntegerField()
    calls_this_month = serializers.IntegerField()
    high_risk_calls = serializers.IntegerField()
    avg_duration = serializers.DurationField()
    risk_distribution = serializers.ListField()
    status_distribution = serializers.ListField()
