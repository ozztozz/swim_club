# finance/forms.py
from django import forms
from .models import PaymentRecord

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