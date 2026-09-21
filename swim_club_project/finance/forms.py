# finance/forms.py

from django import forms
from django.forms.widgets import ClearableFileInput

from .models import (
    Equipment,
    Expense,
    ExpenseCategory,
    PaymentRecord,
    RegularExpense,
)


# =========================================================
# MULTIPLE FILE INPUT
# =========================================================

class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if not data:
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        return [
            single_file_clean(item, initial)
            for item in data
        ]


# =========================================================
# EQUIPMENT
# =========================================================

class EquipmentForm(forms.ModelForm):

    colors_text = forms.CharField(
        required=False,
        label="Renk seçenekleri",
        help_text="Virgülle ayırın. Örn: Pembe, Siyah",
        widget=forms.TextInput(
            attrs={
                "class": "ui-input",
                "placeholder": "Pembe, Siyah",
            }
        ),
    )

    sizes_text = forms.CharField(
        required=False,
        label="Beden seçenekleri",
        help_text=(
            "Virgülle ayırın. Örn: Küçük, Büyük veya "
            "Small, Medium, Large, XLarge"
        ),
        widget=forms.TextInput(
            attrs={
                "class": "ui-input",
                "placeholder": "Small, Medium, Large, XLarge",
            }
        ),
    )

    class Meta:
        model = Equipment

        fields = (
            "name",
            "price",
            "is_active",
        )

        labels = {
            "name": "Malzeme türü",
            "price": "Birim fiyat",
            "is_active": "Aktif",
        }

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "ui-input",
                    "placeholder": "Örn. Kulüp tişörtü",
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": "ui-input ui-input-money",
                    "step": "1",
                    "min": "0",
                    "inputmode": "numeric",
                    "placeholder": "0",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "ui-checkbox",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (
            self.instance
            and self.instance.pk
            and not self.is_bound
        ):
            self.initial["colors_text"] = ", ".join(
                self.instance.colors
            )

            self.initial["sizes_text"] = ", ".join(
                self.instance.sizes
            )

    @staticmethod
    def _split_options(value):
        return list(
            dict.fromkeys(
                option.strip()
                for option in value.replace("\n", ",").split(",")
                if option.strip()
            )
        )

    def clean_colors_text(self):
        return self._split_options(
            self.cleaned_data.get(
                "colors_text",
                "",
            )
        )

    def clean_sizes_text(self):
        return self._split_options(
            self.cleaned_data.get(
                "sizes_text",
                "",
            )
        )

    def save(self, commit=True):
        equipment = super().save(
            commit=False
        )

        equipment.colors = (
            self.cleaned_data.get(
                "colors_text",
                [],
            )
        )

        equipment.sizes = (
            self.cleaned_data.get(
                "sizes_text",
                [],
            )
        )

        if commit:
            equipment.save()

        return equipment


# =========================================================
# EQUIPMENT IMAGES
# =========================================================

class EquipmentImagesForm(forms.Form):

    images = MultipleImageField(
        required=False,
        label="Malzeme görselleri",
        widget=MultipleFileInput(
            attrs={
                "class": "ui-file-input",
                "accept": "image/*",
                "multiple": True,
            }
        ),
    )


# =========================================================
# PAYMENT
# =========================================================

class ProcessPaymentForm(forms.ModelForm):

    class Meta:
        model = PaymentRecord

        fields = (
            "payment_method",
            "notes",
        )

        widgets = {
            "payment_method": forms.Select(
                attrs={
                    "class": "ui-select",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "ui-textarea",
                    "rows": 4,
                    "placeholder": (
                        "Dekont no, açıklama veya "
                        "not ekleyebilirsiniz..."
                    ),
                }
            ),
        }


# =========================================================
# EXPENSE
# =========================================================

