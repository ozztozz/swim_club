# athletes/tests/test_athletes.py
import datetime
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from athletes.models import Athlete

User = get_user_model()

class AthleteModuleTests(APITestCase):

    def setUp(self):
        # 1. Kullanıcılar (User Testi ve İlişkilendirme İçin)
        self.parent1 = User.objects.create_user(
            username='veli1',
            email='veli1@example.com',
            password='Password123!',
            first_name='Ahmet',
            last_name='Yılmaz',
            role=User.Role.PARENT
        )
        self.parent2 = User.objects.create_user(
            username='veli2',
            email='veli2@example.com',
            password='Password123!',
            first_name='Mehmet',
            last_name='Kaya',
            role=User.Role.PARENT
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123!',
            role=User.Role.ADMIN
        )

        # 2. Sporcular
        self.athlete1 = Athlete.objects.create(
            parent=self.parent1,
            first_name='Can',
            last_name='Yılmaz',
            tc_identity='11111111111',
            birth_date=datetime.date(2012, 5, 10),
            gender='M',
            school='Atatürk İlkokulu',
            joined_date=datetime.date(2023, 1, 15)
        )
        self.athlete2 = Athlete.objects.create(
            parent=self.parent2,
            first_name='Zeynep',
            last_name='Kaya',
            tc_identity='22222222222',
            birth_date=datetime.date(2014, 8, 20),
            gender='F',
            school='Cumhuriyet Ortaokulu',
            joined_date=datetime.date(2023, 6, 1)
        )

        self.athlete_list_url = reverse('athlete-list')

    # --- MODEL & USER İLİŞKİ TESTLERİ ---

    def test_athlete_creation_and_user_relation(self):
        """Sporcu modeli doğru oluşturuluyor mu ve User (Veli) ilişkisi çalışıyor mu?"""
        self.assertEqual(self.athlete1.parent.get_full_name(), 'Ahmet Yılmaz')
        
        # Model __str__ metodu 'Ad Soyad (Durum)' döndüğü için kontrolü güncelliyoruz
        self.assertEqual(str(self.athlete1), 'Can Yılmaz (Onay Bekliyor)')
        
        # Veli üzerinden sporcularına erişim (related_name='athletes')
        self.assertIn(self.athlete1, self.parent1.athletes.all())
        self.assertNotIn(self.athlete2, self.parent1.athletes.all())

    # --- API & YETKİLENDİRME TESTLERİ ---

    def test_parent_can_only_see_own_athletes(self):
        """Veli1 giriş yaptığında SADECE kendi çocuğu Can'ı görebilmeli, Zeynep'i görmemeli"""
        self.client.force_authenticate(user=self.parent1)
        response = self.client.get(self.athlete_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['first_name'], 'Can')

    def test_admin_can_see_all_athletes(self):
        """Yönetici giriş yaptığında TÜM sporcuları görebilmeli"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.athlete_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_parent_creates_athlete_auto_assigns_parent(self):
        """Veli yeni sporcu oluşturduğunda parent otomatik kendisi atanıyor mu?"""
        self.client.force_authenticate(user=self.parent1)
        data = {
            'first_name': 'Efe',
            'last_name': 'Yılmaz',
            'tc_identity': '33333333333',
            'birth_date': '2016-03-12',
            'gender': 'M',
            'school': 'Güneş Anaokulu',
            'joined_date': '2024-01-01'
        }
        response = self.client.post(self.athlete_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_athlete = Athlete.objects.get(id=response.data['id'])
        self.assertEqual(new_athlete.parent, self.parent1)

        def test_admin_can_approve_athlete(self):
            """Yönetici onay bekleyen sporcuyu onaylayabiliyor mu?"""
            self.client.force_authenticate(user=self.admin_user)
            approve_url = reverse('athlete-approve', kwargs={'pk': self.athlete1.pk})
            
            response = self.client.post(approve_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            self.athlete1.refresh_from_db()
            self.assertEqual(self.athlete1.status, 'approved')
            self.assertTrue(self.athlete1.is_active)

        def test_parent_cannot_approve_athlete(self):
            """Veli kendi çocuğunu veya başka sporcuyu onaylayamamalı (403 dönmeli)"""
            self.client.force_authenticate(user=self.parent1)
            approve_url = reverse('athlete-approve', kwargs={'pk': self.athlete1.pk})
            
            response = self.client.post(approve_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)