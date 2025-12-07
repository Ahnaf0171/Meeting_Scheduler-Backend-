from datetime import datetime, timezone as dt_timezone
from django.conf import settings
from django.utils import timezone
from meetings.models import Meeting, MeetingParticipant


def _format_dt_utc(dt: datetime) -> str:
    # datetime যদি naive হয়, আগে project timezone দিয়ে aware করা
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    # Python datetime.timezone.utc ব্যবহার করা (Django 5 compatible)
    dt = dt.astimezone(dt_timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def generate_meeting_ics(meeting: Meeting, include_participants: bool = True) -> bytes:
    dtstamp = _format_dt_utc(timezone.now())
    dtstart = _format_dt_utc(meeting.start_time)
    dtend = _format_dt_utc(meeting.end_time)

    organizer_email = getattr(meeting.created_by, "email", "")
    organizer_name = getattr(meeting.created_by, "full_name", "") or organizer_email

    domain = getattr(settings, "ICS_PRODID_DOMAIN", "meeting-scheduler.local")
    uid = f"meeting-{meeting.id}@{domain}"

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//Meeting Scheduler//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{meeting.title}",
    ]

    if meeting.description:
        desc = meeting.description.replace("\r\n", "\\n").replace("\n", "\\n")
        lines.append(f"DESCRIPTION:{desc}")

    if meeting.location:
        loc = meeting.location.replace("\r\n", " ").replace("\n", " ")
        lines.append(f"LOCATION:{loc}")

    if organizer_email:
        lines.append(f"ORGANIZER;CN={organizer_name}:mailto:{organizer_email}")

    if include_participants:
        participants = meeting.meeting_participants.select_related("participant").all()
        for mp in participants:
            email = mp.participant.email
            name = mp.participant.name or email
            lines.append(f"ATTENDEE;CN={name};RSVP=TRUE:mailto:{email}")

    lines.extend(
        [
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )

    ics_text = "\r\n".join(lines) + "\r\n"
    return ics_text.encode("utf-8")
