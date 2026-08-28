# apps/users/tests/test_api.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class UserAPITests(APITestCase):

    def setUp(self):
        # Test kullanıcıları
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123!',
            role=User.Role.ADMIN
        )
        self.parent_user = User.objects.create_user(
            username='parent',
            email='parent@example.com',
            password='ParentPassword123!',
            role=User.Role.PARENT
        )
        self.login_url = reverse('token_obtain_pair')
        self.profile_url = reverse('user-profile')

    def test_jwt_login_success(self):
        """Geçerli bilgilerle JWT Login testi"""
        data = {
            'email': 'parent@example.com',
            'password': 'ParentPassword123!'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_get_profile_authenticated(self):
        """Giriş yapmış kullanıcının kendi profilini çekme testi"""
        self.client.force_authenticate(user=self.parent_user)
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.parent_user.email)

    def test_get_profile_unauthenticated(self):
        """Giriş yapmamış kullanıcının profile erişim engeli testi"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)