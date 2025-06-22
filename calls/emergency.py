"""
Emergency contact alert system for critical suicide risk cases.
This module handles alerting emergency contacts when a caller is at immediate risk.
"""

import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from .models import Call, EmergencyContact
from decouple import config


logger = logging.getLogger(__name__)


class EmergencyAlertService:
    """Service for handling emergency contact alerts"""
    
    def __init__(self):
        """Initialize Twilio client and emergency settings"""
        self.account_sid = config('TWILIO_ACCOUNT_SID', default='')
        self.auth_token = config('TWILIO_AUTH_TOKEN', default='')
        self.twilio_number = config('TWILIO_PHONE_NUMBER', default='')
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured. Emergency alerts will be logged only.")
        
        # Sample emergency contact for testing
        self.sample_emergency_contacts = [
            {
                'name': 'Crisis Hotline Supervisor',
                'phone': '+1234567890',  # Test number - replace with actual
                'type': 'supervisor'
            },
            {
                'name': 'Emergency Services',
                'phone': '+1987654321',  # Test number - replace with actual
                'type': 'emergency'
            },
            {
                'name': 'Mental Health Crisis Team',
                'phone': '+1555123456',  # Test number - replace with actual
                'type': 'crisis_team'
            }
        ]
    
    def alert_emergency_contacts(self, call: Call, risk_level: str = 'critical', 
                               caller_info: Optional[Dict] = None) -> Dict:
        """
        Alert emergency contacts about a critical risk situation
        
        Args:
            call: Call object from database
            risk_level: Risk level (critical, high, etc.)
            caller_info: Additional caller information
            
        Returns:
            Dict with alert results
        """
        if risk_level not in ['critical', 'high']:
            logger.info(f"Risk level {risk_level} does not require emergency alerts")
            return {'status': 'no_alert_needed', 'risk_level': risk_level}
        
        # Get caller information
        caller_phone = call.phone_number
        caller_location = self._get_caller_location(call)
        caller_name = caller_info.get('name', 'Unknown Caller') if caller_info else 'Unknown Caller'
        
        # Get emergency contacts from database
        db_contacts = self._get_database_emergency_contacts(call)
        
        # Combine with sample contacts for testing
        all_contacts = db_contacts + self.sample_emergency_contacts
        
        alert_results = {
            'call_id': str(call.id),
            'caller_phone': caller_phone,
            'caller_location': caller_location,
            'risk_level': risk_level,
            'contacts_attempted': 0,
            'contacts_successful': 0,
            'contacts_failed': 0,
            'alerts_sent': [],
            'errors': []
        }
        
        if not all_contacts:
            logger.warning(f"No emergency contacts available for call {call.id}")
            alert_results['errors'].append("No emergency contacts available")
            return alert_results
        
        # Create emergency alert message
        alert_message = self._create_alert_message(
            caller_name=caller_name,
            caller_phone=caller_phone,
            caller_location=caller_location,
            risk_level=risk_level,
            call_time=call.start_time
        )
        
        # Send alerts to each contact
        for contact in all_contacts:
            alert_results['contacts_attempted'] += 1
            
            try:
                result = self._send_voice_alert(
                    contact_phone=contact['phone'],
                    contact_name=contact.get('name', 'Emergency Contact'),
                    alert_message=alert_message,
                    call_id=str(call.id)
                )
                
                if result['success']:
                    alert_results['contacts_successful'] += 1
                    alert_results['alerts_sent'].append({
                        'contact': contact,
                        'call_sid': result.get('call_sid'),
                        'timestamp': timezone.now().isoformat()
                    })
                    
                    # Record in database
                    self._record_emergency_contact_alert(call, contact, result)
                    
                else:
                    alert_results['contacts_failed'] += 1
                    alert_results['errors'].append(f"Failed to contact {contact['name']}: {result.get('error')}")
                    
            except Exception as e:
                alert_results['contacts_failed'] += 1
                alert_results['errors'].append(f"Error contacting {contact.get('name', 'Unknown')}: {str(e)}")
                logger.error(f"Emergency alert error for call {call.id}: {e}")
        
        # Log the emergency alert
        logger.critical(f"EMERGENCY ALERT SENT for call {call.id}. "
                       f"Successful: {alert_results['contacts_successful']}, "
                       f"Failed: {alert_results['contacts_failed']}")
        
        return alert_results
    
    def _get_database_emergency_contacts(self, call: Call) -> List[Dict]:
        """Get emergency contacts from database for this call"""
        contacts = []
        
        # Get existing emergency contacts for this call
        db_contacts = EmergencyContact.objects.filter(call=call)
        
        for contact in db_contacts:
            contacts.append({
                'name': contact.contact_type,
                'phone': contact.contact_info,
                'type': 'database',
                'id': str(contact.id)
            })
        
        return contacts
    
    def _get_caller_location(self, call: Call) -> str:
        """Get formatted caller location"""
        location_parts = []
        
        if call.caller_city:
            location_parts.append(call.caller_city)
        if call.caller_state:
            location_parts.append(call.caller_state)
        if call.caller_country:
            location_parts.append(call.caller_country)
        
        if location_parts:
            return ', '.join(location_parts)
        else:
            return 'Location unknown'
    
    def _create_alert_message(self, caller_name: str, caller_phone: str, 
                            caller_location: str, risk_level: str, call_time) -> str:
        """Create the emergency alert message"""
        
        message = f"""
        EMERGENCY ALERT: This is an automated message from the Suicide Prevention Hotline.
        
        We have identified a {risk_level} risk situation that requires immediate attention.
        
        Caller Information:
        - Name: {caller_name}
        - Phone Number: {caller_phone}
        - Location: {caller_location}
        - Call Time: {call_time.strftime('%Y-%m-%d at %H:%M UTC')}
        - Risk Level: {risk_level.upper()}
        
        The caller has expressed thoughts of self-harm and may be in immediate danger.
        Please respond according to your emergency protocols.
        
        This is an automated alert. Please contact emergency services if immediate intervention is required.
        
        Thank you.
        """
        
        return message.strip()
    
    def _send_voice_alert(self, contact_phone: str, contact_name: str, 
                         alert_message: str, call_id: str) -> Dict:
        """Send voice alert to emergency contact"""
        
        if not self.client:
            # Log only mode when Twilio not configured
            logger.critical(f"EMERGENCY ALERT (LOG ONLY) to {contact_name} ({contact_phone}): {alert_message}")
            return {
                'success': True,
                'call_sid': f'LOGGED_ALERT_{call_id}',
                'method': 'log_only'
            }
        
        try:
            # Create TwiML for the alert call
            twiml_message = self._create_twiml_alert_message(alert_message)
            
            # Make the call
            call = self.client.calls.create(
                to=contact_phone,
                from_=self.twilio_number,
                twiml=twiml_message,
                status_callback=f"{settings.BASE_URL if hasattr(settings, 'BASE_URL') else ''}/twilio/emergency-status/",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed']
            )
            
            logger.info(f"Emergency alert call initiated to {contact_name} ({contact_phone}). Call SID: {call.sid}")
            
            return {
                'success': True,
                'call_sid': call.sid,
                'method': 'twilio_voice'
            }
            
        except Exception as e:
            logger.error(f"Failed to send emergency alert to {contact_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'twilio_voice'
            }
    
    def _create_twiml_alert_message(self, alert_message: str) -> str:
        """Create TwiML for voice alert"""
        response = VoiceResponse()
        
        # Slow down speech and repeat important information
        response.say(
            "Emergency Alert. Emergency Alert. This is the Suicide Prevention Hotline.",
            voice='alice',
            rate='slow'
        )
        
        response.pause(length=1)
        
        # Main alert message
        response.say(
            alert_message,
            voice='alice',
            rate='slow'
        )
        
        response.pause(length=1)
        
        # Repeat critical information
        response.say(
            "This was an emergency alert from the Suicide Prevention Hotline. "
            "Please respond according to your emergency protocols. Thank you.",
            voice='alice',
            rate='slow'
        )
        
        return str(response)
    
    def _record_emergency_contact_alert(self, call: Call, contact: Dict, result: Dict):
        """Record the emergency contact alert in database"""
        
        try:
            emergency_contact, created = EmergencyContact.objects.get_or_create(
                call=call,
                contact_type=contact.get('name', 'Emergency Contact'),
                contact_info=contact['phone'],
                defaults={
                    'contacted': True,
                    'contact_time': timezone.now(),
                    'notes': f"Emergency alert sent via {result.get('method', 'unknown')}. "
                           f"Call SID: {result.get('call_sid', 'N/A')}"
                }
            )
            
            if not created:
                # Update existing record
                emergency_contact.contacted = True
                emergency_contact.contact_time = timezone.now()
                emergency_contact.notes += f"\n\nAdditional alert sent: {timezone.now().isoformat()}"
                emergency_contact.save()
                
        except Exception as e:
            logger.error(f"Failed to record emergency contact alert: {e}")


