#!/usr/bin/env python3
"""測試邊界值案例的穩定性"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ['MAIN_MODEL'] = 'gpt-5-mini'

from agentic_rag_bridge import run_single_call_from_context

# 測試案例：WMT 2017Q1 (之前顯示 D7)
test_case = {
    "symbol": "WMT",
    "year": 2017,
    "quarter": 1,
    "transcript_date": None
}

print("🔬 測試邊界值案例穩定性")
print(f"案例: {test_case['symbol']} {test_case['year']}Q{test_case['quarter']} (之前結果: D7)")
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
        }
        
        results.append(key_metrics)
        
        print(f"  Direction Score: {key_metrics['direction_score']}")
        print(f"  Trade Long: {key_metrics['trade_long']}")
        print(f"  Tier: {key_metrics['tier'] if key_metrics['tier'] else 'N/A'}")
        
    except Exception as e:
        print(f"  ❌ 錯誤: {e}")
        results.append({"run": i + 1, "error": str(e)})

print("\n" + "=" * 80)
print("📊 結果比較")
print("=" * 80)

if len(results) == 3 and all("error" not in r for r in results):
    ds_values = [r['direction_score'] for r in results]
    tl_values = [r['trade_long'] for r in results]
    tier_values = [r['tier'] if r['tier'] else 'N/A' for r in results]
    
    print(f"\n執行      Direction   Trade Long   Tier")
    print("-" * 50)
    for r in results:
        tier_str = r['tier'] if r['tier'] else 'N/A'
        print(f"第{r['run']}次:    {r['direction_score']:<11} {str(r['trade_long']):<12} {tier_str}")
    
    print("\n" + "=" * 80)
    
    ds_consistent = len(set(ds_values)) == 1
    tl_consistent = len(set(tl_values)) == 1
    tier_consistent = len(set(tier_values)) == 1
    
    if all([ds_consistent, tl_consistent, tier_consistent]):
        print("✅ 結論: 所有關鍵指標完全一致")
    else:
        print("❌ 結論: 存在不一致")
        if not ds_consistent:
            print(f"   Direction Score 範圍: {min(ds_values)} - {max(ds_values)}")
        if not tl_consistent:
            print(f"   ⚠️  嚴重: Trade Long 信號不穩定！")
        if not tier_consistent:
            print(f"   ⚠️  Tier 分類不穩定: {set(tier_values)}")

with open("stability_test2_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n💾 結果已保存到 stability_test2_results.json")

