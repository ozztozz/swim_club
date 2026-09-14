from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .services import IletiMerkeziService


class IletiMerkeziServiceTests(TestCase):
    @patch("sendSMS.services.requests.post")
    def test_send_sms_posts_iletimerkezi_payload(self, post):
        response = Mock()
        response.json.return_value = {
            "request": {
                "response": {
                    "status": {"code": "200"},
                    "order": {"id": "order-123"},
                }
            }
        }
        post.return_value = response

        result = IletiMerkeziService.send_sms(
            "+90 530 244 26 70", "Antrenman bugün 18:00"
        )

        self.assertEqual(result, {"status": "success", "id": "order-123"})
        post.assert_called_once_with(
            "https://api.iletimerkezi.com/v1/send-sms/json",
            json={
                "request": {
                    "authentication": {
                        "key": IletiMerkeziService.API_KEY,
                        "hash": IletiMerkeziService.API_HASH,
                    },
                    "order": {
                        "sender": "APITEST",
                        "sendDateTime": [],
                        "iys": "1",
                        "iysList": "BIREYSEL",
                        "message": {
                            "text": "Antrenman bugün 18:00",
                            "receipents": {"number": ["5302442670"]},
                        },
                    },
                }
            },
            timeout=10,
        )

    @patch("sendSMS.services.requests.post")
    def test_send_sms_returns_api_error(self, post):
        response = Mock()
        response.json.return_value = {
            "response": {
                "status": {"code": 450, "message": "Gönderilen başlık kullanıma uygun değil"}
            }
        }
        post.return_value = response

        result = IletiMerkeziService.send_sms("5302442670", "Test")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], 450)
        self.assertEqual(result["message"], "Gönderilen başlık kullanıma uygun değil")


class SendSmsViewTests(TestCase):
    def test_send_view_returns_unpaid_athletes_as_json(self):
        user = get_user_model().objects.create_user(
            username="sms-view-user",
            password="test-password",
        )
        team = SimpleNamespace(name="A Takımı")
        athlete = SimpleNamespace(
            pk=12,
            team_id=3,
            team=team,
            parent_phone="05321234567",
            parent_email="veli@example.com",
            amount=1500,
            due_date=date(2026, 9, 15),
            payment_status="pending",
            regular_payment_day=1,
            get_full_name=lambda: "Ahmet Yılmaz",
        )

        self.client.force_login(user)
        with patch(
            "sendSMS.views.get_or_create_monthly_payments",
            return_value=[athlete],
        ), patch(
            "sendSMS.views.IletiMerkeziService.send_sms",
            return_value={"status": "success", "id": "order-456"},
        ) as send_sms:
            response = self.client.get(
                reverse("send-sms"),
                {"period": "2026-09", "team": "3"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["athletes"][0]["name"], "Ahmet Yılmaz")
        self.assertEqual(data["athletes"][0]["amount"], 1500.0)
        self.assertEqual(data["athletes"][0]["sms_status"], "success")
        self.assertEqual(data["athletes"][0]["sms_id"], "order-456")
        send_sms.assert_called_once_with(
            "05321234567",
            "Sayın velimiz, sporcumuz Ahmet Yılmaz 2026-09 aidatı "
            "(1500.00 TL) ödenmemiş görünmektedir. Ödeme yaptıysanız "
            "bu mesajı dikkate almayınız. Alpha Academy",
        )
