# athletes/forms.py
from django import forms
from finance.models import PaymentRecord
from .models import Athlete
from teams.models import Team


class AthleteForm(forms.ModelForm):
    class Meta:
        model = Athlete
        fields = (
            'parent', 'parent_phone', 'parent_email', 'first_name', 'last_name', 'phone_number', 'tc_identity', 'birth_date',
            'gender', 'school', 'license_number', 'joined_date', 'photo',
            'status', 'is_active', 'team', 'custom_fee', 'discount_percentage',
            'regular_payment_day',
        )
        widgets = {
            'parent': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'parent_phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'parent_email': forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
            'first_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'last_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'phone_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'tc_identity': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'maxlength': '11'}),
            'birth_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'school': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'license_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'joined_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'toggle toggle-primary'}),
            'team': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'custom_fee': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01', 'min': '0', 'max': '100'}),
            'regular_payment_day': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'min': '1', 'max': '31'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['team'].queryset = Team.objects.filter(is_active=True).order_by('name')

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


class AthletePaymentEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance or not self.instance.pk:
            self.fields['payment_method'].initial = 'cash'

    class Meta:
        model = PaymentRecord
        fields = ('amount', 'payment_method', 'status', 'notes')
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0',
            }),
            'payment_method': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Dekont no veya ödeme notu',
            }),
        }