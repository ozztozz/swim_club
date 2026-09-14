from unittest.mock import Mock, patch

from django.test import TestCase

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
