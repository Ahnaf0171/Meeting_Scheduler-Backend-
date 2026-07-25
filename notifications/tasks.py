from huey.contrib.djhuey import db_task
import logging

logger = logging.getLogger(__name__)


@db_task()
def send_invitations_task(meeting_id, meeting_participant_ids):

    from meetings.models import Meeting, MeetingParticipant
    from .services import send_meeting_invitations

    try:
        meeting = Meeting.objects.get(id=meeting_id)
    except Meeting.DoesNotExist:
        logger.error(f"send_invitations_task: Meeting {meeting_id} not found")
        return 0

    targets = MeetingParticipant.objects.select_related("participant").filter(
        id__in=meeting_participant_ids
    )
    return send_meeting_invitations(meeting, targets)


@db_task()
def notify_cancelled_task(meeting_id, reason=""):
    """Background-এ meeting cancellation email পাঠায়।"""
    from meetings.models import Meeting
    from .services import notify_meeting_cancelled

    try:
        meeting = Meeting.objects.get(id=meeting_id)
    except Meeting.DoesNotExist:
        logger.error(f"notify_cancelled_task: Meeting {meeting_id} not found")
        return 0

    return notify_meeting_cancelled(meeting, reason=reason)