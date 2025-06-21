from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
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
from .ai_service import (
    twilio_voice_webhook, twilio_recording_webhook, twilio_continue_webhook,
    twilio_user_choice_webhook, twilio_status_webhook
)


class DashboardPermission:
    """Custom permission for dashboard endpoints - always allow access"""
    def has_permission(self, request, view):
        return True
    
    def has_object_permission(self, request, view, obj):
        return True

class IsDashboardAccess(BasePermission):
    """
    Custom permission to allow unauthenticated access to dashboard endpoints
    """
    def has_permission(self, request, view):
        return True  # Allow all access
    
    def has_object_permission(self, request, view, obj):
        return True  # Allow all object access


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
    permission_classes = [IsDashboardAccess]  # Use custom permission
    authentication_classes = []  # No authentication required
    
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
    permission_classes = [IsDashboardAccess]  # Use custom permission
    authentication_classes = []  # No authentication required
    authentication_classes = []  # No authentication required


# Twilio webhook views are now in ai_service.py

@api_view(['GET'])
@authentication_classes([])
@permission_classes([IsDashboardAccess])
def dashboard_view(request):
    """Dashboard view"""
    return render(request, 'dashboard.html')


@api_view(['GET'])
@authentication_classes([])
@permission_classes([IsDashboardAccess])
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


@api_view(['GET'])
@authentication_classes([])
@permission_classes([IsDashboardAccess])
def dashboard_historical_data(request):
    """Get historical data for dashboard charts"""
    from django.db.models import Count, Avg
    from datetime import datetime, timedelta
    
    # Get date range from query params (default to last 7 days)
    days = int(request.GET.get('days', 7))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    # Daily call counts for trends
    daily_calls = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        call_count = Call.objects.filter(start_time__date=date).count()
        daily_calls.append({
            'date': date.strftime('%Y-%m-%d'),
            'date_formatted': date.strftime('%b %d'),
            'count': call_count
        })
    
    # Average response times by day (using call duration as proxy)
    daily_response_times = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        avg_duration = Call.objects.filter(
            start_time__date=date,
            duration__isnull=False
        ).aggregate(avg_duration=Avg('duration'))
        
        # Convert duration to minutes
        avg_minutes = 0
        if avg_duration['avg_duration']:
            avg_minutes = avg_duration['avg_duration'].total_seconds() / 60
        
        daily_response_times.append({
            'date': date.strftime('%Y-%m-%d'),
            'date_formatted': date.strftime('%b %d'),
            'avg_duration_minutes': round(avg_minutes, 1)
        })
    
    # Hourly distribution for current day
    hourly_calls = []
    today = datetime.now().date()
    for hour in range(24):
        call_count = Call.objects.filter(
            start_time__date=today,
            start_time__hour=hour
        ).count()
        hourly_calls.append({
            'hour': hour,
            'hour_formatted': f"{hour:02d}:00",
            'count': call_count
        })
    
    # Risk level trends over time
    risk_trends = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        risk_counts = Memory.objects.filter(
            call__start_time__date=date
        ).values('risk_level').annotate(count=Count('risk_level'))
        
        risk_data = {
            'date': date.strftime('%Y-%m-%d'),
            'date_formatted': date.strftime('%b %d'),
            'low': 0,
            'moderate': 0,
            'high': 0,
            'critical': 0
        }
        
        for item in risk_counts:
            if item['risk_level'] in risk_data:
                risk_data[item['risk_level']] = item['count']
        
        risk_trends.append(risk_data)
    
    return JsonResponse({
        'daily_calls': daily_calls,
        'daily_response_times': daily_response_times,
        'hourly_calls': hourly_calls,
        'risk_trends': risk_trends,
        'date_range': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'days': days
        }
    })

def test_view(request):
    """Test view"""
    return render(request, 'test.html')

def debug_view(request):
    """Debug view"""
    return render(request, 'debug.html')


# Simple dashboard API views (bypass DRF authentication)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def simple_dashboard_calls(request):
    """Simple dashboard calls endpoint without DRF"""
    if request.method == 'GET':
        try:
            limit = int(request.GET.get('limit', 10))
            calls = Call.objects.all().order_by('-start_time')[:limit]
            
            results = []
            for call in calls:
                # Get the latest memory/risk level for this call
                latest_memory = call.memories.order_by('-created_at').first()
                latest_risk_level = None
                if latest_memory:
                    latest_risk_level = {
                        'level': latest_memory.risk_level,
                        'display': latest_memory.get_risk_level_display()
                    }
                
                # Format call duration
                call_duration_formatted = 'N/A'
                if call.duration:
                    total_seconds = int(call.duration.total_seconds())
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    call_duration_formatted = f"{minutes}:{seconds:02d}"
                
                results.append({
                    'id': str(call.id),
                    'phone_number': call.phone_number,
                    'status': call.status,
                    'start_time': call.start_time.isoformat() if call.start_time else None,
                    'end_time': call.end_time.isoformat() if call.end_time else None,
                    'duration': str(call.duration) if call.duration else None,
                    'call_duration_formatted': call_duration_formatted,
                    'caller_city': call.caller_city,
                    'caller_state': call.caller_state,
                    'caller_country': call.caller_country,
                    'latest_risk_level': latest_risk_level,
                })
            
            return JsonResponse({
                'results': results,
                'count': len(results)
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def simple_dashboard_memories(request):
    """Simple dashboard memories endpoint without DRF"""
    if request.method == 'GET':
        try:
            limit = int(request.GET.get('limit', 10))
            memories = Memory.objects.all().order_by('-created_at')[:limit]
            
            results = []
            for memory in memories:
                results.append({
                    'id': str(memory.id),
                    'call_id': str(memory.call.id),
                    'risk_level': memory.risk_level,
                    'primary_emotion': memory.primary_emotion,
                    'emotion_intensity': memory.emotion_intensity,
                    'conversation_summary': memory.conversation_summary,
                    'follow_up_needed': memory.follow_up_needed,
                    'created_at': memory.created_at.isoformat() if memory.created_at else None,
                })
            
            return JsonResponse({
                'results': results,
                'count': len(results)
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
