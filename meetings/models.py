from django.db import models
from uuid import uuid4
from django.conf import settings

class Participant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    email = models.EmailField(max_length=255, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="participants",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("email", "user")
        ordering = ["email"]

    def __str__(self):
        return self.name or self.email


class Meeting(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    timezone = models.CharField(max_length=64, default="UTC")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_meetings",
        on_delete=models.CASCADE,
    )
    participants = models.ManyToManyField(
        Participant,
        through="MeetingParticipant",
        related_name="meetings",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return self.title


class MeetingParticipant(models.Model):
    class Role(models.TextChoices):
        ORGANIZER = "organizer", "Organizer"
        REQUIRED = "required", "Required"
        OPTIONAL = "optional", "Optional"

    class ResponseStatus(models.TextChoices):
        INVITED = "invited", "Invited"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        TENTATIVE = "tentative", "Tentative"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        related_name="meeting_participants",
        on_delete=models.CASCADE,
    )
    participant = models.ForeignKey(
        Participant,
        related_name="meeting_participants",
        on_delete=models.CASCADE,
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.REQUIRED,
    )
    response_status = models.CharField(
        max_length=20,
        choices=ResponseStatus.choices,
        default=ResponseStatus.INVITED,
    )
    is_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("meeting", "participant")
        ordering = ["meeting", "participant__email"]

    def __str__(self):
        return f"{self.participant} @ {self.meeting}"

