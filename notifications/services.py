from django.conf import settings
from django.core.mail import EmailMessage
from calendar_integration.services import generate_meeting_ics
import logging

logger = logging.getLogger(__name__)


def send_meeting_invitations(meeting, meeting_participants):
    ics_bytes = generate_meeting_ics(meeting, meeting_participants)    
    sent = 0
    failed = []
    
    for mp in meeting_participants:
        participant = mp.participant
        
        if not participant.email:
            logger.warning(f"Skipping participant {participant.id} - no email address")
            continue
        
        try:
            subject = f"Meeting Invitation: {meeting.title}"
            body = (
                f"Hi {participant.name or participant.email},\n\n"
                f"You are invited to a meeting.\n\n"
                f"Title: {meeting.title}\n"
                f"Time: {meeting.start_time} - {meeting.end_time}\n"
                f"Location: {meeting.location or '-'}\n\n"
                f"Please find the calendar invitation attached.\n\n"
                f"Thanks."
            )
            
            msg = EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                to=[participant.email],
            )
            
            msg.attach(
                f"meeting-{meeting.id}.ics",
                ics_bytes,
                "text/calendar; charset=utf-8; method=REQUEST",
            )
            
            msg.send(fail_silently=False)
            sent += 1
            
        except Exception as e:
            logger.error(
                f"Failed to send invitation to {participant.email} "
                f"for meeting {meeting.id}: {str(e)}"
            )
            failed.append({
                "email": participant.email,
                "error": str(e)
            })
            continue
  
    if failed:
        logger.warning(
            f"Meeting {meeting.id}: Sent {sent} invitations, "
            f"{len(failed)} failed: {failed}"
        )
    else:
        logger.info(f"Meeting {meeting.id}: Successfully sent {sent} invitations")
    
    return sent