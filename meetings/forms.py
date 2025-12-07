from django import forms

from .models import Meeting, Participant, MeetingParticipant
from .services import MeetingService


class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = (
            "title",
            "description",
            "location",
            "start_time",
            "end_time",
            "timezone",
        )

    def __init__(self, *args, **kwargs):
        # view theke expect korbo: user=..., participants_data=[{...}, ...]
        self.user = kwargs.pop("user", None)
        # eita expect korsi: list of dicts [{"email": "...", "name": "...", ...}]
        self.participants_data = kwargs.pop("participants_data", None)
        # conflicts info rakhar jonno (host ke dekhano jabe)
        self.conflicts = []
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")

        # time validation
        if start and end and end <= start:
            self.add_error("end_time", "End time must be after start time.")

        # participants_data theke email gulo collect
        emails = []
        if self.participants_data:
            for item in self.participants_data:
                email = (item.get("email") or "").strip().lower()
                if email:
                    emails.append(email)

        # conflict check: meeting block korbo na, shudhu info store korbo
        if start and end and emails:
            conflicts_qs = MeetingService.conflicts_for(
                start_time=start,
                end_time=end,
                participant_emails=emails,
                exclude_meeting_id=self.instance.id
                if self.instance and self.instance.id
                else None,
            )
            # API er moto: conflicts info host er jonno rakhi
            self.conflicts = [
                {
                    "participant_email": mp.participant.email,
                    "meeting_id": str(mp.meeting_id),
                    "meeting_title": mp.meeting.title,
                    "start_time": mp.meeting.start_time,
                    "end_time": mp.meeting.end_time,
                }
                for mp in conflicts_qs
            ]

        return cleaned

    def save(self, commit=True):
        meeting = super().save(commit=False)

        # notun meeting create hole created_by set korbo
        if self.user and not self.instance.pk:
            meeting.created_by = self.user

        if commit:
            meeting.save()

            # jodi participants_data thake, ogula sync korbo
            if self.participants_data:
                # jeigula conflict e chilo, oder email list
                conflicted_emails = {
                    c["participant_email"].lower()
                    for c in getattr(self, "conflicts", [])
                }

                # existing MeetingParticipant link gulo map kore rakhi
                existing_links = {
                    mp.participant.email.lower(): mp
                    for mp in MeetingParticipant.objects.select_related(
                        "participant"
                    ).filter(meeting=meeting)
                }
                seen_emails = set()

                for item in self.participants_data:
                    email = (item.get("email") or "").strip().lower()
                    if not email or email in seen_emails:
                        continue

                    # ei participant jodi conflict e thake, skip korbo
                    if email in conflicted_emails:
                        continue

                    seen_emails.add(email)
                    name = item.get("name") or ""

                    # valid enum defaults
                    role = item.get("role") or MeetingParticipant.Role.REQUIRED
                    is_required = item.get("is_required", True)

                    # Participant per-host (created_by) basis e
                    participant, _ = Participant.objects.get_or_create(
                        email=email,
                        user=meeting.created_by,
                        defaults={"name": name, "user": meeting.created_by},
                    )

                    # name update (optional)
                    if name and participant.name != name:
                        participant.name = name
                        participant.save(update_fields=["name"])

                    # age theke link thakle update, na thakle notun create
                    if email in existing_links:
                        mp = existing_links[email]
                        mp.role = role
                        mp.is_required = is_required
                        mp.save(update_fields=["role", "is_required"])
                        del existing_links[email]
                    else:
                        MeetingParticipant.objects.create(
                            meeting=meeting,
                            participant=participant,
                            role=role,
                            is_required=is_required,
                        )

                # jei link gulo ar participants_data te nai, chaile remove kori
                if existing_links:
                    MeetingParticipant.objects.filter(
                        id__in=[mp.id for mp in existing_links.values()]
                    ).delete()

                # finally, je participant-ra meeting-e attach hoyeche
                # (mane jeigula conflict chilo na), sudhu oder kache auto email jabe
                MeetingService.send_invitations(
                    meeting=meeting,
                    send_to_all=True,
                    participant_ids=[],
                )

        return meeting


class ParticipantForm(forms.Form):
    email = forms.EmailField()
    name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(
        choices=MeetingParticipant.Role.choices,
        required=False,
    )
    is_required = forms.BooleanField(initial=True, required=False)


class ConflictCheckForm(forms.Form):
    participant_emails = forms.CharField(widget=forms.Textarea)
    start_time = forms.DateTimeField()
    end_time = forms.DateTimeField()

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", "End time must be after start time.")
        return cleaned

    def get_email_list(self):
        raw = self.cleaned_data.get("participant_emails", "")
        parts = raw.replace("\n", ",").split(",")
        emails = [p.strip() for p in parts if p.strip()]
        return emails
