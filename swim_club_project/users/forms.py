# users/forms.py
from django import forms

from .models import User


class UserCreateForm(forms.ModelForm):
    """Yönetici kullanıcı oluşturur; kullanıcı adı otomatik üretilir, şifreyi kullanıcı kendisi belirler."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone_number", "role")
        labels = {"first_name": "Ad", "last_name": "Soyad"}
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "ui-input", "autocomplete": "off"}),
            "last_name": forms.TextInput(attrs={"class": "ui-input", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"class": "ui-input", "autocomplete": "off"}),
            "phone_number": forms.TextInput(attrs={"class": "ui-input", "inputmode": "tel"}),
            "role": forms.Select(attrs={"class": "ui-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu e-posta ile kayıtlı bir kullanıcı var.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
        return user