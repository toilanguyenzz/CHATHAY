#!/usr/bin/env python3
"""Unit tests for db_service — Study Mode limit & usage tracking"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import db_service as dbs
import time

def test_check_study_mode_limit():
    """Test check_study_mode_limit default (should allow 3 free/day)."""
    user_id = 999
    # Initially no usage -> should allow
    assert dbs.check_study_mode_limit(user_id) is True

def test_increment_study_mode_usage():
    """Test increment and check limit."""
    user_id = 998
    today = time.strftime("%Y-%m-%d")

    # Reset state
    dbs._memory_usage.pop(user_id, None)

    # First increment
    dbs.increment_study_mode_usage(user_id)
    assert dbs.check_study_mode_limit(user_id) is True  # Still under limit (3)

    # Simulate hitting limit (need 3 to hit, 4 to exceed)
    # config.FREE_STUDY_SESSIONS_PER_DAY default = 3
    dbs.increment_study_mode_usage(user_id)
    dbs.increment_study_mode_usage(user_id)
    # Now count = 3 -> limit reached, check returns False
    assert dbs.check_study_mode_limit(user_id) is False

    # Cleanup
    dbs._memory_usage.pop(user_id, None)

def test_study_count_isolated_from_qa_count():
    """Ensure study_count is separate from other counters."""
    user_id = 997
    dbs._memory_usage.pop(user_id, None)

    # Increment study usage 3 times
    for _ in range(3):
        dbs.increment_study_mode_usage(user_id)

    # Should be at limit
    assert dbs.check_study_mode_limit(user_id) is False

    # Reset for next user
    dbs._memory_usage.pop(user_id, None)

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    tests = [
        test_check_study_mode_limit,
        test_increment_study_mode_usage,
        test_study_count_isolated_from_qa_count,
    ]

    passed = 0
    for test in tests:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
