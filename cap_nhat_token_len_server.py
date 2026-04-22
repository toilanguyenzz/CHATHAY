import os
import requests
from dotenv import load_dotenv

# Load env file locally
load_dotenv()

APP_SECRET = os.getenv("ZALO_APP_SECRET")
NEW_ACCESS_TOKEN = os.getenv("ZALO_OA_ACCESS_TOKEN")
NEW_REFRESH_TOKEN = os.getenv("ZALO_REFRESH_TOKEN")

# API endpoint trên server Railway của bạn
RAILWAY_URL = "https://chathay-production.up.railway.app"
API_ENDPOINT = f"{RAILWAY_URL}/api/update-tokens"

print("Pushing token to " + RAILWAY_URL)

try:
    response = requests.post(
        API_ENDPOINT,
        json={
            "secret": APP_SECRET,
            "access_token": NEW_ACCESS_TOKEN,
            "refresh_token": NEW_REFRESH_TOKEN
        },
        timeout=10
    )
    
    if response.status_code == 200:
        print("SUCCESS! Tokens updated remotely.")
        print(response.json())
    else:
        print("FAIL! Code " + str(response.status_code))
        print(response.text)
except Exception as e:
    print("Error: " + str(e))
