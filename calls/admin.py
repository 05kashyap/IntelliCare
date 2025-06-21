from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Call, Memory, CallNote, EmergencyContact


class MemoryInline(admin.StackedInline):
    """Inline admin for memories within call admin"""
    model = Memory
    extra = 0
    fields = (
        ('risk_level', 'confidence_score'),
        ('primary_emotion', 'emotion_intensity'),
        'conversation_summary',
        ('follow_up_needed', 'follow_up_notes'),
        ('risk_factors', 'protective_factors'),
        ('key_topics', 'emotions_detected'),
        'mental_health_concerns',
        'immediate_safety_plan',
        ('resources_provided', 'referrals_made'),
        'intervention_techniques_used',
        'chat_messages',
    )
    readonly_fields = ('created_at', 'updated_at')


class CallNoteInline(admin.TabularInline):
    """Inline admin for call notes"""
    model = CallNote
    extra = 0
    fields = ('author', 'note', 'is_urgent', 'created_at')
    readonly_fields = ('created_at',)


class EmergencyContactInline(admin.TabularInline):
    """Inline admin for emergency contacts"""
    model = EmergencyContact
    extra = 0
    fields = ('contact_type', 'contact_info', 'contacted', 'contact_time', 'notes')


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    """Admin interface for Call model"""
    list_display = (
        'phone_number', 
        'status', 
        'start_time', 
        'call_duration_formatted',
        'risk_level_display',
        'location_display',
        'has_transcription'
    )
    list_filter = (
        'status', 
        'start_time', 
        'caller_state', 
        'caller_country',
        'memories__risk_level'
    )
    search_fields = (
        'phone_number', 
        'twilio_call_sid', 
        'caller_city', 
        'caller_state',
        'transcription'
    )
    readonly_fields = (
        'id', 
        'created_at', 
        'updated_at', 
        'call_duration_formatted',
        'audio_player'
    )
    fieldsets = (
        ('Call Information', {
            'fields': (
                'id',
                ('phone_number', 'twilio_call_sid'),
                ('status', 'call_duration_formatted'),
                ('start_time', 'end_time'),
                'audio_player',
                'transcription'
            )
        }),
        ('Location Information', {
            'fields': (
                ('caller_city', 'caller_state'),
                'caller_country',
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        })
    )
    inlines = [MemoryInline, CallNoteInline, EmergencyContactInline]
    date_hierarchy = 'start_time'
    actions = ['mark_as_completed', 'export_to_csv']
    
    def risk_level_display(self, obj):
        """Display risk level with color coding"""
        memory = obj.memories.first()
        if memory:
            color = memory.risk_level_color
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                memory.get_risk_level_display()
            )
        return '-'
    risk_level_display.short_description = 'Risk Level'
    
    def location_display(self, obj):
        """Display caller location"""
        location_parts = []
        if obj.caller_city:
            location_parts.append(obj.caller_city)
        if obj.caller_state:
            location_parts.append(obj.caller_state)
        if obj.caller_country:
            location_parts.append(obj.caller_country)
        return ', '.join(location_parts) if location_parts else '-'
    location_display.short_description = 'Location'
    
    def has_transcription(self, obj):
        """Check if call has transcription"""
        return bool(obj.transcription)
    has_transcription.boolean = True
    has_transcription.short_description = 'Transcribed'
    
    def audio_player(self, obj):
        """Display audio player if audio file exists"""
        if obj.audio_file_url:
            return format_html(
                '<audio controls><source src="{}" type="audio/mpeg">Your browser does not support the audio element.</audio>',
                obj.audio_file_url
            )
        return 'No audio file'
    audio_player.short_description = 'Audio Recording'
    
    def mark_as_completed(self, request, queryset):
        """Mark selected calls as completed"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} calls marked as completed.')
    mark_as_completed.short_description = 'Mark selected calls as completed'


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    """Admin interface for Memory model"""
    list_display = (
        'call_phone_number',
        'risk_level_colored',
        'primary_emotion',
        'emotion_intensity',
        'confidence_score',
        'follow_up_needed',
        'created_at'
    )
    list_filter = (
        'risk_level',
        'primary_emotion',
        'follow_up_needed',
        'created_at',
        'confidence_score'
    )
    search_fields = (
        'call__phone_number',
        'conversation_summary',
        'mental_health_concerns',
        'key_topics'
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Call Reference', {
            'fields': ('call',)
        }),
        ('Risk Assessment', {
            'fields': (
                ('risk_level', 'confidence_score'),
                'risk_factors',
                'protective_factors',
            )
        }),
        ('Emotional Analysis', {
            'fields': (
                ('primary_emotion', 'emotion_intensity'),
                'emotions_detected',
            )
        }),
        ('Conversation Data', {
            'fields': (
                'conversation_summary',
                'key_topics',
                'intervention_techniques_used',
                'chat_messages',
            )
        }),
        ('Clinical Assessment', {
            'fields': (
                'mental_health_concerns',
                'immediate_safety_plan',
                ('follow_up_needed', 'follow_up_notes'),
            )
        }),
        ('Resources & Referrals', {
            'fields': (
                'resources_provided',
                'referrals_made',
            )
        }),
        ('Metadata', {
            'fields': (
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        })
    )
    date_hierarchy = 'created_at'
    
    def call_phone_number(self, obj):
        """Display the phone number from related call"""
        return obj.call.phone_number
    call_phone_number.short_description = 'Phone Number'
    
    def risk_level_colored(self, obj):
        """Display risk level with color"""
        color = obj.risk_level_color
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_risk_level_display()
        )
    risk_level_colored.short_description = 'Risk Level'


@admin.register(CallNote)
class CallNoteAdmin(admin.ModelAdmin):
    """Admin interface for CallNote model"""
    list_display = (
        'call_phone_number',
        'author',
        'note_preview',
        'is_urgent',
        'created_at'
    )
    list_filter = (
        'is_urgent',
        'created_at',
        'author'
    )
    search_fields = (
        'call__phone_number',
        'note',
        'author__username'
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    fields = (
        'call',
        'author',
        'note',
        'is_urgent',
        ('created_at', 'updated_at')
    )
    
    def call_phone_number(self, obj):
        """Display the phone number from related call"""
        return obj.call.phone_number
    call_phone_number.short_description = 'Phone Number'
    
    def note_preview(self, obj):
        """Display first 50 characters of note"""
        return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
    note_preview.short_description = 'Note Preview'


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    """Admin interface for EmergencyContact model"""
    list_display = (
        'call_phone_number',
        'contact_type',
        'contact_info',
        'contacted',
        'contact_time',
        'created_at'
    )
    list_filter = (
        'contacted',
        'contact_type',
        'created_at',
        'contact_time'
    )
    search_fields = (
        'call__phone_number',
        'contact_type',
        'contact_info'
    )
    readonly_fields = ('id', 'created_at')
    fields = (
        'call',
        ('contact_type', 'contact_info'),
        ('contacted', 'contact_time'),
        'notes',
        'created_at'
    )
    
    def call_phone_number(self, obj):
        """Display the phone number from related call"""
        return obj.call.phone_number
    call_phone_number.short_description = 'Phone Number'


# Customize admin site headers
admin.site.site_header = "Suicide Prevention Hotline Admin"
admin.site.site_title = "Hotline Admin Portal"
admin.site.index_title = "Welcome to Hotline Administration"
