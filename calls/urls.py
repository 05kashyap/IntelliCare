from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .ai_service import (
    process_audio_endpoint, 
    test_twilio_call,
    recording_management_endpoint
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'calls', views.CallViewSet)
router.register(r'memories', views.MemoryViewSet)
router.register(r'notes', views.CallNoteViewSet)
router.register(r'emergency-contacts', views.EmergencyContactViewSet)

# Dashboard router (no authentication required)
dashboard_router = DefaultRouter()
dashboard_router.register(r'calls', views.DashboardCallViewSet)
dashboard_router.register(r'memories', views.DashboardMemoryViewSet)

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    path('test/', views.test_view, name='test'),
    path('debug/', views.debug_view, name='debug'),
    
    # API endpoints (authenticated)
    path('api/', include(router.urls)),
    
    # Dashboard API endpoints (public)
    path('api/dashboard/', include(dashboard_router.urls)),
    path('api/dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    path('api/dashboard/historical/', views.dashboard_historical_data, name='dashboard_historical'),
    
    # Simple dashboard endpoints (no authentication)
    path('api/simple-dashboard/calls/', views.simple_dashboard_calls, name='simple_dashboard_calls'),
    path('api/simple-dashboard/memories/', views.simple_dashboard_memories, name='simple_dashboard_memories'),
    
    # Twilio webhooks
    path('twilio/voice/', views.twilio_voice_webhook, name='twilio_voice_webhook'),
    path('twilio/recording/<uuid:call_id>/', views.twilio_recording_webhook, name='twilio_recording_webhook'),
    path('twilio/continue/<uuid:call_id>/', views.twilio_continue_webhook, name='twilio_continue_webhook'),
    path('twilio/user-choice/<uuid:call_id>/', views.twilio_user_choice_webhook, name='twilio_user_choice_webhook'),
    path('twilio/recording-status/<uuid:call_id>/', views.twilio_recording_webhook, name='twilio_recording_status_webhook'),
    path('twilio/status/', views.twilio_status_webhook, name='twilio_status_webhook'),
    
    # Audio processing endpoints
    path('api/process-audio/', process_audio_endpoint, name='process_audio'),
    path('api/test-call/', test_twilio_call, name='test_twilio_call'),
    path('api/recordings/', recording_management_endpoint, name='recording_management'),
]
