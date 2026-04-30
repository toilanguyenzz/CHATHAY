import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv(".env")

url = f"{os.getenv('SUPABASE_URL')}/rest/v1/zalo_tokens"
headers = {
    'apikey': os.getenv('SUPABASE_KEY'),
    'Authorization': f"Bearer {os.getenv('SUPABASE_KEY')}"
}

req = urllib.request.Request(url, headers=headers)
try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except Exception as e:
    print("ERROR:", e)
