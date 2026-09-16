# apps/users/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.urls import reverse

User = get_user_model()

class UserModelTests(TestCase):

    def test_create_user_with_role(self):
        """Kullanıcı başarıyla oluşturuluyor mu ve rolü doğru atanıyor mu?"""
        user = User.objects.create_user(
            username='veli1',
            email='veli@example.com',
            password='Password123!',
            first_name='Ahmet',
            last_name='Yılmaz',
            role=User.Role.PARENT
        )
        self.assertEqual(user.email, 'veli@example.com')
        self.assertTrue(user.check_password('Password123!'))
        self.assertEqual(user.role, User.Role.PARENT)
        self.assertTrue(user.is_parent)
        self.assertFalse(user.is_club_admin)

    def test_default_role_is_parent(self):
        """Rol belirtilmediğinde varsayılan rol PARENT oluyor mu?"""
        user = User.objects.create_user(
            username='veli2',
            email='veli2@example.com',
            password='Password123!'
        )
        self.assertEqual(user.role, User.Role.PARENT)

    def test_authentication_uses_username(self):
        user = User.objects.create_user(
            username='login-user',
            email='login@example.com',
            password='Password123!',
        )

        self.assertEqual(
            authenticate(username='login-user', password='Password123!'),
            user,
        )
        self.assertIsNone(
            authenticate(username='login@example.com', password='Password123!'),
        )

    def test_password_change_screen_updates_password_and_keeps_session(self):
        user = User.objects.create_user(
            username='password-user',
            email='password@example.com',
            password='OldPassword123!',
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse('password-change'),
            {
                'old_password': 'OldPassword123!',
                'new_password1': 'NewPassword123!',
                'new_password2': 'NewPassword123!',
            },
        )

        self.assertRedirects(response, reverse('password-change'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewPassword123!'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_role_properties(self):
        """Rol helper fonksiyonları (is_coach, is_finance vb.) doğru dönüyor mu?"""
        coach = User.objects.create_user(
            username='coach1',
            email='coach@example.com',
            password='Password123!',
            role=User.Role.COACH
        )
        finance = User.objects.create_user(
            username='finance1',
            email='finance@example.com',
            password='Password123!',
            role=User.Role.FINANCE
        )
        
        self.assertTrue(coach.is_coach)
        self.assertFalse(coach.is_parent)
        
        self.assertTrue(finance.is_finance)
        self.assertFalse(finance.is_coach)