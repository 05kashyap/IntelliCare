from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'calls', views.CallViewSet)
router.register(r'memories', views.MemoryViewSet)
router.register(r'notes', views.CallNoteViewSet)
router.register(r'emergency-contacts', views.EmergencyContactViewSet)

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # Dashboard stats
    path('api/dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    
    # Twilio webhooks
    path('twilio/voice/', views.twilio_voice_webhook, name='twilio_voice_webhook'),
    path('twilio/recording/<uuid:call_id>/', views.twilio_recording_webhook, name='twilio_recording_webhook'),
    path('twilio/status/', views.twilio_status_webhook, name='twilio_status_webhook'),
]
