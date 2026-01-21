#!/usr/bin/env python3
"""
P0-1 驗證：測試 market_anchors 單位修正
驗證 earnings_day_return 和 pre_earnings_5d_return 的截斷是否正確
"""

from agentic_rag_bridge import validate_market_anchors


def test_unit_fix():
    """測試單位修正是否正確"""

    print("=" * 80)
    print("P0-1 驗證：Market Anchors 單位修正")
    print("=" * 80)
    print()

    test_cases = [
        {
            "name": "正常案例 - earnings_day_return +6%",
            "anchors": {
                "eps_surprise": 0.08,
                "earnings_day_return": 6.0,  # +6%
                "pre_earnings_5d_return": 3.5,  # +3.5%
            },
            "expected_earnings_day_return": 6.0,
            "expected_pre_earnings_5d_return": 3.5,
        },
        {
            "name": "正常案例 - pre_earnings_5d_return +12%",
            "anchors": {
                "eps_surprise": 0.15,
                "earnings_day_return": 4.2,  # +4.2%
                "pre_earnings_5d_return": 12.0,  # +12%
            },
            "expected_earnings_day_return": 4.2,
            "expected_pre_earnings_5d_return": 12.0,
        },
        {
            "name": "極端案例 - earnings_day_return +150% (應截斷為 100%)",
            "anchors": {
                "eps_surprise": 0.50,
                "earnings_day_return": 150.0,  # +150%
                "pre_earnings_5d_return": 5.0,
            },
            "expected_earnings_day_return": 100.0,
            "expected_pre_earnings_5d_return": 5.0,
        },
        {
            "name": "極端案例 - pre_earnings_5d_return +80% (應截斷為 50%)",
            "anchors": {
                "eps_surprise": 0.20,
                "earnings_day_return": 8.0,
                "pre_earnings_5d_return": 80.0,  # +80%
            },
            "expected_earnings_day_return": 8.0,
            "expected_pre_earnings_5d_return": 50.0,
        },
        {
            "name": "負值案例 - earnings_day_return -10%",
            "anchors": {
                "eps_surprise": -0.05,
                "earnings_day_return": -10.0,  # -10%
                "pre_earnings_5d_return": 2.0,
            },
            "expected_earnings_day_return": -10.0,
            "expected_pre_earnings_5d_return": 2.0,
        },
        {
            "name": "極端負值 - earnings_day_return -80% (應截斷為 -50%)",
            "anchors": {
                "eps_surprise": -0.30,
                "earnings_day_return": -80.0,  # -80%
                "pre_earnings_5d_return": 1.0,
            },
            "expected_earnings_day_return": -50.0,
            "expected_pre_earnings_5d_return": 1.0,
        },
    ]

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n測試 {i}: {test_case['name']}")
        print("-" * 80)

        # 執行驗證
        validated = validate_market_anchors(test_case["anchors"])

        # 檢查結果
        earnings_day_return = validated.get("earnings_day_return")
        pre_earnings_5d_return = validated.get("pre_earnings_5d_return")

        print(f"輸入:")
        print(f"  earnings_day_return: {test_case['anchors'].get('earnings_day_return')}")
        print(f"  pre_earnings_5d_return: {test_case['anchors'].get('pre_earnings_5d_return')}")

        print(f"\n輸出:")
        print(f"  earnings_day_return: {earnings_day_return}")
        print(f"  pre_earnings_5d_return: {pre_earnings_5d_return}")

        print(f"\n預期:")
        print(f"  earnings_day_return: {test_case['expected_earnings_day_return']}")
        print(f"  pre_earnings_5d_return: {test_case['expected_pre_earnings_5d_return']}")

        # 驗證
        earnings_match = earnings_day_return == test_case["expected_earnings_day_return"]
        pre_earnings_match = pre_earnings_5d_return == test_case["expected_pre_earnings_5d_return"]

        if earnings_match and pre_earnings_match:
            print("\n✅ 通過")
            passed += 1
        else:
            print("\n❌ 失敗")
            if not earnings_match:
                print(f"  earnings_day_return 不符: {earnings_day_return} != {test_case['expected_earnings_day_return']}")
            if not pre_earnings_match:
                print(f"  pre_earnings_5d_return 不符: {pre_earnings_5d_return} != {test_case['expected_pre_earnings_5d_return']}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"測試結果: {passed} 通過, {failed} 失敗")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = test_unit_fix()
    exit(0 if success else 1)
