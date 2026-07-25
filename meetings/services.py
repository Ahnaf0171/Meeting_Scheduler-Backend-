from typing import Iterable, Sequence
from django.db.models import Count, Q, QuerySet
from django.contrib.auth import get_user_model
from .models import Meeting, MeetingParticipant, Participant
from calendar_integration.services import generate_meeting_ics
from notifications.tasks import send_invitations_task, notify_cancelled_task


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
    def list_visible_for_user(cls, user) -> QuerySet[Meeting]:
        return (
            Meeting.objects.filter(
                Q(created_by=user) | Q(meeting_participants__participant__user=user)
            )
            .select_related("created_by")
            .prefetch_related("meeting_participants__participant")
            .annotate(participants_count=Count("meeting_participants"))
            .distinct()
        )

    @classmethod
    def list_invited_for_user(cls, user) -> QuerySet[Meeting]:
        return (
            Meeting.objects.filter(meeting_participants__participant__user=user)
            .exclude(created_by=user)
            .select_related("created_by")
            .prefetch_related("meeting_participants__participant")
            .annotate(participants_count=Count("meeting_participants"))
            .distinct()
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
        participants_qs = (
            meeting.meeting_participants.select_related("participant")
            if include_participants
            else meeting.meeting_participants.none()
        )
        return generate_meeting_ics(meeting, meeting_participants=participants_qs)

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
        target_ids = list(targets.values_list("id", flat=True))
        send_invitations_task(meeting.id, target_ids)
        return len(target_ids)

    @classmethod
    def send_invitations_to_new_participants(cls, meeting: Meeting, new_emails: set[str]):
        if not new_emails:
            return 0
        target_ids = list(
            meeting.meeting_participants.filter(
                participant__email__in=new_emails
            ).values_list("id", flat=True)
        )
        if target_ids:
            send_invitations_task(meeting.id, target_ids)
        return len(target_ids)

    @classmethod
    def get_or_create_participant(cls, *, email: str, name: str = "") -> Participant:
        email = email.strip().lower()
        participant, created = Participant.objects.get_or_create(
            email=email,
            defaults={"name": name},
        )
        if not created and name and participant.name != name:
            participant.name = name
            participant.save(update_fields=["name"])

        if participant.user_id is None:
            matched_user = get_user_model().objects.filter(email=email).first()
            if matched_user:
                participant.user = matched_user
                participant.save(update_fields=["user"])

        return participant

    @classmethod
    def record_response(cls, meeting: Meeting, *, user, response_status: str) -> MeetingParticipant:
        mp = (
            MeetingParticipant.objects.select_related("participant")
            .filter(meeting=meeting, participant__user=user)
            .first()
        )
        if mp is None:
            raise MeetingParticipant.DoesNotExist(
                "You are not a participant of this meeting."
            )
        mp.response_status = response_status
        mp.save(update_fields=["response_status"])
        return mp

    @classmethod
    def cancel(cls, meeting: Meeting, *, reason: str = "") -> Meeting:
        if meeting.status == Meeting.Status.CANCELLED:
            return meeting
        meeting.status = Meeting.Status.CANCELLED
        meeting.save(update_fields=["status"])
        notify_cancelled_task(meeting.id, reason)
        return meeting