# athletes/forms.py
from django import forms
from .models import Athlete
from teams.models import Team

class AthleteTeamForm(forms.ModelForm):
    # Takım seçimi için dropdown (is_active=True olan takımlar)
    team = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_active=True),
        required=False,
        label="Takım / Seviye",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
        empty_label="-- Takımsız / Atanmadı --"
    )

    # Özel aidat girişi
    custom_fee = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Özel Aidat Tutar (TL)",
        widget=forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01', 'placeholder': 'Takım aidatını kullanmak için boş bırakın'})
    )

    class Meta:
        model = Athlete
        fields = ['team', 'custom_fee']