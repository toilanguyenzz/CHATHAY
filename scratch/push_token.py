import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv(".env")

url = f"{os.getenv('SUPABASE_URL')}/rest/v1/zalo_tokens"
headers = {
    'apikey': os.getenv('SUPABASE_KEY'),
    'Authorization': f"Bearer {os.getenv('SUPABASE_KEY')}",
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates'
}

data = [
    {'key': 'zalo_access_token', 'value': os.getenv('ZALO_OA_ACCESS_TOKEN')},
    {'key': 'zalo_refresh_token', 'value': os.getenv('ZALO_REFRESH_TOKEN')}
]

req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
try:
    res = urllib.request.urlopen(req)
    print("STATUS:", res.status)
except Exception as e:
    print("ERROR:", e)
