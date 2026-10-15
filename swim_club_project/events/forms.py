from django import forms
from django.forms.widgets import ClearableFileInput

from .models import CompetitionEvent, EventAttachment


class CompetitionEventForm(forms.ModelForm):
    event_date = forms.DateField(
                    input_formats=[
                        "%Y-%m-%d",
                    ],
                    widget=forms.DateInput(
                        format="%Y-%m-%d",
                        attrs={
                            "class": "ui-input",
                            "type": "date",
                        },
                    ),
                )
    class Meta:
        model = CompetitionEvent
        fields = (
            "event_date",
            "name",
            "pool_type",
            "age_group_start",
            "age_group_end",
            "place",
        )
        widgets = {
            "event_date": forms.DateInput(attrs={"class": "ui-input", "type": "date"}),
            "name": forms.TextInput(attrs={"class": "ui-input", "placeholder": "Örn. İstanbul İl Şampiyonası"}),
            "pool_type": forms.Select(attrs={"class": "ui-select"}),
            "age_group_start": forms.TextInput(attrs={"class": "ui-input", "placeholder": "Örn. 8 yaş"}),
            "age_group_end": forms.TextInput(attrs={"class": "ui-input", "placeholder": "Örn. 10 yaş"}),
            "place": forms.TextInput(attrs={"class": "ui-input", "placeholder": "Örn. İstanbul"}),
        }


class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super().clean(item, initial) for item in data]


class EventAttachmentForm(forms.ModelForm):
    class Meta:
        model = EventAttachment
        fields = ["file_name", "file"]
        widgets = {
            "file_name": forms.TextInput(
                attrs={
                    "class": "ui-input",
                    "placeholder": "Örn: Etkinlik Programı 2026",
                }
            ),
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "ui-input ui-input-file",
                    "accept": ".pdf,.xls,.xlsx,.csv,.jpg,.jpeg,.png,.webp",
                }
            ),
        }