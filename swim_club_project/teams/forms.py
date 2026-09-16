from django import forms

from users.models import User

from .models import Team, TeamTrainingSchedule


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ('name', 'description', 'coaches', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Örn. Minikler A',
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Yaş grubu veya takım hakkında kısa bilgi',
            }),
            'coaches': forms.SelectMultiple(attrs={
                'class': 'select select-bordered h-28 w-full',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'toggle toggle-primary',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['coaches'].queryset = User.objects.filter(
            role=User.Role.COACH,
            is_active=True,
        ).order_by('first_name', 'last_name', 'email')
        self.fields['coaches'].required = False


class TeamTrainingScheduleForm(forms.ModelForm):
    class Meta:
        model = TeamTrainingSchedule
        fields = ('weekday', 'training_type', 'start_time', 'end_time', 'location')
        widgets = {
            'weekday': forms.Select(attrs={
                'class': 'select select-bordered h-11 min-h-0 w-full rounded-xl bg-base-100 text-sm',
            }),
            'training_type': forms.RadioSelect(attrs={
                'class': 'radio radio-primary radio-sm',
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'input input-bordered h-11 min-h-0 w-full rounded-xl bg-base-100 text-sm',
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'input input-bordered h-11 min-h-0 w-full rounded-xl bg-base-100 text-sm',
            }),
            'location': forms.TextInput(attrs={
                'class': 'input input-bordered h-11 min-h-0 w-full rounded-xl bg-base-100 text-sm',
                'placeholder': 'Örn. Olimpik havuz',
            }),
        }