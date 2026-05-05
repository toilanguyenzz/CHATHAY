"""ZaloPay Service — Tích hợp thanh toán ZaloPay."""

import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Optional
from fastapi import Request

logger = logging.getLogger(__name__)

# ZaloPay config (set in Railway Dashboard)
ZALOPAY_APP_ID = "2553"  # Test app_id
ZALOPAY_KEY1 = "PcY4rqas"  # Test key1
ZALOPAY_KEY2 = "kRPD7trq"  # Test key2
ZALOPAY_ENDPOINT = "https://sb-openapi.zalopay.vn/v2/create"
ZALOPAY_QUERY_ENDPOINT = "https://sb-openapi.zalopay.vn/v2/query"

# Coin packages mapping
COIN_PACKAGES = {
    'trial': {'price': 5000, 'coins': 50, 'bonus': 0},
    'save': {'price': 15000, 'coins': 180, 'bonus': 20},
    'vip_week': {'price': 35000, 'coins': 500, 'bonus': 40},
}


async def create_zalopay_order(user_id: str, package_id: str, redirect_url: str) -> dict:
    """Tạo đơn hàng ZaloPay."""
    if package_id not in COIN_PACKAGES:
        return {'error': 'Gói không hợp lệ'}

    pkg = COIN_PACKAGES[package_id]
    app_trans_id = f"{int(time.time())}{uuid.uuid4().hex[:6]}"

    embed_data = json.dumps({
        'redirecturl': redirect_url or 'https://zalo.me/your_oa_id',
    })

    items = json.dumps([{
        'itemid': package_id,
        'itemname': f"CHAT HAY - {pkg['coins'] + pkg['bonus']} Coin",
        'itemprice': pkg['price'],
        'itemquantity': 1,
    }])

    order = {
        'appid': int(ZALOPAY_APP_ID),
        'apptransid': app_trans_id,
        'appuser': user_id,
        'apptime': int(time.time()),
        'item': items,
        'embeddata': embed_data,
        'amount': pkg['price'],
        'description': f"Nạp {pkg['coins'] + pkg['bonus']} Coin - CHAT HAY",
        'bankcode': '',
    }

    # Generate MAC signature
    data_str = f"{order['appid']}|{order['apptransid']}|{order['appuser']}|{order['amount']}|{order['apptime']}|{order['embeddata']}|{order['item']}|{ZALOPAY_KEY1}"
    mac = hmac.new(ZALOPAY_KEY2.encode(), data_str.encode(), hashlib.sha256).hexdigest()
    order['mac'] = mac

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(ZALOPAY_ENDPOINT, json=order)
            result = resp.json()

            if result.get('returncode') == 1:
                return {
                    'order_url': result.get('orderurl'),
                    'zp_trans_token': result.get('zptranstoken'),
                    'app_trans_id': app_trans_id,
                    'package_id': package_id,
                }
            else:
                logger.error("ZaloPay create order failed: %s", result)
                return {'error': result.get('returnmessage', 'Tạo đơn hàng thất bại')}
    except Exception as e:
        logger.error("ZaloPay create order error: %s", e)
        return {'error': 'Lỗi kết nối ZaloPay'}


async def verify_zalopay_callback(request: Request) -> dict:
    """Xử lý callback từ ZaloPay."""
    try:
        body = await request.json()
        data = body.get('data', '{}')
        mac_from_zalopay = body.get('mac', '')

        # Verify MAC
        mac_str = f"{data}{ZALOPAY_KEY2}"
        expected_mac = hmac.new(ZALOPAY_KEY2.encode(), mac_str.encode(), hashlib.sha256).hexdigest()

        if mac_from_zalopay != expected_mac:
            logger.error("ZaloPay callback MAC mismatch!")
            return {'error': 'Invalid MAC'}

        # Parse data
        payment_data = json.loads(data)
        app_trans_id = payment_data.get('apptransid')
        user_id = payment_data.get('appuser')
        amount = payment_data.get('amount')
        status = payment_data.get('status')  # 1 = success

        if status != 1:
            logger.warning("ZaloPay payment not successful: %s", status)
            return {'error': 'Payment not successful'}

        # Add coins to user
        from services.coin_service import add_coins
        from services.db_service import get_supabase_client

        # Determine package from amount
        pkg = None
        for pid, pdata in COIN_PACKAGES.items():
            if pdata['price'] == amount:
                pkg = (pid, pdata)
                break

        if not pkg:
            logger.error("Unknown package for amount: %s", amount)
            return {'error': 'Unknown package'}

        pid, pdata = pkg
        total_coins = pdata['coins'] + pdata['bonus']
        new_balance = await add_coins(user_id, total_coins, f'zalopay_{pid}')

        logger.info("✅ ZaloPay payment success: user=%s, coins=%s, new_balance=%s",
                    user_id[:8], total_coins, new_balance)

        return {'success': True, 'coins_added': total_coins, 'new_balance': new_balance}

    except Exception as e:
        logger.error("ZaloPay callback error: %s", e)
        return {'error': str(e)}
