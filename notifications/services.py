from typing import Iterable
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from calendar_integration.services import generate_meeting_ics
from meetings.models import Meeting, MeetingParticipant
from zoneinfo import ZoneInfo


def send_meeting_invitations(
    meeting: Meeting,
    participants: Iterable[MeetingParticipant],
) -> int:
    participants = list(participants)
    if not participants:
        return 0

    from_email = (
        getattr(settings, "DEFAULT_FROM_EMAIL", None)
        or getattr(meeting.created_by, "email", None)
        or "no-reply@meeting-scheduler.local"
    )

    try:
        tz = ZoneInfo(meeting.timezone)
    except Exception:
        tz = timezone.get_default_timezone()

    start_local = meeting.start_time.astimezone(tz)
    end_local = meeting.end_time.astimezone(tz)
    date_str = start_local.strftime("%Y-%m-%d")
    time_str = f"{start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M')} ({meeting.timezone})"


    subject = f"Invitation: {meeting.title}"
    ics_bytes = generate_meeting_ics(meeting, include_participants=True)

    sent = 0
    for mp in participants:
        recipient = mp.participant.email
        if not recipient:
            continue
        name = mp.participant.name or recipient
        lines = [
            f"Hi {name},",
            "",
            "You are invited to a meeting.",
            "",
            f"Title: {meeting.title}",
            f"Date: {date_str}",
            f"Time: {time_str}",
        ]
        if meeting.location:
            lines.append(f"Location: {meeting.location}")
        if meeting.description:
            lines.extend(["", "Details:", meeting.description])
        lines.append("")
        lines.append("A calendar invite is attached to this email.")
        body = "\n".join(lines)

        message = EmailMessage(subject, body, from_email, [recipient])
        message.attach(
            "meeting.ics",
            ics_bytes,
            "text/calendar; method=REQUEST; charset=UTF-8",
        )
        message.send(fail_silently=False)
        sent += 1

    return sent
