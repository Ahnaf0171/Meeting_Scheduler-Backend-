from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo
from django.utils import timezone
from django.conf import settings

def _utc(dt: datetime) -> str:
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def _local(dt: datetime, tzid: str) -> str:
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt.astimezone(ZoneInfo(tzid)).strftime("%Y%m%dT%H%M%S")

def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

def generate_meeting_ics(meeting, meeting_participants=None) -> bytes:
    tzid = meeting.timezone or "UTC"
    domain = getattr(settings, "ICS_PRODID_DOMAIN", "meeting.local")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        f"X-WR-TIMEZONE:{tzid}",
        "BEGIN:VEVENT",
        f"UID:meeting-{meeting.id}@{domain}",
        f"DTSTAMP:{_utc(timezone.now())}",
        f"DTSTART;TZID={tzid}:{_local(meeting.start_time, tzid)}",
        f"DTEND;TZID={tzid}:{_local(meeting.end_time, tzid)}",
        f"SUMMARY:{_esc(meeting.title)}",
    ]

    if meeting.location:
        lines.append(f"LOCATION:{_esc(meeting.location)}")

    if meeting.description:
        lines.append(f"DESCRIPTION:{_esc(meeting.description)}")

    qs = meeting_participants or meeting.meeting_participants.select_related("participant")
    for mp in qs:
        p = mp.participant
        lines.append(f'ATTENDEE;CN="{_esc(p.name or p.email)}":mailto:{p.email}')

    lines += ["END:VEVENT", "END:VCALENDAR"]
    return ("\r\n".join(lines) + "\r\n").encode()
