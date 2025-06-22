"""
Risk Assessment Service for Suicide Hotline
Integrates the SetFit model for risk classification with Django models
"""
import threading
import logging
import requests
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from .models import Call, Memory, RecordingChunk

# Configure logging
logger = logging.getLogger(__name__)

# Risk mappings from the original risk.py
RISK_CATEGORY_DESCRIPTIONS = {
    "Presence of a loved one": "This class reflects emotional pain rooted in loneliness, lack of connection, or craving emotional support. The person expresses a desire for someone to talk to, lean on, or simply be there during hard times.",
    "Previous attempt": "Refers to prior suicide attempts and the individual's reflections or ambivalence about surviving. There's a mix of regret, fear, and unresolved pain. These expressions show how the trauma of previous attempts lingers.",
    "Ability to take care of oneself": "Shows functional decline, losing interest in hobbies, neglecting responsibilities, and struggling to maintain basic routines. It's a key behavioral indicator of depression, often linked to withdrawal and burnout.",
    "Ability to hope for change": "Reflects a deep sense of hopelessness and despair, often with a desperate wish for something to improve. People in this category express feeling stuck, drained, or unable to see a way forward.",
    "Other": "Mentions non-depressive or positive aspects of life, such as hobbies, nature, learning, or routines. These are grounding statements, and may come from someone coping or recovering, or simply from unrelated content.",
    "Suicidal planning": "Involves explicit thoughts, intentions, or plans about suicide. This is the most acute and dangerous form of ideation, requiring immediate attention in real-life settings.",
    "Ability to control oneself": "Captures the struggle with impulse control and emotional regulation. Individuals here feel out of control, often battling rapid thoughts, urges, or emotional breakdowns that they can't manage.",
    "Consumption": "Describes maladaptive coping behaviors, especially substance use (like alcohol) used to escape pain. It reflects how the person is using external substances to numb or survive emotional turmoil."
}

RISK_LEVELS = {
    "Presence of a loved one": "low",
    "Previous attempt": "high", 
    "Ability to take care of oneself": "moderate",
    "Ability to hope for change": "low",
    "Other": "low",  # Changed from "no risk" to "low" to fit Memory model choices
    "Suicidal planning": "critical",  # Changed from "ALERT!" to "critical" to fit Memory model choices
    "Ability to control oneself": "low",
    "Consumption": "moderate"
}


