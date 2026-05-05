"""Coin Service — Quản lý ví Coin và giao dịch."""

import logging
from typing import Optional, Dict, Any
from services.db_service import (
    get_supabase_client,
)

logger = logging.getLogger(__name__)

# Coin rewards
QUIZ_COMPLETE_REWARD = 50
STREAK_7_REWARD = 100
STREAK_30_REWARD = 500
SHARE_REWARD = 20
FILE_PROCESS_COST = 10

# Coin packages
COIN_PACKAGES = {
    'trial': {'price': 5000, 'coins': 50, 'bonus': 0},
    'save': {'price': 15000, 'coins': 180, 'bonus': 20},
    'vip_week': {'price': 35000, 'coins': 500, 'bonus': 40},
}

# In-memory fallback for when Supabase is unavailable
_memory_coin_balance: Dict[str, int] = {}


async def get_coin_balance(user_id: str) -> int:
    """Lấy số dư Coin của user."""
    try:
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table('user_coin_balance').select('balance').eq('user_id', user_id).single().execute()
            if result.data:
                return result.data.get('balance', 0)
            else:
                # Create record if not exists
                supabase.table('user_coin_balance').insert({'user_id': user_id, 'balance': 0}).execute()
                return 0
        else:
            # Memory fallback
            return _memory_coin_balance.get(user_id, 0)
    except Exception as e:
        logger.error("Get coin balance error: %s", e)
        return _memory_coin_balance.get(user_id, 0)


async def add_coins(user_id: str, amount: int, reason: str = 'reward', metadata: Optional[Dict[str, Any]] = None) -> int:
    """Cộng Coin vào ví user. Trả về số dư mới."""
    try:
        supabase = get_supabase_client()
        if supabase:
            # Use database function if available, otherwise direct update
            try:
                # Try to use SQL function for atomic operation
                result = supabase.rpc('add_coins_transaction', {
                    'p_user_id': user_id,
                    'p_amount': amount,
                    'p_reason': reason,
                    'p_metadata': metadata or {}
                }).execute()
                if result.data:
                    return result.data
            except Exception as e:
                logger.warning("RPC not available, using direct update: %s", e)

            # Fallback: direct table update with transaction
            current = await get_coin_balance(user_id)
            new_balance = current + amount

            supabase.table('user_coin_balance').upsert({
                'user_id': user_id,
                'balance': new_balance
            }).execute()

            # Log transaction
            supabase.table('coin_transactions').insert({
                'user_id': user_id,
                'amount': amount,
                'type': 'credit',
                'reason': reason,
                'balance_after': new_balance,
                'metadata': metadata or {}
            }).execute()

            logger.info("✅ Added %s coins to user %s (reason: %s). New balance: %s",
                        amount, user_id[:8], reason, new_balance)
            return new_balance
        else:
            # Memory fallback
            current = _memory_coin_balance.get(user_id, 0)
            new_balance = current + amount
            _memory_coin_balance[user_id] = new_balance
            logger.info("✅ Added %s coins (memory) to user %s. New balance: %s",
                        amount, user_id[:8], new_balance)
            return new_balance
    except Exception as e:
        logger.error("Add coins error: %s", e)
        return await get_coin_balance(user_id)


async def spend_coins(user_id: str, amount: int, reason: str = 'spend', metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Trừ Coin. Trả về True nếu thành công."""
    try:
        supabase = get_supabase_client()
        if supabase:
            try:
                # Try to use SQL function for atomic operation
                result = supabase.rpc('spend_coins_transaction', {
                    'p_user_id': user_id,
                    'p_amount': amount,
                    'p_reason': reason,
                    'p_metadata': metadata or {}
                }).execute()
                if result.data is not None:
                    return True
                return False
            except Exception as e:
                logger.warning("RPC not available, using direct update: %s", e)

            # Fallback: direct table update with check
            current = await get_coin_balance(user_id)

            if current < amount:
                logger.warning("Insufficient coins: user %s has %s, needs %s", user_id[:8], current, amount)
                return False

            new_balance = current - amount

            supabase.table('user_coin_balance').update({'balance': new_balance}).eq('user_id', user_id).execute()

            # Log transaction
            supabase.table('coin_transactions').insert({
                'user_id': user_id,
                'amount': -amount,
                'type': 'debit',
                'reason': reason,
                'balance_after': new_balance,
                'metadata': metadata or {}
            }).execute()

            logger.info("✅ Spent %s coins from user %s (reason: %s). New balance: %s",
                        amount, user_id[:8], reason, new_balance)
            return True
        else:
            # Memory fallback
            current = _memory_coin_balance.get(user_id, 0)
            if current < amount:
                return False
            _memory_coin_balance[user_id] = current - amount
            return True
    except Exception as e:
        logger.error("Spend coins error: %s", e)
        return False


async def reward_quiz_complete(user_id: str, score: int, total: int) -> int:
    """Thưởng Coin khi hoàn thành Quiz."""
    if score >= total * 0.7:  # 70% correct
        return await add_coins(user_id, QUIZ_COMPLETE_REWARD, 'quiz_complete', {'score': score, 'total': total})
    return 0


async def reward_streak(user_id: str, streak_count: int) -> int:
    """Thưởng Coin khi đạt cột mốc Streak."""
    if streak_count == 7:
        return await add_coins(user_id, STREAK_7_REWARD, 'streak_7', {'streak': streak_count})
    elif streak_count == 30:
        return await add_coins(user_id, STREAK_30_REWARD, 'streak_30', {'streak': streak_count})
    return 0


async def reward_share(user_id: str) -> int:
    """Thưởng Coin khi share kết quả."""
    return await add_coins(user_id, SHARE_REWARD, 'share')


async def get_transaction_history(user_id: str, limit: int = 20):
    """Lấy lịch sử giao dịch Coin."""
    try:
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table('coin_transactions').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
            return result.data or []
        return []
    except Exception as e:
        logger.error("Get transactions error: %s", e)
        return []
