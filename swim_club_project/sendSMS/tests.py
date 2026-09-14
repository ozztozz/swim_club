from unittest.mock import Mock, patch

import requests
from django.test import TestCase

from .services import TextBeeService


class TextBeeServiceTests(TestCase):
    @patch("sendSMS.services.requests.post")
    def test_send_posts_textbee_payload(self, post):
        response = Mock()
        response.json.return_value = {
            "data": {"smsBatchId": "batch-123", "recipientCount": 1}
        }
        post.return_value = response

        result = TextBeeService("device-123", "api-key").send(
            "+90 530 244 26 70", "Antrenman bugün 18:00"
        )

        self.assertEqual(result["smsBatchId"], "batch-123")
        post.assert_called_once_with(
            "https://api.textbee.dev/api/v1/gateway/send-sms",
            headers={
                "x-api-key": "api-key",
                "Content-Type": "application/json",
            },
            json={
                "deviceId": "device-123",
                "recipients": ["+90 530 244 26 70"],
                "message": "Antrenman bugün 18:00",
            },
            timeout=10,
        )

    @patch("sendSMS.services.requests.post")
    def test_send_returns_api_error_without_raising(self, post):
        response = Mock()
        response.json.return_value = {"message": "Invalid API key"}
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=response
        )
        post.return_value = response

        result = TextBeeService("device-123", "bad-key").send("5302442670", "Test")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["details"], {"message": "Invalid API key"})
