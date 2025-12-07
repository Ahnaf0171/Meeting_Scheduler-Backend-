from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Meeting
from .serializers import (
    MeetingCreateUpdateSerializer,
    MeetingListSerializer,
    MeetingDetailSerializer,
    ConflictCheckSerializer,
    SendInvitationSerializer,
    IcsExportOptionsSerializer,
)
from .services import MeetingService

@extend_schema_view(
    list=extend_schema(tags=["Meetings"]),
    retrieve=extend_schema(tags=["Meetings"]),
    create=extend_schema(tags=["Meetings"]),
    update=extend_schema(tags=["Meetings"]),
    partial_update=extend_schema(tags=["Meetings"]),
    destroy=extend_schema(tags=["Meetings"]),
    check_conflicts=extend_schema(tags=["Meetings"]),
    send_invitations=extend_schema(tags=["Meetings"]),
    export_ics=extend_schema(tags=["Meetings"]),
)
class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.none()

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Meeting.objects.none()
        return MeetingService.list_for_user(user)

    def get_serializer_class(self):
        if self.action == "list":
            return MeetingListSerializer
        if self.action == "retrieve":
            return MeetingDetailSerializer
        return MeetingCreateUpdateSerializer

    def perform_create(self, serializer):
        meeting = serializer.save()
        MeetingService.send_invitations(
            meeting=meeting,
            send_to_all=True,
            participant_ids=[],
        )

    @action(detail=True, methods=["post"], url_path="check-conflicts")
    def check_conflicts(self, request, pk=None):
        meeting = self.get_object()
        serializer = ConflictCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        conflicts = MeetingService.conflicts_for(
            start_time=data["start_time"],
            end_time=data["end_time"],
            participant_emails=data["participant_emails"],
            exclude_meeting_id=meeting.id,
        )
        results = []
        for mp in conflicts:
            m = mp.meeting
            results.append(
                {
                    "participant_email": mp.participant.email,
                    "meeting_id": str(m.id),
                    "meeting_title": m.title,
                    "start_time": m.start_time,
                    "end_time": m.end_time,
                }
            )
        return Response({"conflicts": results}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="send-invitations")
    def send_invitations(self, request, pk=None):
        meeting = self.get_object()
        serializer = SendInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sent = MeetingService.send_invitations(
            meeting=meeting,
            send_to_all=data.get("send_to_all", True),
            participant_ids=data.get("participant_ids") or [],
        )
        return Response({"sent": sent}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="export-ics")
    def export_ics(self, request, pk=None):
        meeting = self.get_object()
        serializer = IcsExportOptionsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        include_participants = serializer.validated_data.get("include_participants", True)
        ics_bytes = MeetingService.export_ics(
            meeting=meeting,
            include_participants=include_participants,
        )
        response = HttpResponse(
            ics_bytes,
            content_type="text/calendar; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="meeting-{meeting.id}.ics"'
        return response
