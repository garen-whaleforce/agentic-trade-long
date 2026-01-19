#!/usr/bin/env python3
"""測試 gemini-3-flash-preview 的穩定性和性能"""

import os
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 使用 gemini-3-flash-preview
os.environ['MAIN_MODEL'] = 'gemini-3-flash-preview'

from agentic_rag_bridge import run_single_call_from_context

# 測試案例：NVDA 2017Q1 (與其他模型相同，方便比較)
test_case = {
    "symbol": "NVDA",
    "year": 2017,
    "quarter": 1,
    "transcript_date": None
}

print("🔬 測試 gemini-3-flash-preview 穩定性和性能")
print(f"案例: {test_case['symbol']} {test_case['year']}Q{test_case['quarter']}")
print("=" * 80)

results = []
total_start = time.time()

for i in range(3):
    print(f"\n執行第 {i+1} 次...")
    run_start = time.time()
    
    try:
        result = run_single_call_from_context(test_case)
        run_time = time.time() - run_start
        
        # 提取關鍵資訊
        long_eligible = result.get("long_eligible_json", {})
        
        key_metrics = {
            "run": i + 1,
            "direction_score": long_eligible.get("DirectionScore", 0),
            "confidence": result.get("confidence", 0),
            "trade_long": result.get("trade_long", False),
            "tier": result.get("trade_long_tier", ""),
            "risk_code": long_eligible.get("RiskCode", ""),
            "time_seconds": run_time
        }
        
        results.append(key_metrics)
        
        print(f"  ✅ Direction Score: {key_metrics['direction_score']}")
        print(f"  Confidence: {key_metrics['confidence']}")
        print(f"  Trade Long: {key_metrics['trade_long']}")
        print(f"  Tier: {key_metrics['tier'] if key_metrics['tier'] else 'N/A'}")
        print(f"  時間: {run_time:.1f}s")
        
    except Exception as e:
        run_time = time.time() - run_start
        print(f"  ❌ 錯誤: {e}")
        results.append({"run": i + 1, "error": str(e), "time_seconds": run_time})

total_time = time.time() - total_start

print("\n" + "=" * 80)
print("📊 結果比較")
print("=" * 80)

if len(results) == 3 and all("error" not in r for r in results):
    print(f"\n{'執行':<10} {'Direction':<12} {'Confidence':<12} {'Trade Long':<12} {'Tier':<10} {'時間':<10}")
    print("-" * 80)
    for r in results:
        tier_str = r['tier'] if r['tier'] else 'N/A'
        print(f"第{r['run']}次:{'':<4} {r['direction_score']:<12} {r['confidence']:<12} {str(r['trade_long']):<12} {tier_str:<10} {r['time_seconds']:.1f}s")
    
    print("\n" + "=" * 80)
    
    # 檢查一致性
    ds_values = [r['direction_score'] for r in results]
    conf_values = [r['confidence'] for r in results]
    tl_values = [r['trade_long'] for r in results]
    tier_values = [r['tier'] if r['tier'] else 'N/A' for r in results]
    
    ds_consistent = len(set(ds_values)) == 1
    conf_consistent = len(set(conf_values)) == 1
    tl_consistent = len(set(tl_values)) == 1
    tier_consistent = len(set(tier_values)) == 1
    
    print("\n一致性檢查:")
    print(f"  Direction Score: {'✅ 一致' if ds_consistent else '❌ 不一致'} ({set(ds_values)})")
    print(f"  Confidence: {'✅ 一致' if conf_consistent else '❌ 不一致'} ({set(conf_values)})")
    print(f"  Trade Long: {'✅ 一致' if tl_consistent else '❌ 不一致'} ({set(tl_values)})")
    print(f"  Tier: {'✅ 一致' if tier_consistent else '❌ 不一致'} ({set(tier_values)})")
    
    # 時間統計
    times = [r['time_seconds'] for r in results]
    avg_time = sum(times) / len(times)
    print(f"\n⏱️  時間統計:")
    print(f"  平均時間: {avg_time:.1f}s")
    print(f"  最快: {min(times):.1f}s")
    print(f"  最慢: {max(times):.1f}s")
    print(f"  總時間: {total_time:.1f}s")
    
    print("\n" + "=" * 80)
    
    if all([ds_consistent, tl_consistent, tier_consistent]):
        print("✅ 結論: gemini-3-flash-preview 結果完全一致且穩定")
    else:
        print("⚠️  結論: 存在不一致")
        if not ds_consistent:
            print(f"   Direction Score 範圍: {min(ds_values)}-{max(ds_values)} (波動±{max(ds_values)-min(ds_values)}分)")
        if not tl_consistent:
            print("   ⚠️  嚴重: 交易信號不穩定")
        if not tier_consistent:
            print(f"   Tier 分類不穩定: {set(tier_values)}")
else:
    print("❌ 測試失敗，有錯誤發生")
    for r in results:
        if "error" in r:
            print(f"  第{r['run']}次: {r['error']}")

# 保存結果
with open("gemini_stability_test_results.json", "w") as f:
    json.dump({
        "test_case": test_case,
        "results": results,
        "total_time": total_time,
        "model": "gemini-3-flash-preview"
    }, f, indent=2)

print(f"\n💾 結果已保存到 gemini_stability_test_results.json")

