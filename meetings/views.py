from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Meeting, MeetingParticipant
from .serializers import (
    MeetingCreateUpdateSerializer,
    MeetingListSerializer,
    MeetingDetailSerializer,
    MeetingParticipantSerializer,
    ConflictCheckSerializer,
    SendInvitationSerializer,
    IcsExportOptionsSerializer,
    RSVPSerializer,
    MeetingCancelSerializer,
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
    invited=extend_schema(tags=["Meetings"]),
    respond=extend_schema(tags=["Meetings"]),
    cancel=extend_schema(tags=["Meetings"]),
)
class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.none()

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Meeting.objects.none()
        if self.action in ("retrieve", "respond"):
            return MeetingService.list_visible_for_user(user)
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

    def perform_update(self, serializer):
        previous_emails = set(
            serializer.instance.meeting_participants.values_list(
                "participant__email", flat=True
            )
        )
        meeting = serializer.save()
        current_emails = set(
            meeting.meeting_participants.values_list("participant__email", flat=True)
        )
        new_emails = current_emails - previous_emails
        MeetingService.send_invitations_to_new_participants(meeting, new_emails)

    @action(detail=False, methods=["get"], url_path="invited")
    def invited(self, request):
        meetings = MeetingService.list_invited_for_user(request.user)
        page = self.paginate_queryset(meetings)
        serializer = MeetingListSerializer(page if page is not None else meetings, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="respond")
    def respond(self, request, pk=None):
        meeting = self.get_object()
        serializer = RSVPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            mp = MeetingService.record_response(
                meeting,
                user=request.user,
                response_status=serializer.validated_data["response_status"],
            )
        except MeetingParticipant.DoesNotExist as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(MeetingParticipantSerializer(mp).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        meeting = self.get_object()
        serializer = MeetingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meeting = MeetingService.cancel(
            meeting, reason=serializer.validated_data.get("reason", "")
        )
        return Response(MeetingDetailSerializer(meeting).data, status=status.HTTP_200_OK)

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
        queued = MeetingService.send_invitations(
            meeting=meeting,
            send_to_all=data.get("send_to_all", True),
            participant_ids=data.get("participant_ids") or [],
        )
        return Response({"queued": queued}, status=status.HTTP_202_ACCEPTED)

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