class RiskAssessmentService:
    """Service for performing risk assessment on transcribed audio"""
    
    def __init__(self):
        self._model = None
        self._sarvam_api_key = "78ea6d74-9f90-4f0a-9f87-1cc7e1c27d6e"  # From original risk.py
        
    def _get_model(self):
        """Lazy load the SetFit model"""
        if self._model is None:
            try:
                from setfit import SetFitModel
                self._model = SetFitModel.from_pretrained("richie-ghost/setfit-mental-bert-base-uncased-Suicidal-Topic-Check")
                logger.info("SetFit risk assessment model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load SetFit model: {e}")
                self._model = False  # Mark as failed to avoid repeated attempts
        return self._model if self._model is not False else None
    
    def _translate_to_english(self, text: str, source_language: str = "auto") -> Optional[str]:
        """Translate text to English using Sarvam AI translation API"""
        try:
            url = "https://api.sarvam.ai/translate"
            payload = {
                "input": text,
                "source_language_code": source_language,
                "target_language_code": "en-IN"
            }
            headers = {
                "api-subscription-key": self._sarvam_api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            translated_text = result.get('translated_text', '')
            
            if translated_text:
                logger.info(f"Successfully translated text from {source_language} to English")
                return translated_text
            else:
                logger.warning("Translation API returned empty text")
                return text  # Return original if translation fails
                
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text  # Return original text if translation fails
    
    def _assess_risk(self, text: str) -> Dict[str, str]:
        """Perform risk assessment on English text"""
        model = self._get_model()
        if not model:
            logger.error("Risk assessment model not available")
            return {
                "category": "Other",
                "risk_level": "unknown",
                "description": "Risk assessment model not available",
                "confidence": "0.0"
            }
        
        try:
            # Get prediction from the model
            prediction = model(text)
            
            # Handle different prediction formats
            if isinstance(prediction, list) and len(prediction) > 0:
                prediction = prediction[0]
            elif prediction is None:
                logger.error("Model returned None prediction")
                return {
                    "category": "Other",
                    "risk_level": "unknown",
                    "description": "Model returned no prediction",
                    "confidence": "0.0"
                }
            
            # Get risk level and description
            risk_level = RISK_LEVELS.get(prediction, "unknown")
            description = RISK_CATEGORY_DESCRIPTIONS.get(prediction, "Unknown risk category")
            
            logger.info(f"Risk assessment completed: {prediction} -> {risk_level}")
            
            return {
                "category": prediction,
                "risk_level": risk_level,
                "description": description,
                "confidence": "1.0"  # SetFit doesn't provide confidence scores easily
            }
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            return {
                "category": "Other",
                "risk_level": "unknown", 
                "description": f"Risk assessment failed: {str(e)}",
                "confidence": "0.0"
            }
    
    def assess_call_risk(self, call_id: str, up_to_chunk: Optional[int] = None) -> Dict[str, str]:
        """
        Assess risk for a call using all transcriptions up to a specific chunk
        
        Args:
            call_id: UUID of the call
            up_to_chunk: Include chunks up to this number (inclusive). If None, include all chunks.
            
        Returns:
            Dict containing risk assessment results
        """
        try:
            call = Call.objects.get(id=call_id)
            
            # Get all recording chunks for this call, ordered by chunk number
            chunks_query = call.recording_chunks.filter(
                transcription__isnull=False
            ).order_by('chunk_number')
            
            if up_to_chunk is not None:
                chunks_query = chunks_query.filter(chunk_number__lte=up_to_chunk)
            
            chunks = list(chunks_query)
            
            if not chunks:
                logger.warning(f"No transcriptions available for call {call_id}")
                return {
                    "category": "Other",
                    "risk_level": "unknown",
                    "description": "No transcriptions available for risk assessment",
                    "confidence": "0.0"
                }
            
            # Combine all transcriptions
            combined_text = " ".join([chunk.transcription for chunk in chunks])
            
            logger.info(f"Assessing risk for call {call_id} using {len(chunks)} chunks")
            logger.debug(f"Combined text length: {len(combined_text)} characters")
            
            # Translate to English if needed (detect if text contains non-English characters)
            if any(ord(char) > 127 for char in combined_text):
                logger.info("Non-English text detected, translating...")
                english_text = self._translate_to_english(combined_text)
                if not english_text:
                    logger.error("Translation failed, using original text")
                    english_text = combined_text
            else:
                english_text = combined_text
            
            # Perform risk assessment
            risk_result = self._assess_risk(english_text)
            
            # Add metadata
            risk_result.update({
                "chunks_analyzed": len(chunks),
                "text_length": len(combined_text),
                "english_text_length": len(english_text)
            })
            
            return risk_result
            
        except Call.DoesNotExist:
            logger.error(f"Call {call_id} not found")
            return {
                "category": "Other", 
                "risk_level": "unknown",
                "description": "Call not found",
                "confidence": "0.0"
            }
        except Exception as e:
            logger.error(f"Error assessing risk for call {call_id}: {e}")
            return {
                "category": "Other",
                "risk_level": "unknown", 
                "description": f"Risk assessment error: {str(e)}",
                "confidence": "0.0"
            }
    
    def update_memory_with_risk(self, call_id: str, risk_result: Dict[str, str]) -> bool:
        """Update or create Memory record with risk assessment results"""
        try:
            call = Call.objects.get(id=call_id)
            
            # Get or create memory for this call
            memory, created = Memory.objects.get_or_create(
                call=call,
                defaults={
                    'risk_level': 'unknown',
                    'conversation_summary': 'Risk assessment in progress',
                    'risk_factors': [],
                    'protective_factors': [],
                    'key_topics': [],
                    'intervention_techniques_used': [],
                    'chat_messages': [],
                    'resources_provided': [],
                    'referrals_made': []
                }
            )
            
            # Update risk assessment fields
            memory.risk_level = risk_result.get('risk_level', 'unknown')
            
            # Add risk factors based on category
            risk_factors = memory.risk_factors or []
            category = risk_result.get('category', 'Other')
            
            if category not in [rf.get('category') for rf in risk_factors]:
                risk_factors.append({
                    'category': category,
                    'description': risk_result.get('description', ''),
                    'confidence': risk_result.get('confidence', '0.0'),
                    'assessed_at': str(timezone.now())
                })
            
            memory.risk_factors = risk_factors
            
            # Update conversation summary if it was default
            if memory.conversation_summary == 'Risk assessment in progress':
                memory.conversation_summary = f"Risk assessment completed: {category} - {risk_result.get('description', '')}"
            
            # Set follow-up needed for high/critical risk
            if memory.risk_level in ['high', 'critical']:
                memory.follow_up_needed = True
                memory.follow_up_notes = f"High risk case identified: {category}"
            
            # Update confidence score
            try:
                memory.confidence_score = float(risk_result.get('confidence', 0.0))
            except (ValueError, TypeError):
                memory.confidence_score = 0.0
            
            memory.save()
            
            logger.info(f"Updated memory for call {call_id} with risk level: {memory.risk_level}")
            
            # Handle high-risk cases
            if memory.risk_level in ['high', 'critical']:
                self._handle_high_risk_case(memory)
            
            return True
            
        except Call.DoesNotExist:
            logger.error(f"Call {call_id} not found for memory update")
            return False
        except Exception as e:
            logger.error(f"Error updating memory for call {call_id}: {e}")
            return False
    
    def _handle_high_risk_case(self, memory: Memory):
        """Handle high-risk cases with additional actions"""
        try:
            from .models import EmergencyContact
            from django.utils import timezone
            
            # Check if emergency contact already exists for this call
            existing_contact = memory.call.emergency_contacts.filter(
                contact_type='Crisis Team - Risk Assessment'
            ).first()
            
            if not existing_contact:
                # Create emergency contact record
                EmergencyContact.objects.create(
                    call=memory.call,
                    contact_type='Crisis Team - Risk Assessment',
                    contact_info='Automated risk assessment identified high risk',
                    notes=f'Risk level: {memory.risk_level}, Category: {memory.risk_factors[-1].get("category") if memory.risk_factors else "Unknown"}',
                    contacted=False  # This would be handled by human operators
                )
                
                logger.warning(f"HIGH RISK CASE DETECTED - Call {memory.call.id}: {memory.risk_level}")
            
        except Exception as e:
            logger.error(f"Error handling high-risk case for call {memory.call.id}: {e}")


# Global instance
risk_service = RiskAssessmentService()


def assess_risk_async(call_id: str, chunk_number: int):
    """
    Asynchronously assess risk for a call using transcriptions up to a specific chunk
    This function is designed to be run in a separate thread
    """
    def _assess_risk_thread():
        try:
            logger.info(f"Starting async risk assessment for call {call_id}, chunk {chunk_number}")
            
            # Perform risk assessment
            risk_result = risk_service.assess_call_risk(call_id, up_to_chunk=chunk_number)
            
            # Update memory with results
            success = risk_service.update_memory_with_risk(call_id, risk_result)
            
            if success:
                # Mark the chunk as risk assessment completed
                try:
                    call = Call.objects.get(id=call_id)
                    chunk = call.recording_chunks.get(chunk_number=chunk_number)
                    chunk.risk_assessment_completed = True
                    chunk.save()
                    logger.info(f"Risk assessment completed for call {call_id}, chunk {chunk_number}")
                except Exception as e:
                    logger.error(f"Error updating chunk risk assessment status: {e}")
            else:
                logger.error(f"Failed to update memory with risk assessment for call {call_id}")
                
        except Exception as e:
            logger.error(f"Error in async risk assessment for call {call_id}: {e}")
    
    # Start the risk assessment in a separate thread
    thread = threading.Thread(target=_assess_risk_thread, daemon=True)
    thread.start()
    logger.info(f"Started risk assessment thread for call {call_id}, chunk {chunk_number}")
