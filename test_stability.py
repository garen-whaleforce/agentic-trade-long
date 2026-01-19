#!/usr/bin/env python3
"""測試 gpt-5-mini 的結果穩定性"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ['MAIN_MODEL'] = 'gpt-5-mini'

from agentic_rag_bridge import run_single_call_from_context

# 測試案例：NVDA 2017Q1
test_case = {
    "symbol": "NVDA",
    "year": 2017,
    "quarter": 1,
    "transcript_date": None
}

print("🔬 測試 gpt-5-mini 穩定性")
print(f"案例: {test_case['symbol']} {test_case['year']}Q{test_case['quarter']}")
print("=" * 80)

results = []

for i in range(3):
    print(f"\n執行第 {i+1} 次...")
    
    try:
        result = run_single_call_from_context(test_case)
        
        # 提取關鍵資訊
        long_eligible = result.get("long_eligible_json", {})
        
        key_metrics = {
            "run": i + 1,
            "direction_score": long_eligible.get("DirectionScore", 0),
            "confidence": result.get("confidence", 0),
            "trade_long": result.get("trade_long", False),
            "tier": result.get("trade_long_tier", ""),
            "risk_code": long_eligible.get("RiskCode", ""),
            "hard_vetoes": result.get("detailed_vetoes", {}).get("hard_vetoes", []),
            "soft_vetoes": list(result.get("detailed_vetoes", {}).get("soft_vetoes", {}).keys())
        }
        
        results.append(key_metrics)
        
        print(f"  Direction Score: {key_metrics['direction_score']}")
        print(f"  Confidence: {key_metrics['confidence']}")
        print(f"  Trade Long: {key_metrics['trade_long']}")
        print(f"  Tier: {key_metrics['tier'] if key_metrics['tier'] else 'N/A'}")
        print(f"  Risk Code: {key_metrics['risk_code']}")
        
    except Exception as e:
        print(f"  ❌ 錯誤: {e}")
        results.append({"run": i + 1, "error": str(e)})

print("\n" + "=" * 80)
print("📊 結果比較")
print("=" * 80)

# 比較結果
if len(results) == 3 and all("error" not in r for r in results):
    print(f"\n{'指標':<20} {'第1次':<15} {'第2次':<15} {'第3次':<15} {'是否一致':<10}")
    print("-" * 80)
    
    # Direction Score
    ds_values = [r['direction_score'] for r in results]
    ds_consistent = len(set(ds_values)) == 1
    print(f"{'Direction Score':<20} {ds_values[0]:<15} {ds_values[1]:<15} {ds_values[2]:<15} {'✅' if ds_consistent else '❌':<10}")
    
    # Confidence
    conf_values = [r['confidence'] for r in results]
    conf_consistent = len(set(conf_values)) == 1
    print(f"{'Confidence':<20} {conf_values[0]:<15} {conf_values[1]:<15} {conf_values[2]:<15} {'✅' if conf_consistent else '❌':<10}")
    
    # Trade Long
    tl_values = [r['trade_long'] for r in results]
    tl_consistent = len(set(tl_values)) == 1
    print(f"{'Trade Long':<20} {str(tl_values[0]):<15} {str(tl_values[1]):<15} {str(tl_values[2]):<15} {'✅' if tl_consistent else '❌':<10}")
    
    # Tier
    tier_values = [r['tier'] if r['tier'] else 'N/A' for r in results]
    tier_consistent = len(set(tier_values)) == 1
    print(f"{'Tier':<20} {tier_values[0]:<15} {tier_values[1]:<15} {tier_values[2]:<15} {'✅' if tier_consistent else '❌':<10}")
    
    # Risk Code
    risk_values = [r['risk_code'] for r in results]
    risk_consistent = len(set(risk_values)) == 1
    print(f"{'Risk Code':<20} {risk_values[0]:<15} {risk_values[1]:<15} {risk_values[2]:<15} {'✅' if risk_consistent else '❌':<10}")
    
    print("\n" + "=" * 80)
    
    # 總結
    all_consistent = all([ds_consistent, conf_consistent, tl_consistent, tier_consistent, risk_consistent])
    
    if all_consistent:
        print("✅ 結論: 所有關鍵指標完全一致")
    else:
        print("❌ 結論: 存在不一致的指標")
        print("\n⚠️  可能影響:")
        if not ds_consistent:
            print("   - Direction Score 不穩定")
        if not tl_consistent:
            print("   - 交易信號不穩定 (嚴重問題)")
        if not tier_consistent:
            print("   - Tier 分類不穩定")

# 保存結果
with open("stability_test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n💾 詳細結果已保存到 stability_test_results.json")

