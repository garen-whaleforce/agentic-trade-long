#!/usr/bin/env python3
"""
P0-1 風險邏輯驗證：確認 risk 判斷在修正後能正常工作
"""

import os
os.environ["RISK_EARNINGS_DAY_LOW"] = "-3"
os.environ["RISK_PRE_RUNUP_HIGH"] = "15"

from agentic_rag_bridge import validate_market_anchors


def _compute_risk_from_anchors(anchors):
    """簡化版本的 risk 計算（複製自 agentic_rag_bridge.py）"""
    if not anchors:
        return "medium"

    eps_surprise = anchors.get("eps_surprise")
    earnings_day_return = anchors.get("earnings_day_return")
    pre_earnings_5d_return = anchors.get("pre_earnings_5d_return")

    RISK_EPS_MISS_THRESHOLD = 0
    RISK_EARNINGS_DAY_LOW = -3
    RISK_PRE_RUNUP_HIGH = 15
    RISK_PRE_RUNUP_LOW = 5

    # High risk conditions (any triggers HIGH)
    if eps_surprise is not None and eps_surprise <= RISK_EPS_MISS_THRESHOLD:
        return "high"
    if earnings_day_return is not None and earnings_day_return < RISK_EARNINGS_DAY_LOW:
        return "high"
    if pre_earnings_5d_return is not None and pre_earnings_5d_return > RISK_PRE_RUNUP_HIGH:
        return "high"

    # Low risk conditions (all must be true)
    eps_ok = eps_surprise is None or eps_surprise > 0
    day_ok = earnings_day_return is None or earnings_day_return > 0
    runup_low = pre_earnings_5d_return is None or pre_earnings_5d_return < RISK_PRE_RUNUP_LOW

    if eps_ok and day_ok and runup_low:
        return "low"

    return "medium"


def test_risk_logic():
    """測試修正後的 risk 判斷邏輯"""

    print("=" * 80)
    print("P0-1 風險邏輯驗證")
    print("=" * 80)
    print()
    print("閾值設定:")
    print("  RISK_EARNINGS_DAY_LOW = -3%")
    print("  RISK_PRE_RUNUP_HIGH = 15%")
    print("=" * 80)
    print()

    test_cases = [
        {
            "name": "應判斷為 HIGH - earnings_day_return -5% (< -3%)",
            "anchors": {
                "eps_surprise": 0.08,
                "earnings_day_return": -5.0,  # -5% < -3%
                "pre_earnings_5d_return": 3.0,
            },
            "expected_risk": "high",
        },
        {
            "name": "應判斷為 HIGH - pre_earnings_5d_return +20% (> 15%)",
            "anchors": {
                "eps_surprise": 0.10,
                "earnings_day_return": 2.0,
                "pre_earnings_5d_return": 20.0,  # +20% > 15%
            },
            "expected_risk": "high",
        },
        {
            "name": "應判斷為 HIGH - eps miss",
            "anchors": {
                "eps_surprise": -0.05,  # miss
                "earnings_day_return": 2.0,
                "pre_earnings_5d_return": 3.0,
            },
            "expected_risk": "high",
        },
        {
            "name": "應判斷為 LOW - 所有條件良好",
            "anchors": {
                "eps_surprise": 0.10,  # beat
                "earnings_day_return": 3.0,  # +3% > 0
                "pre_earnings_5d_return": 2.0,  # +2% < 5%
            },
            "expected_risk": "low",
        },
        {
            "name": "應判斷為 MEDIUM - earnings_day_return -2% (邊界內)",
            "anchors": {
                "eps_surprise": 0.08,
                "earnings_day_return": -2.0,  # -2% > -3%
                "pre_earnings_5d_return": 8.0,  # 5% < 8% < 15%
            },
            "expected_risk": "medium",
        },
        {
            "name": "應判斷為 MEDIUM - pre_earnings_5d_return +12% (邊界內)",
            "anchors": {
                "eps_surprise": 0.05,
                "earnings_day_return": 1.0,
                "pre_earnings_5d_return": 12.0,  # 5% < 12% < 15%
            },
            "expected_risk": "medium",
        },
    ]

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n測試 {i}: {test_case['name']}")
        print("-" * 80)

        # 先驗證 market_anchors
        validated = validate_market_anchors(test_case["anchors"])

        # 計算 risk
        risk = _compute_risk_from_anchors(validated)

        print(f"Market Anchors (已驗證):")
        print(f"  eps_surprise: {validated.get('eps_surprise')}")
        print(f"  earnings_day_return: {validated.get('earnings_day_return')}%")
        print(f"  pre_earnings_5d_return: {validated.get('pre_earnings_5d_return')}%")

        print(f"\n計算結果: risk = '{risk}'")
        print(f"預期結果: risk = '{test_case['expected_risk']}'")

        if risk == test_case["expected_risk"]:
            print("\n✅ 通過")
            passed += 1
        else:
            print(f"\n❌ 失敗: 期望 '{test_case['expected_risk']}', 實際 '{risk}'")
            failed += 1

    print("\n" + "=" * 80)
    print(f"測試結果: {passed} 通過, {failed} 失敗")
    print("=" * 80)
    print()

    if failed == 0:
        print("✅ P0-1 風險邏輯修正成功！")
        print()
        print("修正前的問題:")
        print("  - earnings_day_return 6% 會被截斷為 1.0")
        print("  - pre_earnings_5d_return 12% 會被截斷為 0.5")
        print("  - 導致 risk 判斷永遠無法觸發 HIGH")
        print()
        print("修正後:")
        print("  - earnings_day_return 和 pre_earnings_5d_return 使用百分點制")
        print("  - risk 判斷能正確觸發 HIGH/MEDIUM/LOW")
    else:
        print("❌ 仍有失敗的測試，需要進一步檢查")

    return failed == 0


if __name__ == "__main__":
    success = test_risk_logic()
    exit(0 if success else 1)
