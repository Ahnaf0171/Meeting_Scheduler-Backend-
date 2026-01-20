from rest_framework import serializers
from .models import Meeting, Participant, MeetingParticipant
from .services import MeetingService

class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ("id", "email", "name")

class MeetingParticipantSerializer(serializers.ModelSerializer):
    participant = ParticipantSerializer(read_only=True)

    class Meta:
        model = MeetingParticipant
        fields = (
            "id",
            "participant",
            "role",
            "response_status",
            "is_required",
            "created_at",
        )

class MeetingListSerializer(serializers.ModelSerializer):
    participant_count = serializers.IntegerField(
        source="participants_count", read_only=True
    )
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Meeting
        fields = (
            "id",
            "title",
            "description",
            "location",
            "start_time",
            "end_time",
            "timezone",
            "status",
            "participant_count",
            "created_by_email",
        )


class MeetingDetailSerializer(serializers.ModelSerializer):
    participants = MeetingParticipantSerializer(
        source="meeting_participants", many=True, read_only=True
    )
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Meeting
        fields = (
            "id",
            "title",
            "description",
            "location",
            "start_time",
            "end_time",
            "timezone",
            "status",
            "created_by_email",
            "participants",
            "created_at",
            "updated_at",
        )


class MeetingCreateUpdateSerializer(serializers.ModelSerializer):
    participants = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
    )
    conflicts = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Meeting
        fields = (
            "id",
            "title",
            "description",
            "location",
            "start_time",
            "end_time",
            "timezone",
            "participants",
            "conflicts",
        )

    def validate(self, attrs):
       
        start = attrs.get("start_time")
        end = attrs.get("end_time")

        if self.instance is not None:
            if start is None:
                start = self.instance.start_time
            if end is None:
                end = self.instance.end_time

        if start and end and end <= start:
            raise serializers.ValidationError(
                {"end_time": "end_time must be after start_time."}
            )
        return attrs

    def create(self, validated_data):
        participants_data = validated_data.pop("participants", [])
        request = self.context.get("request")
        user = getattr(request, "user", None)

        allowed_participants, conflict_info = self._partition_participants_by_conflict(
            participants_data=participants_data,
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
            exclude_meeting_id=None,
        )

        meeting = Meeting.objects.create(
            created_by=user,
            **validated_data,
        )

        self._sync_participants(meeting, allowed_participants)
        self.conflict_info = conflict_info
        return meeting

    def update(self, instance, validated_data):
        participants_data = validated_data.pop("participants", None)

        if participants_data is not None:
            allowed_participants, conflict_info = self._partition_participants_by_conflict(
                participants_data=participants_data,
                start_time=validated_data.get("start_time", instance.start_time),
                end_time=validated_data.get("end_time", instance.end_time),
                exclude_meeting_id=instance.id,
            )
            self._sync_participants(instance, allowed_participants)
            self.conflict_info = conflict_info

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def _partition_participants_by_conflict(
        self,
        participants_data,
        start_time,
        end_time,
        exclude_meeting_id=None,
    ):
        
        normalized = []
        for item in participants_data:
            email_raw = (item.get("email") or "").strip().lower()
            if not email_raw:
                continue
            normalized.append((email_raw, item))

        emails = [email for email, _ in normalized]
        if not emails:
            return [item for _, item in normalized], []

        conflicts_qs = MeetingService.conflicts_for(
            start_time=start_time,
            end_time=end_time,
            participant_emails=emails,
            exclude_meeting_id=exclude_meeting_id,
        )

        conflicted_emails = set()
        conflict_info = []

        for mp in conflicts_qs:
            m = mp.meeting
            email = mp.participant.email.lower()
            conflicted_emails.add(email)
            conflict_info.append(
                {
                    "participant_email": mp.participant.email,
                    "meeting_id": str(m.id),
                    "meeting_title": m.title,
                    "start_time": m.start_time,
                    "end_time": m.end_time,
                }
            )

        allowed_participants = [
            item for email, item in normalized if email not in conflicted_emails
        ]
        return allowed_participants, conflict_info

    def _sync_participants(self, meeting, participants_data):
     
        existing_links = {
            mp.participant.email.lower(): mp
            for mp in MeetingParticipant.objects.select_related("participant").filter(
                meeting=meeting
            )
        }
        seen_emails = set()

        for item in participants_data:
            email = (item.get("email") or "").strip().lower()
            if not email or email in seen_emails:
                continue

            seen_emails.add(email)
            name = item.get("name") or ""

            role = item.get("role") or MeetingParticipant.Role.REQUIRED
            response_status = (
                item.get("response_status")
                or MeetingParticipant.ResponseStatus.INVITED
            )
            is_required = item.get("is_required", True)

            participant, created = Participant.objects.get_or_create(
                email=email,
                defaults={"name": name},
                )
            if name and participant.name != name:
                participant.name = name
                participant.save(update_fields=["name"])

            if email in existing_links:
                mp = existing_links[email]
                mp.role = role
                mp.response_status = response_status
                mp.is_required = is_required
                mp.save(update_fields=["role", "response_status", "is_required"])
                del existing_links[email]
            else:
                MeetingParticipant.objects.create(
                    meeting=meeting,
                    participant=participant,
                    role=role,
                    response_status=response_status,
                    is_required=is_required,
                )

        if existing_links:
            MeetingParticipant.objects.filter(
                id__in=[mp.id for mp in existing_links.values()]
            ).delete()

    def get_conflicts(self, obj):
        return getattr(self, "conflict_info", [])

class ConflictCheckSerializer(serializers.Serializer):
    participant_emails = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=False,
    )
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError(
                {"end_time": "end_time must be after start_time."}
            )
        return attrs

class SendInvitationSerializer(serializers.Serializer):
    send_to_all = serializers.BooleanField(default=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )


class IcsExportOptionsSerializer(serializers.Serializer):
    include_participants = serializers.BooleanField(required=False, default=True)
