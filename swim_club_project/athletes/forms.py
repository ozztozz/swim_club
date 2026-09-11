# athletes/forms.py
from django import forms
from finance.models import Equipment, PaymentRecord
from .models import Athlete
from teams.models import Team


class AthleteForm(forms.ModelForm):
    class Meta:
        model = Athlete
        fields = (
            'parent', 'parent_phone', 'parent_email', 'first_name', 'last_name', 'phone_number', 'tc_identity', 'birth_date',
            'gender', 'school', 'license_number', 'joined_date', 'photo',
            'is_active', 'team', 'custom_fee', 'private_lesson_fee',
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
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'school': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'license_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'joined_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'toggle toggle-primary'}),
            'team': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'custom_fee': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'inputmode': 'numeric', 'step': '1', 'min': '0'}),
            'private_lesson_fee': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'inputmode': 'numeric', 'step': '1', 'min': '0'}),
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
    custom_fee = forms.IntegerField(
        required=False,
        label="Özel Aidat Tutar (TL)",
        widget=forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'inputmode': 'numeric', 'step': '1', 'min': '0', 'placeholder': 'Takım aidatını kullanmak için boş bırakın'})
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
            'amount': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'inputmode': 'numeric',
                'data-money-input': 'true',
            }),
            'payment_method': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'status': forms.RadioSelect(attrs={'class': 'radio radio-primary radio-sm'}),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Dekont no veya ödeme notu',
            }),
        }


class AthletePaymentCreateForm(forms.ModelForm):
    class Meta:
        model = PaymentRecord
        fields = (
            'payment_type', 'period', 'amount', 'due_date',
            'payment_method', 'status', 'notes',
        )
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'period': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '2026-09',
            }),
            'amount': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'inputmode': 'numeric',
                'data-money-input': 'true',
            }),
            'due_date': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'input input-bordered w-full',
                'type': 'date',
            }),
            'payment_method': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'status': forms.RadioSelect(attrs={'class': 'radio radio-primary radio-sm'}),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
            }),
        }


class EquipmentSaleForm(forms.Form):
    def __init__(self, *args, initial_quantities=None, coach_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        initial_quantities = initial_quantities or {}
        if coach_queryset is not None:
            self.fields['coach'] = forms.ModelChoiceField(
                queryset=coach_queryset,
                label='Stok sahibi antrenör',
                required=False,
                empty_label='Antrenör seçin',
                widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
            )
        self.equipment_items = list(Equipment.objects.filter(is_active=True))
        for equipment in self.equipment_items:
            self.fields[f'equipment_{equipment.pk}'] = forms.IntegerField(
                label=equipment.name,
                required=False,
                min_value=0,
                initial=initial_quantities.get(equipment.pk, 0),
                widget=forms.NumberInput(attrs={
                    'class': 'input input-bordered w-20 text-center equipment-quantity',
                    'min': '0',
                    'step': '1',
                    'data-price': str(equipment.price),
                }),
            )

    def selected_equipment(self):
        return [
            (equipment, self.cleaned_data.get(f'equipment_{equipment.pk}') or 0)
            for equipment in self.equipment_items
            if (self.cleaned_data.get(f'equipment_{equipment.pk}') or 0) > 0
        ]

    @property
    def equipment_rows(self):
        return [
            {
                'equipment': equipment,
                'field': self[f'equipment_{equipment.pk}'],
            }
            for equipment in self.equipment_items
        ]

    payment_method = forms.ChoiceField(
        choices=PaymentRecord.PAYMENT_METHOD_CHOICES,
        label='Ödeme yöntemi',
        initial='cash',
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )
    status = forms.ChoiceField(
        choices=PaymentRecord.STATUS_CHOICES,
        label='Durum',
        initial='pending',
        widget=forms.RadioSelect(attrs={'class': 'radio radio-primary'}),
    )
    notes = forms.CharField(
        label='Not',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'Satış notu',
        }),
    )