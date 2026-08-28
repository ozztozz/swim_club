# athletes/tests/test_dashboard.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from athletes.models import Athlete
import datetime

User = get_user_model()

class DashboardViewsTests(TestCase):
    def setUp(self):
        # 1. Kullanıcı Oluşturma (is_active ve role açıkça belirtilmeli)
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='Password123!',
            role='club_admin',
            is_staff=True,
            is_active=True
        )
        self.parent_user = User.objects.create_user(
            username='parent_user',
            email='parent@test.com',
            password='Password123!',
            role='parent',
            is_active=True
        )

        # 2. Test Sporcusu (Onay Bekleyen)
        self.athlete = Athlete.objects.create(
            parent=self.parent_user,
            first_name='Ege',
            last_name='Yılmaz',
            birth_date=datetime.date(2012, 5, 10),
            gender='M',
            joined_date=datetime.date.today(),
            status='pending',
            is_active=False
        )

        # URL Tanımlamaları
        self.dashboard_url = reverse('dashboard-index')
        self.approve_url = reverse('dashboard-approve-athlete', kwargs={'pk': self.athlete.pk})
        self.reject_url = reverse('dashboard-reject-athlete', kwargs={'pk': self.athlete.pk})
    def test_parent_user_access_denied(self):
        """Veli roldeki kullanıcı dashboard'a erişmek istediğinde 403 Forbidden almalı"""
        self.client.force_login(self.parent_user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 403)

    def test_admin_user_can_access_dashboard(self):
        """Admin roldeki kullanıcı dashboard'a erişebilmeli ve onay bekleyen sporcuyu görebilmeli"""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ege')
        self.assertContains(response, 'Yılmaz')

    def test_admin_can_approve_athlete_via_htmx(self):
        """Admin HTMX POST isteği ile sporcuyu onaylayabilmeli"""
        self.client.force_login(self.admin_user)
        response = self.client.post(self.approve_url, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)

        self.athlete.refresh_from_db()
        self.assertEqual(self.athlete.status, 'approved')
        self.assertTrue(self.athlete.is_active)

    def test_admin_can_reject_athlete_via_htmx(self):
        """Admin HTMX POST isteği ile sporcu kaydını reddedebilmeli"""
        self.client.force_login(self.admin_user)
        response = self.client.post(self.reject_url, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)

        self.athlete.refresh_from_db()
        self.assertEqual(self.athlete.status, 'rejected')
        self.assertFalse(self.athlete.is_active)

    def test_get_method_not_allowed_on_approve(self):
        """Onayla fonksiyonuna GET isteği atıldığında 405 Method Not Allowed dönmeli (@require_POST)"""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.approve_url)
        self.assertEqual(response.status_code, 405)
    def test_admin_can_search_approved_athletes(self):
        """Admin onaylı sporcular arasında HTMX ile arama yapabilmeli"""
        self.client.force_login(self.admin_user)
        
        # Sporcuyu onaylı duruma getirelim
        self.athlete.status = 'approved'
        self.athlete.is_active = True
        self.athlete.save()

        search_url = reverse('dashboard-search-athletes')
        
        # Ege araması yapıldığında sporcu listede çıkmalı
        response = self.client.get(f"{search_url}?q=Ege")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ege')

        # Olmayan bir isim arandığında eşleşme çıkmamalı
        response = self.client.get(f"{search_url}?q=Ahmet")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'uygun onaylı sporcu bulunamadı')