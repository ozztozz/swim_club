from django import forms

from users.models import User

from .models import Team


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