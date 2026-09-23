 # athletes/forms.py
import json

from django import forms
from finance.models import Equipment, PaymentRecord
from .models import Athlete
from teams.models import Team

from django import forms

from .models import Athlete, Team


class AthleteForm(forms.ModelForm):
    class Meta:
        model = Athlete

        fields = (
            'parent',
            'parent_phone',
            'parent_email',
            'first_name',
            'last_name',
            'phone_number',
            'tc_identity',
            'birth_date',
            'gender',
            'school',
            'license_number',
            'joined_date',
            'photo',
            'is_active',
            'team',
            'custom_fee',
            'private_lesson_fee',
            'regular_payment_day',
        )

        widgets = {

            # =====================================================
            # VELİ
            # =====================================================

            'parent': forms.TextInput(
                attrs={
                    'class': 'ui-input',
                    'autocomplete': 'name',
                }
            ),

            'parent_phone': forms.TextInput(
                attrs={
                    'class': 'ui-input',
                    'inputmode': 'tel',
                    'autocomplete': 'tel',
                }
            ),

            'parent_email': forms.EmailInput(
                attrs={
                    'class': 'ui-input',
                    'inputmode': 'email',
                    'autocomplete': 'email',
                }
            ),

            # =====================================================
            # SPORCU
            # =====================================================

            'first_name': forms.TextInput(
                attrs={
                    'class': 'ui-input',
                    'autocomplete': 'given-name',
                }
            ),

            'last_name': forms.TextInput(
                attrs={
                    'class': 'ui-input',
                    'autocomplete': 'family-name',
                }
            ),

            'phone_number': forms.TextInput(
                attrs={
                    'class': 'ui-input',
                    'inputmode': 'tel',
                    'autocomplete': 'tel',
                }
            ),

            'tc_identity': forms.TextInput(
                attrs={
                    'class': 'ui-input',
                    'maxlength': '11',
                    'minlength': '11',
                    'inputmode': 'numeric',
                    'pattern': '[0-9]{11}',
                    'autocomplete': 'off',
                }
            ),

            'birth_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'ui-input',
                    'type': 'date',
                }
            ),

            'gender': forms.Select(
                attrs={
                    'class': 'ui-select',
                }
            ),

            'school': forms.TextInput(
                attrs={
                    'class': 'ui-input',
                }
            ),

            'license_number': forms.TextInput(
                attrs={
                    'class': 'ui-input',
                }
            ),

            'joined_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'ui-input',
                    'type': 'date',
                }
            ),

            # =====================================================
            # FOTOĞRAF
            # =====================================================

            'photo': forms.ClearableFileInput(
                attrs={
                    'class': 'file-input file-input-bordered w-full',
                    'accept': 'image/*',
                }
            ),

            # =====================================================
            # KULÜP
            # =====================================================

            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'toggle toggle-primary',
                }
            ),

            'team': forms.Select(
                attrs={
                    'class': 'ui-select',
                }
            ),

            # =====================================================
            # AİDAT
            # =====================================================

            'custom_fee': forms.NumberInput(
                attrs={
                    'class': 'ui-input',
                    'inputmode': 'numeric',
                    'step': '1',
                    'min': '0',
                }
            ),

            'private_lesson_fee': forms.NumberInput(
                attrs={
                    'class': 'ui-input',
                    'inputmode': 'numeric',
                    'step': '1',
                    'min': '0',
                }
            ),

            'regular_payment_day': forms.NumberInput(
                attrs={
                    'class': 'ui-input',
                    'inputmode': 'numeric',
                    'min': '1',
                    'max': '31',
                    'step': '1',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # =========================================================
        # AKTİF TAKIMLAR
        # =========================================================

        self.fields['team'].queryset = (
            Team.objects
            .filter(is_active=True)
            .order_by('name')
        )

        # =========================================================
        # ÖDEME GÜNÜ
        # HTML tarafındaki sınırları garanti et
        # =========================================================

        self.fields['regular_payment_day'].widget.attrs.update({
            'min': '1',
            'max': '31',
            'step': '1',
            'inputmode': 'numeric',
        })



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
    def __init__(self, *args, initial_quantities=None, initial_variants=None, coach_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        initial_quantities = initial_quantities or {}
        initial_variants = initial_variants or {}
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
            variant_initial = initial_variants.get(equipment.pk, [])
            if isinstance(variant_initial, dict):
                variant_initial = [variant_initial]
            first_variant = variant_initial[0] if variant_initial else {}
            self.fields[f'equipment_{equipment.pk}'] = forms.IntegerField(
                label=equipment.display_name,
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
            colors = [(color, color) for color in equipment.colors]
            sizes = [(size, size) for size in equipment.sizes]
            self.fields[f'equipment_{equipment.pk}_color'] = forms.ChoiceField(
                choices=colors,
                required=False,
                initial=first_variant.get('color') or (equipment.colors[0] if equipment.colors else ''),
                widget=forms.RadioSelect(attrs={'class': 'radio radio-primary radio-xs'}),
            )
            self.fields[f'equipment_{equipment.pk}_size'] = forms.ChoiceField(
                choices=sizes,
                required=False,
                initial=first_variant.get('size') or (equipment.sizes[0] if equipment.sizes else ''),
                widget=forms.RadioSelect(attrs={'class': 'radio radio-primary radio-xs'}),
            )
            self.fields[f'equipment_{equipment.pk}_variants'] = forms.CharField(
                required=False,
                initial=json.dumps(variant_initial, ensure_ascii=False),
                widget=forms.HiddenInput(),
            )

    def selected_equipment(self):
        selected = []
        for equipment in self.equipment_items:
            variants_raw = self.cleaned_data.get(f'equipment_{equipment.pk}_variants') or ''
            if variants_raw:
                try:
                    variants = json.loads(variants_raw)
                except (TypeError, ValueError):
                    self.add_error(f'equipment_{equipment.pk}_variants', 'Varyant bilgisi geçersiz.')
                    continue
                if not isinstance(variants, list):
                    self.add_error(f'equipment_{equipment.pk}_variants', 'Varyant bilgisi geçersiz.')
                    continue
                for variant in variants:
                    if not isinstance(variant, dict):
                        self.add_error(f'equipment_{equipment.pk}_variants', 'Varyant bilgisi geçersiz.')
                        continue
                    quantity = int(variant.get('quantity') or 0)
                    if quantity <= 0:
                        continue
                    color = variant.get('color') or ''
                    size = variant.get('size') or ''
                    if equipment.colors and color not in equipment.colors:
                        self.add_error(f'equipment_{equipment.pk}_variants', 'Geçerli bir renk seçin.')
                        continue
                    if equipment.sizes and size not in equipment.sizes:
                        self.add_error(f'equipment_{equipment.pk}_variants', 'Geçerli bir beden seçin.')
                        continue
                    selected.append((equipment, quantity, color, size))
                continue
            quantity = self.cleaned_data.get(f'equipment_{equipment.pk}') or 0
            if quantity <= 0:
                continue
            color = self.cleaned_data.get(f'equipment_{equipment.pk}_color') or (equipment.colors[0] if equipment.colors else '')
            size = self.cleaned_data.get(f'equipment_{equipment.pk}_size') or (equipment.sizes[0] if equipment.sizes else '')
            if equipment.colors and not color:
                self.add_error(f'equipment_{equipment.pk}_color', 'Renk seçin.')
                continue
            if equipment.sizes and not size:
                self.add_error(f'equipment_{equipment.pk}_size', 'Beden seçin.')
                continue
            selected.append((equipment, quantity, color, size))
        return selected

    @property
    def equipment_rows(self):
        return [
            {
                'equipment': equipment,
                'field': self[f'equipment_{equipment.pk}'],
                'color_field': self[f'equipment_{equipment.pk}_color'],
                'size_field': self[f'equipment_{equipment.pk}_size'],
                'variants_field': self[f'equipment_{equipment.pk}_variants'],
                'colors': bool(equipment.colors),
                'sizes': bool(equipment.sizes),
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