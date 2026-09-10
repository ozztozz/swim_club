# finance/forms.py
from django import forms
from .models import Equipment, Expense, ExpenseCategory, PaymentRecord, RegularExpense


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ('name', 'price')
        labels = {
            'name': 'Malzeme türü',
            'price': 'Birim fiyat',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Örn. Kulüp tişörtü',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '1',
                'min': '0',
                'inputmode': 'numeric',
                'placeholder': '0',
            }),
        }

class ProcessPaymentForm(forms.ModelForm):
    class Meta:
        model = PaymentRecord
        fields = ['payment_method', 'notes']
        widgets = {
            'payment_method': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Dekont no, açıklama veya not ekleyebilirsiniz...'
            }),
        }


class ExpenseForm(forms.ModelForm):
    expense_date = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'input input-bordered w-full',
                'type': 'date',
            },
        ),
    )

    class Meta:
        model = Expense
        fields = ['category', 'amount', 'reciever', 'expense_date', 'receipt_no', 'notes']
        labels = {
            'category': 'Harcama kategorisi',
            'amount': 'Tutar',
            'reciever': 'Alıcı / firma',
            'expense_date': 'Harcama tarihi',
            'receipt_no': 'Fatura / fiş no',
            'notes': 'Açıklama',
        }
        widgets = {
            'category': forms.RadioSelect(attrs={
                'class': 'radio radio-primary radio-xs',
            }),
            'amount': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'inputmode': 'numeric',
                'data-money-input': 'true',
                'placeholder': '0',
            }),
            'reciever': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Örn. Kent Havuz İşletmesi',
            }),
            'receipt_no': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'İsteğe bağlı',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Harcama ile ilgili kısa bir not...',
            }),
        }


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description']
        labels = {
            'name': 'Kategori adı',
            'description': 'Açıklama',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered input-sm w-full',
                'placeholder': 'Örn. Havuz kirası',
                'autofocus': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered textarea-sm w-full',
                'rows': 2,
                'placeholder': 'İsteğe bağlı kısa açıklama',
            }),
        }


class RegularExpenseForm(forms.ModelForm):
    start_date = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={
            'class': 'input input-bordered w-full',
            'type': 'date',
        }),
    )
    end_date = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={
            'class': 'input input-bordered w-full',
            'type': 'date',
        }),
    )

    class Meta:
        model = RegularExpense
        fields = ['category', 'amount', 'reciever', 'start_date', 'end_date', 'frequency', 'paymentDay', 'notes']
        labels = {
            'category': 'Harcama kategorisi',
            'amount': 'Tutar',
            'reciever': 'Alıcı / firma',
            'start_date': 'Başlangıç tarihi',
            'end_date': 'Bitiş tarihi',
            'frequency': 'Tekrarlama sıklığı',
            'paymentDay': 'Ödeme günü',
            'notes': 'Açıklama',
        }
        widgets = {
            'category': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'amount': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'inputmode': 'numeric',
                'data-money-input': 'true',
                'placeholder': '0',
            }),
            'reciever': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Örn. Kent Havuz İşletmesi',
            }),
            'frequency': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'paymentDay': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1',
                'max': '31',
                'placeholder': '1-31',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'İsteğe bağlı açıklama...',
            }),
        }