def alert_emergency_for_critical_risk(call_id: str, caller_info: Optional[Dict] = None) -> Dict:
    """
    Convenience function to alert emergency contacts for critical risk
    
    Args:
        call_id: UUID string of the call
        caller_info: Optional dict with caller information
        
    Returns:
        Dict with alert results
    """
    try:
        call = Call.objects.get(id=call_id)
        service = EmergencyAlertService()
        return service.alert_emergency_contacts(call, 'critical', caller_info)
    except Call.DoesNotExist:
        logger.error(f"Call {call_id} not found for emergency alert")
        return {'status': 'error', 'message': 'Call not found'}
    except Exception as e:
        logger.error(f"Emergency alert failed for call {call_id}: {e}")
        return {'status': 'error', 'message': str(e)}


def test_emergency_alert_system():
    """
    Test function for emergency alert system
    Can be called from Django shell or management command
    """
    # Create a test call if none exists
    from django.utils import timezone
    
    test_call, created = Call.objects.get_or_create(
        phone_number='+1999888777',
        defaults={
            'twilio_call_sid': 'TEST_EMERGENCY_CALL',
            'status': 'in_progress',
            'caller_city': 'Test City',
            'caller_state': 'Test State',
            'caller_country': 'USA'
        }
    )
    
    # Test the emergency alert
    service = EmergencyAlertService()
    result = service.alert_emergency_contacts(
        call=test_call,
        risk_level='critical',
        caller_info={'name': 'Test Caller'}
    )
    
    print("Emergency Alert Test Results:")
    print(f"Call ID: {result.get('call_id')}")
    print(f"Contacts Attempted: {result.get('contacts_attempted')}")
    print(f"Contacts Successful: {result.get('contacts_successful')}")
    print(f"Contacts Failed: {result.get('contacts_failed')}")
    print(f"Errors: {result.get('errors')}")
    
    return result
