import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")
token = os.getenv("ZALO_OA_ACCESS_TOKEN")

res = requests.get(
    "https://openapi.zalo.me/v2.0/oa/getprofile?data={\"user_id\":\"6936318033006018164\"}",
    headers={"access_token": token}
)
print("STATUS:", res.status_code)
print("TEXT:", res.text)