class ExpenseForm(forms.ModelForm):

    expense_date = forms.DateField(
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
        model = Expense

        fields = [
            "category",
            "amount",
            "status",
            "reciever",
            "expense_date",
            "receipt_no",
            "notes",
        ]

        labels = {
            "category": "Harcama kategorisi",
            "amount": "Tutar",
            "status": "Gider durumu",
            "reciever": "Alıcı / firma",
            "expense_date": "Harcama tarihi",
            "receipt_no": "Fatura / fiş no",
            "notes": "Açıklama",
        }

        widgets = {

            # -------------------------------------------------
            # CATEGORY
            # -------------------------------------------------

            "category": forms.RadioSelect(
                attrs={
                    "class": "ui-radio",
                }
            ),

            # -------------------------------------------------
            # AMOUNT
            # -------------------------------------------------

            "amount": forms.TextInput(
                attrs={
                    "class": "ui-input ui-input-money",
                    "inputmode": "numeric",
                    "data-money-input": "true",
                    "placeholder": "0",
                }
            ),

            # -------------------------------------------------
            # STATUS
            # -------------------------------------------------

            "status": forms.RadioSelect(
                attrs={
                    "class": "ui-radio",
                }
            ),

            # -------------------------------------------------
            # RECIEVER
            # -------------------------------------------------

            "reciever": forms.TextInput(
                attrs={
                    "class": "ui-input",
                    "placeholder": (
                        "Örn. Kent Havuz İşletmesi"
                    ),
                }
            ),

            # -------------------------------------------------
            # RECEIPT
            # -------------------------------------------------

            "receipt_no": forms.TextInput(
                attrs={
                    "class": "ui-input",
                    "placeholder": "İsteğe bağlı",
                }
            ),

            # -------------------------------------------------
            # NOTES
            # -------------------------------------------------

            "notes": forms.Textarea(
                attrs={
                    "class": "ui-textarea",
                    "rows": 4,
                    "placeholder": (
                        "Harcama ile ilgili kısa bir not..."
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        category_queryset = (
            ExpenseCategory.objects
            .select_related("parent")
            .order_by(
                "parent__name",
                "name",
            )
        )

        categories = list(
            category_queryset
        )

        self.fields["category"].queryset = (
            category_queryset
        )

        self.fields[
            "category"
        ].label_from_instance = (
            lambda category: (
                f"{category.parent.name} / {category.name}"
                if category.parent_id
                else category.name
            )
        )

        self.category_roots = [
            category
            for category in categories
            if not category.parent_id
        ]

        selected_category_id = (
            self["category"].value()
        )

        self.selected_category_id = (
            str(selected_category_id)
            if selected_category_id
            else ""
        )

        self.category_groups = [
            {
                "parent": parent,

                "children": [
                    child
                    for child in categories
                    if child.parent_id == parent.pk
                ],

                "is_selected": (
                    str(selected_category_id)
                    in {
                        str(parent.pk),

                        *[
                            str(child.pk)
                            for child in categories
                            if child.parent_id == parent.pk
                        ],
                    }
                ),
            }

            for parent in self.category_roots
        ]


# =========================================================
# EXPENSE CATEGORY
# =========================================================

class ExpenseCategoryForm(forms.ModelForm):

    class Meta:
        model = ExpenseCategory

        fields = [
            "name",
            "parent",
            "description",
        ]

        labels = {
            "name": "Kategori adı",
            "parent": "Üst kategori",
            "description": "Açıklama",
        }

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "ui-input",
                    "placeholder": (
                        "Örn. Havuz kirası"
                    ),
                    "autofocus": True,
                }
            ),

            "parent": forms.Select(
                attrs={
                    "class": "ui-select",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "ui-textarea",
                    "rows": 3,
                    "placeholder": (
                        "İsteğe bağlı kısa açıklama"
                    ),
                }
            ),
        }


# =========================================================
# REGULAR EXPENSE
# =========================================================

class RegularExpenseForm(forms.ModelForm):

    start_date = forms.DateField(
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

    end_date = forms.DateField(
        required=False,
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
        model = RegularExpense

        fields = [
            "category",
            "amount",
            "reciever",
            "start_date",
            "end_date",
            "frequency",
            "paymentDay",
            "notes",
        ]

        labels = {
            "category": "Harcama kategorisi",
            "amount": "Tutar",
            "reciever": "Alıcı / firma",
            "start_date": "Başlangıç tarihi",
            "end_date": "Bitiş tarihi",
            "frequency": "Tekrarlama sıklığı",
            "paymentDay": "Ödeme günü",
            "notes": "Açıklama",
        }

        widgets = {

            # -------------------------------------------------
            # CATEGORY
            # -------------------------------------------------

            "category": forms.RadioSelect(
                attrs={
                    "class": "ui-radio",
                }
            ),

            # -------------------------------------------------
            # AMOUNT
            # -------------------------------------------------

            "amount": forms.TextInput(
                attrs={
                    "class": "ui-input ui-input-money",
                    "inputmode": "numeric",
                    "data-money-input": "true",
                    "placeholder": "0",
                }
            ),

            # -------------------------------------------------
            # RECIEVER
            # -------------------------------------------------

            "reciever": forms.TextInput(
                attrs={
                    "class": "ui-input",
                    "placeholder": (
                        "Örn. Kent Havuz İşletmesi"
                    ),
                }
            ),

            # -------------------------------------------------
            # FREQUENCY
            # -------------------------------------------------

            "frequency": forms.RadioSelect(
                attrs={
                    "class": "ui-radio",
                }
            ),

            # -------------------------------------------------
            # PAYMENT DAY
            # -------------------------------------------------

            "paymentDay": forms.NumberInput(
                attrs={
                    "class": "ui-input",
                    "min": "1",
                    "max": "31",
                    "inputmode": "numeric",
                    "placeholder": "1-31",
                }
            ),

            # -------------------------------------------------
            # NOTES
            # -------------------------------------------------

            "notes": forms.Textarea(
                attrs={
                    "class": "ui-textarea",
                    "rows": 4,
                    "placeholder": (
                        "İsteğe bağlı açıklama..."
                    ),
                }
            ),
        }