from django.contrib import admin
from .models import Meeting, Participant, MeetingParticipant

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "created_at")
    search_fields = ("email", "name")
    ordering = ("email",)

class MeetingParticipantInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 0
    autocomplete_fields = ("participant",)

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "end_time", "status", "created_by")
    list_filter = ("status", "timezone", "start_time")
    search_fields = ("title", "description", "created_by__email")
    date_hierarchy = "start_time"
    inlines = [MeetingParticipantInline]

@admin.register(MeetingParticipant)
class MeetingParticipantAdmin(admin.ModelAdmin):
    list_display = ("meeting", "participant", "role", "response_status", "is_required", "created_at")
    list_filter = ("role", "response_status", "is_required")
    search_fields = ("meeting__title", "participant__email", "participant__name")
    autocomplete_fields = ("meeting", "participant")
