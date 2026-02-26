import requests
import time
import hmac
import hashlib
import json

from src.core.config.settings import settings

def build_payload() -> dict:
    return {
        "object": "instagram",
        "entry": [
            {
                "time": int(time.time() * 1000),
                "id": settings.instagram.page_id,
                "messaging": [
                    {
                        "sender": {
                            "id": settings.instagram.user_id
                        },
                        "recipient": {
                            "id": settings.instagram.page_id
                        },
                        "timestamp": int(time.time() * 1000),
                        "message": {
                            "mid": f"mid.$cAxbO29mJ70r5H4p6q8s9t0u1v2w3x4y5z",
                            "text": "Olá! Como posso te ajudar hoje?"
                        }
                    }
                ]
            }
        ]
    }

def calculate_signature(payload_str: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def main() -> None:
    url = "http://localhost:8000/webhook"
    payload = build_payload()
    
    # É crucial usar a mesma string para o cálculo e para o envio
    # O Instagram usa separators=(',', ':') por padrão no JSON compacto
    payload_str = json.dumps(payload, separators=(',', ':'))
    
    app_secret = settings.instagram.app_secret
    if not app_secret:
        print("Erro: INSTAGRAM_APP_SECRET não configurado.")
        return

    signature = calculate_signature(payload_str, app_secret)
    
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature
    }
    
    response = requests.post(url, data=payload_str, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    main()
