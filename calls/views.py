from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
from django.conf import settings
from .models import Call, Memory, CallNote, EmergencyContact
from .serializers import CallSerializer, MemorySerializer, CallNoteSerializer, EmergencyContactSerializer


class CallViewSet(viewsets.ModelViewSet):
    """ViewSet for Call model"""
    queryset = Call.objects.all()
    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter calls based on query parameters"""
        queryset = Call.objects.all()
        status_filter = self.request.query_params.get('status', None)
        risk_level = self.request.query_params.get('risk_level', None)
        phone_number = self.request.query_params.get('phone_number', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if risk_level:
            queryset = queryset.filter(memories__risk_level=risk_level)
        if phone_number:
            queryset = queryset.filter(phone_number__icontains=phone_number)
            
        return queryset.distinct()
    
    @action(detail=True, methods=['get'])
    def memories(self, request, pk=None):
        """Get memories for a specific call"""
        call = self.get_object()
        memories = call.memories.all()
        serializer = MemorySerializer(memories, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a note to a call"""
        call = self.get_object()
        serializer = CallNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(call=call, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MemoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Memory model"""
    queryset = Memory.objects.all()
    serializer_class = MemorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter memories based on query parameters"""
        queryset = Memory.objects.all()
        risk_level = self.request.query_params.get('risk_level', None)
        call_id = self.request.query_params.get('call_id', None)
        
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        if call_id:
            queryset = queryset.filter(call_id=call_id)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def risk_summary(self, request):
        """Get summary of risk levels"""
        from django.db.models import Count
        
        risk_counts = Memory.objects.values('risk_level').annotate(
            count=Count('risk_level')
        ).order_by('risk_level')
        
        return Response(risk_counts)


class CallNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for CallNote model"""
    queryset = CallNote.objects.all()
    serializer_class = CallNoteSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Set the author when creating a note"""
        serializer.save(author=self.request.user)


class EmergencyContactViewSet(viewsets.ModelViewSet):
    """ViewSet for EmergencyContact model"""
    queryset = EmergencyContact.objects.all()
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]


# Dashboard viewsets (no authentication required)
class DashboardCallViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Call model for dashboard"""
    queryset = Call.objects.all()
    serializer_class = CallSerializer
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        """Override list to handle limit parameter properly"""
        queryset = self.get_queryset()
        limit = request.query_params.get('limit', None)
        
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except ValueError:
                pass
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        })

class DashboardMemoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Memory model for dashboard"""
    queryset = Memory.objects.all()
    serializer_class = MemorySerializer
    permission_classes = [AllowAny]


# Twilio webhook views
@csrf_exempt
def twilio_voice_webhook(request):
    """Handle incoming calls from Twilio"""
    if request.method == 'POST':
        # Get call data from Twilio
        call_sid = request.POST.get('CallSid')
        from_number = request.POST.get('From')
        to_number = request.POST.get('To')
        call_status = request.POST.get('CallStatus')
        caller_city = request.POST.get('CallerCity', '')
        caller_state = request.POST.get('CallerState', '')
        caller_country = request.POST.get('CallerCountry', '')
        
        # Create or update call record
        call, created = Call.objects.get_or_create(
            twilio_call_sid=call_sid,
            defaults={
                'phone_number': from_number,
                'status': 'in_progress',
                'caller_city': caller_city,
                'caller_state': caller_state,
                'caller_country': caller_country,
            }
        )
        
        # Create TwiML response
        response = VoiceResponse()
        
        # Welcome message
        response.say(
            "Hello, you've reached the crisis support hotline. "
            "You are not alone, and we're here to help. "
            "Please hold while we connect you with our AI assistant.",
            voice='alice'
        )
        
        # Record the call
        response.record(
            action=f'/calls/twilio/recording/{call.id}/',
            method='POST',
            max_length=3600,  # 1 hour max
            finish_on_key='#',
            play_beep=True
        )
        
        return JsonResponse({'twiml': str(response)}, content_type='application/xml')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def twilio_recording_webhook(request, call_id):
    """Handle recording completion from Twilio"""
    if request.method == 'POST':
        recording_url = request.POST.get('RecordingUrl')
        recording_duration = request.POST.get('RecordingDuration')
        call_duration = request.POST.get('CallDuration')
        
        try:
            call = Call.objects.get(id=call_id)
            call.audio_file_url = recording_url
            if recording_duration:
                from datetime import timedelta
                call.duration = timedelta(seconds=int(recording_duration))
            call.status = 'completed'
            call.save()
            
            # Here you would typically trigger your audio processing
            # and LLM agent to generate memories
            # process_call_audio.delay(call.id)  # Celery task example
            
        except Call.DoesNotExist:
            return JsonResponse({'error': 'Call not found'}, status=404)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def twilio_status_webhook(request):
    """Handle call status updates from Twilio"""
    if request.method == 'POST':
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        call_duration = request.POST.get('CallDuration')
        
        try:
            call = Call.objects.get(twilio_call_sid=call_sid)
            
            # Map Twilio status to our status
            status_mapping = {
                'ringing': 'incoming',
                'in-progress': 'in_progress',
                'completed': 'completed',
                'busy': 'failed',
                'no-answer': 'failed',
                'canceled': 'disconnected',
                'failed': 'failed'
            }
            
            if call_status in status_mapping:
                call.status = status_mapping[call_status]
            
            if call_duration:
                from datetime import timedelta
                call.duration = timedelta(seconds=int(call_duration))
            
            if call_status in ['completed', 'failed', 'canceled']:
                from django.utils import timezone
                call.end_time = timezone.now()
            
            call.save()
            
        except Call.DoesNotExist:
            return JsonResponse({'error': 'Call not found'}, status=404)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_view(request):
    """Dashboard view"""
    return render(request, 'dashboard.html')


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """Get dashboard statistics"""
    from django.db.models import Count, Avg
    from datetime import datetime, timedelta
    
    # Calculate date ranges
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Basic counts
    total_calls = Call.objects.count()
    calls_today = Call.objects.filter(start_time__date=today).count()
    calls_this_week = Call.objects.filter(start_time__date__gte=week_ago).count()
    calls_this_month = Call.objects.filter(start_time__date__gte=month_ago).count()
    
    # Risk level distribution
    risk_distribution = Memory.objects.values('risk_level').annotate(
        count=Count('risk_level')
    ).order_by('risk_level')
    
    # High risk calls that need follow-up
    high_risk_calls = Call.objects.filter(
        memories__risk_level__in=['high', 'critical'],
        memories__follow_up_needed=True
    ).count()
    
    # Average call duration
    avg_duration = Call.objects.filter(
        duration__isnull=False
    ).aggregate(avg_duration=Avg('duration'))
    
    # Status distribution
    status_distribution = Call.objects.values('status').annotate(
        count=Count('status')
    ).order_by('status')
    
    stats = {
        'total_calls': total_calls,
        'calls_today': calls_today,
        'calls_this_week': calls_this_week,
        'calls_this_month': calls_this_month,
        'risk_distribution': list(risk_distribution),
        'high_risk_calls': high_risk_calls,
        'avg_duration': avg_duration['avg_duration'],
        'status_distribution': list(status_distribution),
    }
    
    return JsonResponse(stats)

def test_view(request):
    """Test view"""
    return render(request, 'test.html')

def debug_view(request):
    """Debug view"""
    return render(request, 'debug.html')
