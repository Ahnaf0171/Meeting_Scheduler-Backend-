from typing import Iterable, Sequence
from django.db.models import Count, QuerySet
from .models import Meeting, MeetingParticipant
from calendar_integration.services import generate_meeting_ics
from notifications.services import send_meeting_invitations


class MeetingService:
    @classmethod
    def list_for_user(cls, user) -> QuerySet[Meeting]:
        return (
            Meeting.objects.filter(created_by=user)
            .select_related("created_by")
            .prefetch_related("meeting_participants__participant")
            .annotate(participants_count=Count("meeting_participants"))
        )

    @classmethod
    def conflicts_for(
        cls,
        *,
        start_time,
        end_time,
        participant_emails: Sequence[str],
        exclude_meeting_id=None,
        ) -> QuerySet[MeetingParticipant]:
        if not participant_emails:
            return MeetingParticipant.objects.none()
    
        normalized_emails = [email.lower() for email in participant_emails]
    
        qs = (
            MeetingParticipant.objects.select_related("meeting", "participant")
            .filter(
                participant__email__in=normalized_emails,  
                meeting__status=Meeting.Status.SCHEDULED,
            )
            .filter(
                meeting__start_time__lt=end_time,
                meeting__end_time__gt=start_time,
            )
        )
        if exclude_meeting_id:
            qs = qs.exclude(meeting_id=exclude_meeting_id)
        return qs

    @classmethod
    def invitation_targets(
        cls,
        meeting: Meeting,
        *,
        send_to_all: bool,
        participant_ids: Iterable,
    ) -> QuerySet[MeetingParticipant]:
        qs = meeting.meeting_participants.select_related("participant")
        if send_to_all or not participant_ids:
            return qs
        return qs.filter(id__in=list(participant_ids))

    @classmethod
    def export_ics(cls, meeting: Meeting, *, include_participants: bool = True) -> bytes:
        return generate_meeting_ics(meeting, include_participants=include_participants)

    @classmethod
    def send_invitations(
        cls,
        meeting: Meeting,
        *,
        send_to_all: bool,
        participant_ids: Iterable,
    ):
        targets = cls.invitation_targets(
            meeting=meeting,
            send_to_all=send_to_all,
            participant_ids=participant_ids,
        )
        return send_meeting_invitations(meeting, targets)
