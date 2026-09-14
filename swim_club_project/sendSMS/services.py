import requests


class TextBeeService:
    URL = "https://api.textbee.dev/api/v1/gateway/send-sms"
    DEVICE_ID = "6aa79d775625abc6b2c5fc51"
    API_KEY = "txb_xJtRMAqWRl3SfiFfaRUFZZmRmwNgc7cc"

    def __init__(self, device_id=None, api_key=None):
        self.device_id = device_id or self.DEVICE_ID
        self.api_key = api_key or self.API_KEY

    def send(self, recipients, message):
        recipient_list = [recipients] if isinstance(recipients, str) else list(recipients)
        payload = {
            "deviceId": self.device_id,
            "recipients": recipient_list,
            "message": message,
        }

        try:
            response = requests.post(
                self.URL,
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data.get("data", response_data)
        except requests.exceptions.HTTPError as error:
            try:
                details = error.response.json()
            except (AttributeError, ValueError):
                details = error.response.text if error.response is not None else str(error)
            return {"status": "error", "message": "TextBee API hatası", "details": details}
        except (requests.exceptions.RequestException, ValueError) as error:
            return {"status": "error", "message": str(error)}


_sms_service = None


def get_sms_service():
    global _sms_service
    if _sms_service is None:
        _sms_service = TextBeeService()
    return _sms_service


# Eski çağrıları bozmamak için geçici uyumluluk adı.
IletiMerkeziService = TextBeeService
