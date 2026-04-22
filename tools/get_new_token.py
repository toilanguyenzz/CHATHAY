"""Lấy Zalo OA token mới qua OAuth authorization code.

Hướng dẫn:
1. Vào https://developers.zalo.me/app/{APP_ID}/oa/settings
2. Click "Lấy mã xác thực" (Get Authorization Code) 
3. Copy Authorization Code
4. Chạy script này: python tools/get_new_token.py <AUTH_CODE>
5. Script sẽ tự động:
   - Đổi auth code thành access_token + refresh_token
   - Lưu vào file .env
   - Push lên Railway server
"""

import os
import sys
import requests
from dotenv import load_dotenv, set_key

# Load env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

APP_ID = os.getenv("ZALO_APP_ID", "1534343952928885811")
APP_SECRET = os.getenv("ZALO_APP_SECRET", "")
RAILWAY_URL = "https://chathay-production.up.railway.app"


def exchange_auth_code(auth_code: str) -> dict:
    """Đổi authorization code thành access_token + refresh_token."""
    print(f"\n🔑 Đổi auth code → tokens...")
    resp = requests.post(
        "https://oauth.zaloapp.com/v4/oa/access_token",
        headers={"secret_key": APP_SECRET},
        data={
            "app_id": APP_ID,
            "code": auth_code,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    data = resp.json()
    
    if "access_token" not in data:
        print(f"❌ Lỗi: {data}")
        return {}
    
    print(f"✅ Lấy được token!")
    print(f"   Access token: ...{data['access_token'][-8:]}")
    print(f"   Refresh token: ...{data.get('refresh_token', 'N/A')[-8:]}")
    return data


def refresh_existing_token(refresh_token: str) -> dict:
    """Refresh token bằng refresh_token hiện có."""
    print(f"\n🔄 Refreshing token...")
    resp = requests.post(
        "https://oauth.zaloapp.com/v4/oa/access_token",
        headers={"secret_key": APP_SECRET},
        data={
            "app_id": APP_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    data = resp.json()
    
    if "access_token" not in data:
        print(f"❌ Refresh thất bại: {data}")
        return {}
    
    print(f"✅ Refresh thành công!")
    print(f"   Access token: ...{data['access_token'][-8:]}")
    print(f"   Refresh token: ...{data.get('refresh_token', 'N/A')[-8:]}")
    return data


def save_to_env(access_token: str, refresh_token: str):
    """Lưu token vào .env file."""
    set_key(env_path, "ZALO_OA_ACCESS_TOKEN", access_token)
    set_key(env_path, "ZALO_REFRESH_TOKEN", refresh_token)
    print(f"\n💾 Đã lưu vào {env_path}")


def push_to_railway(access_token: str, refresh_token: str):
    """Push token lên Railway server."""
    print(f"\n🚀 Pushing lên Railway ({RAILWAY_URL})...")
    try:
        resp = requests.post(
            f"{RAILWAY_URL}/api/update-tokens",
            json={
                "secret": APP_SECRET,
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"✅ Railway updated thành công!")
            print(f"   Response: {resp.json()}")
        else:
            print(f"❌ Railway failed (HTTP {resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Không kết nối được Railway: {e}")


def main():
    if not APP_SECRET:
        print("❌ Thiếu ZALO_APP_SECRET trong .env!")
        return

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python tools/get_new_token.py <AUTH_CODE>      # Đổi auth code mới")
        print("  python tools/get_new_token.py --refresh        # Refresh token hiện có")
        return

    if sys.argv[1] == "--refresh":
        refresh_token = os.getenv("ZALO_REFRESH_TOKEN", "")
        if not refresh_token:
            print("❌ Không tìm thấy ZALO_REFRESH_TOKEN trong .env!")
            return
        data = refresh_existing_token(refresh_token)
    else:
        auth_code = sys.argv[1]
        data = exchange_auth_code(auth_code)

    if not data:
        return

    access_token = data["access_token"]
    refresh_token = data.get("refresh_token", "")

    # Lưu vào .env
    save_to_env(access_token, refresh_token)

    # Push lên Railway
    push_to_railway(access_token, refresh_token)

    print("\n✅ DONE! Bot sẽ tự hoạt động ngay bây giờ.")


if __name__ == "__main__":
    main()
