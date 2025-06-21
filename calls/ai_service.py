"""
Example service for integrating with LLM agent and processing audio
This file shows how you would integrate your AI agent with the Django backend
"""
import requests
import json
from django.conf import settings
from django.http import JsonResponse
from .models import Call, Memory


class AIAgentService:
    """Service for interacting with AI agent"""
    
    def __init__(self):
        self.agent_api_url = getattr(settings, 'AI_AGENT_API_URL', 'http://localhost:5000')
    
    def process_call_audio(self, call_id):
        """
        Process audio from a call and create memory record
        This would be called after a recording is completed
        """
        try:
            call = Call.objects.get(id=call_id)
            
            # Step 1: Send audio to AI agent for processing
            agent_response = self._send_audio_to_agent(call.audio_file_url)
            
            # Step 2: Create memory record from agent response
            memory = self._create_memory_from_response(call, agent_response)
            
            # Step 3: Update call with transcription if provided
            if agent_response.get('transcription'):
                call.transcription = agent_response['transcription']
                call.save()
            
            return memory
            
        except Call.DoesNotExist:
            raise ValueError(f"Call {call_id} not found")
        except Exception as e:
            print(f"Error processing call audio: {e}")
            raise
    
    def _send_audio_to_agent(self, audio_url):
        """
        Send audio URL to AI agent for processing
        Replace this with your actual AI agent API call
        """
        payload = {
            'audio_url': audio_url,
            'task': 'crisis_intervention_analysis'
        }
        
        # This is a mock response - replace with actual API call
        # response = requests.post(f"{self.agent_api_url}/process_audio", json=payload)
        # return response.json()
        
        # Mock response for demonstration
        return {
            'risk_assessment': {
                'level': 'moderate',
                'factors': ['social isolation', 'recent job loss'],
                'protective_factors': ['family support', 'previous therapy experience'],
                'confidence': 0.85
            },
            'emotional_analysis': {
                'primary_emotion': 'sad',
                'intensity': 7,
                'detected_emotions': ['sad', 'anxious', 'hopeless']
            },
            'conversation_analysis': {
                'summary': 'Caller experiencing depression following job loss. Expressed some hopeless thoughts but no immediate suicide plan. Responsive to intervention.',
                'key_topics': ['unemployment', 'financial stress', 'depression', 'family support'],
                'intervention_techniques': ['active listening', 'empathy', 'resource sharing', 'safety assessment'],
                'safety_plan_needed': True
            },
            'chat_messages': [
                {'role': 'caller', 'message': 'I lost my job last week and I don\'t know what to do anymore'},
                {'role': 'ai', 'message': 'I can hear how difficult this situation is for you. Job loss can be really overwhelming. Can you tell me more about what you\'re feeling right now?'},
                {'role': 'caller', 'message': 'I feel like such a failure. My family is counting on me and I let them down'},
                {'role': 'ai', 'message': 'Those feelings of disappointment are understandable, but losing a job doesn\'t make you a failure as a person. Let\'s talk about the support you have available and some next steps we can explore together.'}
            ],
            'resources_recommended': [
                'National Suicide Prevention Lifeline',
                'Local unemployment office',
                'Career counseling services',
                'Financial assistance programs'
            ],
            'follow_up_required': True,
            'transcription': 'Full call transcription would be here...'
        }
    
    def _create_memory_from_response(self, call, agent_response):
        """Create Memory record from AI agent response"""
        
        risk_data = agent_response.get('risk_assessment', {})
        emotion_data = agent_response.get('emotional_analysis', {})
        conversation_data = agent_response.get('conversation_analysis', {})
        
        memory = Memory.objects.create(
            call=call,
            # Risk assessment
            risk_level=risk_data.get('level', 'unknown'),
            risk_factors=risk_data.get('factors', []),
            protective_factors=risk_data.get('protective_factors', []),
            confidence_score=risk_data.get('confidence'),
            
            # Emotional analysis
            primary_emotion=emotion_data.get('primary_emotion'),
            emotion_intensity=emotion_data.get('intensity'),
            emotions_detected=emotion_data.get('detected_emotions', []),
            
            # Conversation data
            conversation_summary=conversation_data.get('summary', ''),
            key_topics=conversation_data.get('key_topics', []),
            intervention_techniques_used=conversation_data.get('intervention_techniques', []),
            chat_messages=agent_response.get('chat_messages', []),
            
            # Follow-up and resources
            follow_up_needed=agent_response.get('follow_up_required', False),
            resources_provided=agent_response.get('resources_recommended', []),
            
            # Safety planning
            immediate_safety_plan=self._generate_safety_plan(conversation_data),
        )
        
        return memory
    
    def _generate_safety_plan(self, conversation_data):
        """Generate safety plan based on conversation analysis"""
        if conversation_data.get('safety_plan_needed'):
            return """
            Immediate Safety Plan:
            1. Remove or secure any means of self-harm
            2. Contact support person: [family member/friend identified]
            3. Call crisis hotline if feelings worsen: 988
            4. Use coping strategies: [breathing exercises, grounding techniques]
            5. Follow up with mental health professional within 48 hours
            """
        return ""
    
    def get_real_time_analysis(self, call_id, audio_chunk):
        """
        Get real-time analysis during an ongoing call
        This could be used for live risk assessment
        """
        payload = {
            'call_id': call_id,
            'audio_chunk': audio_chunk,
            'analysis_type': 'real_time_risk'
        }
        
        # Mock response - replace with actual API call
        return {
            'current_risk_level': 'moderate',
            'emotional_state': 'distressed',
            'intervention_suggestion': 'Focus on safety assessment',
            'confidence': 0.75
        }


# Example usage in your Django views or Celery tasks
def process_call_audio_task(call_id):
    """
    This could be a Celery task that processes audio after recording completion
    """
    agent_service = AIAgentService()
    try:
        memory = agent_service.process_call_audio(call_id)
        print(f"Created memory {memory.id} for call {call_id}")
        
        # If high risk, trigger additional actions
        if memory.risk_level in ['high', 'critical']:
            # Send alerts, create emergency contacts, etc.
            handle_high_risk_case(memory)
            
    except Exception as e:
        print(f"Error processing call {call_id}: {e}")


def handle_high_risk_case(memory):
    """Handle high-risk cases with additional actions"""
    from .models import EmergencyContact
    
    # Create emergency contact record
    EmergencyContact.objects.create(
        call=memory.call,
        contact_type='Crisis Team',
        contact_info='Emergency services contacted',
        notes=f'High risk case - {memory.risk_level} level',
        contacted=True
    )
    
    # Here you could also:
    # - Send notifications to supervisors
    # - Trigger automatic follow-up calls
    # - Create urgent alerts in the system
    # - Contact emergency services if critical


# Example API integration endpoint
def webhook_ai_agent_update(request):
    """
    Webhook endpoint for AI agent to send updates
    Your AI agent can call this endpoint to update memories in real-time
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        call_id = data.get('call_id')
        
        try:
            call = Call.objects.get(id=call_id)
            memory = call.memories.first()
            
            if memory:
                # Update memory with new analysis
                if 'risk_level' in data:
                    memory.risk_level = data['risk_level']
                if 'emotional_state' in data:
                    memory.primary_emotion = data['emotional_state']
                if 'conversation_update' in data:
                    memory.conversation_summary += f"\n\nUpdate: {data['conversation_update']}"
                
                memory.save()
                
                return JsonResponse({'success': True})
            
        except Call.DoesNotExist:
            return JsonResponse({'error': 'Call not found'}, status=404)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
