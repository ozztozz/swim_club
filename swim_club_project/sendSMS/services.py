import requests


class IletiMerkeziService:
    URL = "https://api.iletimerkezi.com/v1/send-sms/json"
    API_KEY = "c7c2d5489ef3637453b4c8d3b68f02ed"
    API_HASH = "6bd23b5b40734398c543e334a98101363a5e5d2d447592df89950a3c3ae3700d"
    SENDER = "APITEST"
    IYS = "1"
    IYS_LIST = "BIREYSEL"

    @classmethod
    def send_sms(cls, phone, message):
        phone = str(phone).strip().replace(" ", "").replace("-", "")
        if phone.startswith("+90"):
            phone = phone[3:]
        elif phone.startswith("90"):
            phone = phone[2:]
        elif phone.startswith("0"):
            phone = phone[1:]

        payload = {
            "request": {
                "authentication": {"key": cls.API_KEY, "hash": cls.API_HASH},
                "order": {
                    "sender": cls.SENDER,
                    "sendDateTime": [],
                    "iys": cls.IYS,
                    "iysList": cls.IYS_LIST,
                    "message": {
                        "text": message,
                        "receipents": {"number": [phone]},
                    },
                },
            }
        }

        try:
            response = requests.post(cls.URL, json=payload, timeout=10)
            response_data = response.json()
            response_body = response_data.get("request", {}).get("response")
            if not isinstance(response_body, dict):
                response_body = response_data.get("response", response_data)

            status = response_body.get("status", {})
            if not isinstance(status, dict):
                status = {}
            status_code = status.get("code")

            if str(status_code) == "200":
                return {
                    "status": "success",
                    "id": response_body.get("order", {}).get("id"),
                }

            return {
                "status": "error",
                "code": status_code,
                "message": (
                    status.get("message")
                    or response_data.get("error")
                    or response_data.get("message")
                    or "Bilinmeyen Hata"
                ),
                "response": response_data,
            }
        except ValueError:
            return {"status": "error", "message": "API geçerli bir JSON yanıtı döndürmedi."}
        except requests.exceptions.RequestException as error:
            return {"status": "error", "message": str(error)}
