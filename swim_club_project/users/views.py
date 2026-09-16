# apps/users/views.py
from rest_framework import viewsets, generics, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserCreateSerializer
from .permissions import IsAdminUserRole

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    Yöneticilerin kullanıcıları listelemesini, oluşturmasını ve düzenlemesini sağlar.
    """
    queryset = User.objects.all()
    permission_classes = [IsAdminUserRole]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Giriş yapmış her kullanıcının (Veli, Antrenör, Mali İşler, vb.) kendi profilini görmesini ve güncellemesini sağlar.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages

def user_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_coach:
            return redirect('training-attendance')
        return redirect('dashboard-index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.is_coach:
                return redirect('training-attendance')
            return redirect('dashboard-index')
        else:
            messages.error(request, 'Hatalı kullanıcı adı veya şifre!')

    return render(request, 'users/login.html')

def user_logout_view(request):
    logout(request)
    request.session.flush()
    return render(request, 'users/login.html')


@login_required(login_url='user-login')
def password_change_view(request):
    form = PasswordChangeForm(request.user, request.POST or None)

    for field in form.fields.values():
        field.widget.attrs.update({
            'class': 'input input-bordered h-11 min-h-0 w-full rounded-xl border-base-300/80 bg-base-100 px-3 text-sm outline-none focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/10',
        })

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Şifreniz başarıyla değiştirildi.')
        return redirect('password-change')

    return render(request, 'users/password_change.html', {'form': form})