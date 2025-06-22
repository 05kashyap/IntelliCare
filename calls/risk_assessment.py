"""
Risk Assessment Service for processing transcriptions and determining suicide risk levels.
"""
import logging
import threading
import requests
from django.utils import timezone
from setfit import SetFitModel

logger = logging.getLogger(__name__)

class RiskAssessmentService:
    """Service for assessing suicide risk from transcriptions"""
    
    def __init__(self):
        self.model = None
        self.model_loading = False
        self.model_load_attempted = False
        self.descr_mapper = {
            "Presence of a loved one": "This class reflects emotional pain rooted in loneliness, lack of connection, or craving emotional support. The person expresses a desire for someone to talk to, lean on, or simply be there during hard times.",
            "Previous attempt": "Refers to prior suicide attempts and the individual's reflections or ambivalence about surviving. There's a mix of regret, fear, and unresolved pain. These expressions show how the trauma of previous attempts lingers.",
            "Ability to take care of oneself": "Shows functional decline, losing interest in hobbies, neglecting responsibilities, and struggling to maintain basic routines. It's a key behavioral indicator of depression, often linked to withdrawal and burnout.",
            "Ability to hope for change": "Reflects a deep sense of hopelessness and despair, often with a desperate wish for something to improve. People in this category express feeling stuck, drained, or unable to see a way forward.",
            "Other": "Mentions non-depressive or positive aspects of life, such as hobbies, nature, learning, or routines. These are grounding statements, and may come from someone coping or recovering, or simply from unrelated content.",
            "Suicidal planning": "Involves explicit thoughts, intentions, or plans about suicide. This is the most acute and dangerous form of ideation, requiring immediate attention in real-life settings.",
            "Ability to control oneself": "Captures the struggle with impulse control and emotional regulation. Individuals here feel out of control, often battling rapid thoughts, urges, or emotional breakdowns that they can't manage.",
            "Consumption": "Describes maladaptive coping behaviors, especially substance use (like alcohol) used to escape pain. It reflects how the person is using external substances to numb or survive emotional turmoil."
        }
        
        self.risk_measure = {
            "Presence of a loved one": "low_risk",
            "Previous attempt": "high_risk",
            "Ability to take care of oneself": "medium_risk",
            "Ability to hope for change": "low_risk",
            "Other": "no_risk",
            "Suicidal planning": "alert",
            "Ability to control oneself": "low_risk",
            "Consumption": "medium_risk"
        }
        
        # Initialize model in background
        self._load_model()
    
    def _load_model(self):
        """Load the SetFit model"""
        if self.model_loading or self.model_load_attempted:
            return
            
        try:
            self.model_loading = True
            logger.info("Loading SetFit suicide risk assessment model...")
            
            # Try to import setfit
            try:
                from setfit import SetFitModel
            except ImportError as e:
                logger.error(f"SetFit not installed: {e}")
                self.model_loading = False
                self.model_load_attempted = True
                return
            
            # Try to load the model
            self.model = SetFitModel.from_pretrained("richie-ghost/setfit-mental-bert-base-uncased-Suicidal-Topic-Check")
            logger.info("SetFit model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load SetFit model: {e}")
            self.model = None
        finally:
            self.model_loading = False
            self.model_load_attempted = True
    
    def translate_text(self, text, target_language="en-IN"):
        """Translate text using Sarvam AI translation API"""
        try:
            url = "https://api.sarvam.ai/translate"
            payload = {
                "input": text,
                "source_language_code": "auto",
                "target_language_code": target_language
            }
            headers = {
                "api-subscription-key": "78ea6d74-9f90-4f0a-9f87-1cc7e1c27d6e",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json().get('translated_text', text)
        except Exception as e:
            logger.warning(f"Translation failed, using original text: {e}")
            return text
    
    def assess_risk(self, text):
        """
        Assess suicide risk from text
        
        Returns:
            dict: Contains risk_category, risk_level, description, and success status
        """
        try:
            # Try to load model if not already loaded
            if not self.model and not self.model_loading and not self.model_load_attempted:
                self._load_model()
            
            # If model is still loading or failed to load, use fallback
            if not self.model:
                logger.warning("SetFit model not available, using fallback risk assessment")
                return self._fallback_risk_assessment(text)
            
            if not text or not text.strip():
                return {
                    'success': True,
                    'risk_category': 'Other',
                    'risk_level': 'no_risk',
                    'description': 'No text to analyze'
                }
            
            # Translate text to English if needed
            translated_text = self.translate_text(text)
            
            # Get prediction from model
            prediction = self.model(translated_text)
            
            # Map to our risk levels
            risk_level = self.risk_measure.get(prediction, 'no_risk')
            description = self.descr_mapper.get(prediction, 'Unknown category')
            
            logger.info(f"Risk assessment: {prediction} -> {risk_level}")
            
            return {
                'success': True,
                'risk_category': prediction,
                'risk_level': risk_level,
                'description': description,
                'translated_text': translated_text
            }
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            return self._fallback_risk_assessment(text)
    
    def _fallback_risk_assessment(self, text):
        """Fallback risk assessment using simple keyword matching"""
        try:
            if not text or not text.strip():
                return {
                    'success': True,
                    'risk_category': 'Other',
                    'risk_level': 'no_risk',
                    'description': 'No text to analyze (fallback)'
                }
            
            text_lower = text.lower()
            
            # High-risk keywords
            high_risk_keywords = [
                'suicide', 'kill myself', 'end my life', 'want to die',
                'planning to die', 'suicide plan', 'kill me', 'ending it all'
            ]
            
            # Alert keywords (most serious)
            alert_keywords = [
                'suicide plan', 'going to kill', 'tonight i will',
                'method to die', 'suicide method', 'plan to end'
            ]
            
            # Medium risk keywords
            medium_risk_keywords = [
                'can\'t take care', 'lost interest', 'drinking to cope',
                'substance abuse', 'can\'t function', 'neglecting'
            ]
            
            # Low risk keywords
            low_risk_keywords = [
                'lonely', 'need someone', 'feeling alone',
                'can\'t control', 'out of control', 'hopeless'
            ]
            
            # Check for different risk levels
            for keyword in alert_keywords:
                if keyword in text_lower:
                    return {
                        'success': True,
                        'risk_category': 'Suicidal planning',
                        'risk_level': 'alert',
                        'description': 'Alert level keywords detected (fallback assessment)'
                    }
            
            for keyword in high_risk_keywords:
                if keyword in text_lower:
                    return {
                        'success': True,
                        'risk_category': 'Previous attempt',
                        'risk_level': 'high_risk',
                        'description': 'High risk keywords detected (fallback assessment)'
                    }
            
            for keyword in medium_risk_keywords:
                if keyword in text_lower:
                    return {
                        'success': True,
                        'risk_category': 'Ability to take care of oneself',
                        'risk_level': 'medium_risk',
                        'description': 'Medium risk keywords detected (fallback assessment)'
                    }
            
            for keyword in low_risk_keywords:
                if keyword in text_lower:
                    return {
                        'success': True,
                        'risk_category': 'Presence of a loved one',
                        'risk_level': 'low_risk',
                        'description': 'Low risk keywords detected (fallback assessment)'
                    }
            
            # Default to Other/no_risk
            return {
                'success': True,
                'risk_category': 'Other',
                'risk_level': 'no_risk',
                'description': 'No risk keywords detected (fallback assessment)'
            }
            
        except Exception as e:
            logger.error(f"Fallback risk assessment failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'risk_category': 'Other',
                'risk_level': 'no_risk',
                'description': 'Risk assessment failed'
            }
    
    def get_risk_priority(self, risk_level):
        """Get numeric priority for risk level (higher = more serious)"""
        priority_map = {
            'no_risk': 0,
            'low_risk': 1,
            'medium_risk': 2,
            'high_risk': 3,
            'alert': 4
        }
        return priority_map.get(risk_level, 0)


def process_chunk_risk_assessment(chunk_id):
    """
    Process risk assessment for a single recording chunk in background.
    This function runs asynchronously and doesn't block the main application.
    """
    from .models import RecordingChunk, Call
    
    def _process_risk():
        try:
            logger.info(f"Starting risk assessment for chunk {chunk_id}")
            
            # Get the chunk
            try:
                chunk = RecordingChunk.objects.get(id=chunk_id)
            except RecordingChunk.DoesNotExist:
                logger.error(f"Chunk {chunk_id} not found")
                return
            
            # Skip if already processed
            if chunk.risk_processed:
                logger.info(f"Chunk {chunk_id} already has risk assessment")
                return
            
            # Skip if no transcription
            if not chunk.transcription:
                logger.info(f"Chunk {chunk_id} has no transcription, skipping risk assessment")
                chunk.risk_processed = True
                chunk.save()
                return
            
            # Perform risk assessment
            risk_service = RiskAssessmentService()
            result = risk_service.assess_risk(chunk.transcription)
            
            if result['success']:
                # Update chunk with risk assessment
                chunk.risk_category = result['risk_category']
                chunk.risk_level = result['risk_level']
                chunk.risk_processed = True
                chunk.save()
                
                logger.info(f"Chunk {chunk_id} risk assessment: {result['risk_category']} -> {result['risk_level']}")
                
                # Update call's highest risk level
                update_call_highest_risk(chunk.call.id)
                
            else:
                logger.error(f"Risk assessment failed for chunk {chunk_id}: {result.get('error')}")
                chunk.risk_processed = True  # Mark as processed even if failed
                chunk.save()
                
        except Exception as e:
            logger.error(f"Error processing risk assessment for chunk {chunk_id}: {e}")
    
    # Run in background thread
    thread = threading.Thread(target=_process_risk, daemon=True)
    thread.start()


def update_call_highest_risk(call_id):
    """Update the call's highest risk level based on all its chunks"""
    from .models import Call, RecordingChunk
    
    try:
        call = Call.objects.get(id=call_id)
        risk_service = RiskAssessmentService()
        
        # Get all processed chunks for this call
        chunks = RecordingChunk.objects.filter(
            call=call,
            risk_processed=True,
            risk_level__isnull=False
        )
        
        if not chunks.exists():
            logger.info(f"No processed chunks with risk levels for call {call_id}")
            return
        
        # Find the highest risk level
        highest_priority = 0
        highest_risk_level = 'no_risk'
        highest_risk_category = None
        
        for chunk in chunks:
            priority = risk_service.get_risk_priority(chunk.risk_level)
            if priority > highest_priority:
                highest_priority = priority
                highest_risk_level = chunk.risk_level
                highest_risk_category = chunk.risk_category
        
        # Update call if risk level changed
        if call.highest_risk_level != highest_risk_level:
            call.highest_risk_level = highest_risk_level
            call.highest_risk_category = highest_risk_category
            call.save()
            
            logger.info(f"Updated call {call_id} highest risk: {highest_risk_level} ({highest_risk_category})")
            
            # Handle high-risk cases
            if highest_risk_level in ['high_risk', 'alert']:
                handle_high_risk_call(call)
        
    except Call.DoesNotExist:
        logger.error(f"Call {call_id} not found")
    except Exception as e:
        logger.error(f"Error updating highest risk for call {call_id}: {e}")


def handle_high_risk_call(call):
    """Handle high-risk calls with additional actions"""
    from .models import EmergencyContact, CallNote
    from django.contrib.auth.models import User
    
    try:
        logger.warning(f"HIGH RISK CALL DETECTED: {call.phone_number} - {call.highest_risk_level}")
        
        # Create emergency contact record if it doesn't exist
        if not call.emergency_contacts.exists():
            EmergencyContact.objects.create(
                call=call,
                contact_type='Crisis Team Alert',
                contact_info=f'Automated high-risk detection: {call.highest_risk_level}',
                notes=f'Risk category: {call.highest_risk_category}',
                contacted=False
            )
        
        # Create urgent call note
        try:
            # Try to get a system user for the note
            system_user = User.objects.filter(is_staff=True).first()
            if system_user:
                CallNote.objects.create(
                    call=call,
                    author=system_user,
                    note=f"AUTOMATED ALERT: High suicide risk detected ({call.highest_risk_level}). "
                         f"Risk category: {call.highest_risk_category}. Immediate review required.",
                    is_urgent=True
                )
        except Exception as e:
            logger.error(f"Failed to create urgent call note: {e}")
        
        # Here you could add more actions:
        # - Send notifications to supervisors
        # - Trigger automatic follow-up calls
        # - Create alerts in external systems
        # - Contact emergency services if critical
        
    except Exception as e:
        logger.error(f"Error handling high-risk call {call.id}: {e}")


# Global service instance
_risk_service = None

def get_risk_service():
    """Get singleton risk assessment service"""
    global _risk_service
    if _risk_service is None:
        _risk_service = RiskAssessmentService()
    return _risk_service
