import os
import requests
import time
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth

def refresh_gigachat_token():
    client_id = os.getenv("GIGACHAT_CLIENT_ID")
    client_secret = os.getenv("GIGACHAT_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET must be set")

    auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

    payload = {
        "scope": "GIGACHAT_API_PERS"
    }

    auth = HTTPBasicAuth(client_id, client_secret)
    response = requests.post(auth_url, auth=auth, data=payload)
    response.raise_for_status()

    token_data = response.json()
    token = token_data["access_token"]
    expires_in = token_data["expires_at"]

    os.environ["GIGACHAT_TOKEN"] = token
    os.environ["GIGACHAT_TOKEN_EXPIRY"] = str(expires_in)

    return token

def monitor_token_expiry():
    while True:
        expiry_time = os.getenv("GIGACHAT_TOKEN_EXPIRY")
        if expiry_time:
            expiry_time = datetime.fromisoformat(expiry_time)
            current_time = datetime.now()
            if current_time >= expiry_time - timedelta(minutes=5):
                refresh_gigachat_token()
        time.sleep(300)

if __name__ == "__main__":
    monitor_token_expiry()
