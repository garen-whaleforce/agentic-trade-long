#!/usr/bin/env python3
"""
Phase 2-3 Test Script
Tests Round 7-8 implementations (Veto Logic + Tier Gates).

Tests:
1. New hard veto detection functions
2. D8_MEGA tier (eps_surprise > 20%)
3. D7_CORE tier (eps_surprise > 12%, Round 10)
4. D7 soft veto relaxation (≤2 soft vetoes if eps > 15%)
5. D6_STRICT tier (eps_surprise > 5%)
6. D4_ENTRY tier (eps_surprise ≥ 8%)
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from agentic_rag_bridge import run_single_call_from_context

def get_test_sample() -> List[Dict[str, Any]]:
    """Get sample earnings calls for Phase 2-3 testing."""
    test_cases = [
        # High surprise cases (should trigger D8_MEGA or D7_CORE)
        {"symbol": "NVDA", "year": 2024, "quarter": 1, "expected_tier": "D8_MEGA or D7_CORE"},
        {"symbol": "META", "year": 2024, "quarter": 1, "expected_tier": "D7_CORE or lower"},

        # Moderate surprise cases (should trigger D6_STRICT or D7_CORE)
        {"symbol": "AAPL", "year": 2024, "quarter": 1, "expected_tier": "D6_STRICT or D4_ENTRY"},
        {"symbol": "MSFT", "year": 2024, "quarter": 1, "expected_tier": "D7_CORE or D6_STRICT"},
        {"symbol": "GOOGL", "year": 2024, "quarter": 1, "expected_tier": "D7_CORE"},
    ]
    return test_cases

def run_test():
    """Run Phase 2-3 test."""
    test_cases = get_test_sample()
    total_samples = len(test_cases)

    print("=" * 80)
    print("Phase 2-3 Test: Veto Logic + Tier Gates (Rounds 7-8)")
    print("=" * 80)
    print(f"測試 {total_samples} 個 2024 Q1 財報電話會議")
    print(f"重點: 驗證新 Veto 邏輯和更新的 Tier 門檻")
    print("=" * 80)
    print()

    results = []
    start_time = time.time()

    for i, case in enumerate(test_cases, 1):
        symbol = case["symbol"]
        year = case["year"]
        quarter = case["quarter"]
        expected = case["expected_tier"]

        print(f"[{i}/{total_samples}] 分析 {symbol} {year}Q{quarter}...", end=" ", flush=True)

        try:
            case_start = time.time()

            context = {
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "transcript_date": None,
            }
            result = run_single_call_from_context(context)

            case_time = time.time() - case_start

            # Extract metrics
            long_eligible = result.get("long_eligible_json", {})
            direction_score = long_eligible.get("DirectionScore", 0)
            confidence = result.get("confidence", 0)
            trade_long = result.get("trade_long", False)
            tier = result.get("trade_long_tier", "N/A")

            # Get market anchors
            market_anchors = result.get("market_anchors", {})
            eps_surprise = market_anchors.get("eps_surprise")

            # Get veto info
            detailed_vetoes = result.get("detailed_vetoes", {})
            hard_vetoes = detailed_vetoes.get("hard_vetoes", [])
            soft_vetoes = detailed_vetoes.get("soft_vetoes", {})
            soft_veto_multiplier = detailed_vetoes.get("total_soft_veto_multiplier", 1.0)

            results.append({
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "direction_score": direction_score,
                "confidence": confidence,
                "trade_long": trade_long,
                "tier": tier,
                "eps_surprise": eps_surprise,
                "n_hard_vetoes": len(hard_vetoes),
                "n_soft_vetoes": len(soft_vetoes),
                "soft_veto_multiplier": soft_veto_multiplier,
                "hard_veto_list": hard_vetoes,
                "soft_veto_list": list(soft_vetoes.keys()),
                "expected_tier": expected,
                "time_seconds": case_time
            })

            # Print result
            eps_str = f"EPS={eps_surprise:.1%}" if eps_surprise is not None else "EPS=N/A"
            veto_str = f"HV={len(hard_vetoes)} SV={len(soft_vetoes)}"
            print(f"✓ D{direction_score} {tier} {eps_str} {veto_str} ({case_time:.1f}s)")

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"✗ 錯誤: {error_msg}")
            results.append({
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "error": error_msg,
                "time_seconds": 0
            })

    total_time = time.time() - start_time

    # Analysis
    print()
    print("=" * 80)
    print("Phase 2-3 測試結果")
    print("=" * 80)

    df = pd.DataFrame(results)

    # Filter successful results
    if "error" in df.columns:
        successful = df[df["error"].isna()]
    else:
        successful = df

    if len(successful) > 0:
        # Tier Distribution
        print("\n📊 Tier 分佈:")
        tier_counts = successful[successful["trade_long"]]["tier"].value_counts()
        for tier, count in tier_counts.items():
            pct = count / len(successful[successful["trade_long"]]) * 100 if len(successful[successful["trade_long"]]) > 0 else 0
            print(f"  {tier}: {count} ({pct:.1f}%)")

        # Check for D8_MEGA tier
        d8_count = len(successful[successful["tier"] == "D8_MEGA"])
        d7_count = len(successful[successful["tier"] == "D7_CORE"])
        d6_count = len(successful[successful["tier"] == "D6_STRICT"])
        d4_count = len(successful[successful["tier"] == "D4_ENTRY"])

        print(f"\n✅ 交易信號: {successful['trade_long'].sum()}/{len(successful)} ({successful['trade_long'].sum()/len(successful)*100:.1f}%)")

        # EPS Surprise Analysis
        print("\n💰 EPS Surprise 分析:")
        eps_available = successful[successful["eps_surprise"].notna()]
        if len(eps_available) > 0:
            avg_eps = eps_available["eps_surprise"].mean()
            max_eps = eps_available["eps_surprise"].max()
            min_eps = eps_available["eps_surprise"].min()
            print(f"  平均: {avg_eps:.1%}")
            print(f"  最大: {max_eps:.1%}")
            print(f"  最小: {min_eps:.1%}")

            # Check tier thresholds
            print("\n🎯 Tier 門檻驗證:")

            # D8_MEGA (eps > 20%)
            d8_eligible = eps_available[eps_available["eps_surprise"] > 0.20]
            print(f"  D8_MEGA 符合資格 (EPS>20%): {len(d8_eligible)}/{len(eps_available)}")
            if len(d8_eligible) > 0:
                d8_triggered = d8_eligible[d8_eligible["tier"] == "D8_MEGA"]
                print(f"    實際觸發: {len(d8_triggered)}/{len(d8_eligible)}")

            # D7_CORE (eps > 12%)
            d7_eligible = eps_available[eps_available["eps_surprise"] > 0.12]
            print(f"  D7_CORE 符合資格 (EPS>12%): {len(d7_eligible)}/{len(eps_available)}")
            if len(d7_eligible) > 0:
                d7_triggered = d7_eligible[d7_eligible["tier"].isin(["D7_CORE", "D8_MEGA"])]
                print(f"    實際觸發 D7/D8: {len(d7_triggered)}/{len(d7_eligible)}")

            # D6_STRICT (eps > 5%)
            d6_eligible = eps_available[eps_available["eps_surprise"] > 0.05]
            print(f"  D6_STRICT 符合資格 (EPS>5%): {len(d6_eligible)}/{len(eps_available)}")

            # D4_ENTRY (eps >= 8%)
            d4_eligible = eps_available[eps_available["eps_surprise"] >= 0.08]
            print(f"  D4_ENTRY 符合資格 (EPS>=8%): {len(d4_eligible)}/{len(eps_available)}")

        # Veto Statistics
        print("\n⚠️  Veto 統計:")
        avg_hard_vetoes = successful["n_hard_vetoes"].mean()
        avg_soft_vetoes = successful["n_soft_vetoes"].mean()
        avg_soft_multiplier = successful["soft_veto_multiplier"].mean()

        print(f"  平均 Hard Vetoes: {avg_hard_vetoes:.1f}")
        print(f"  平均 Soft Vetoes: {avg_soft_vetoes:.1f}")
        print(f"  平均 Soft Veto Multiplier: {avg_soft_multiplier:.2f}x")

        # Check for new veto types
        all_hard_vetoes = []
        all_soft_vetoes = []
        for _, row in successful.iterrows():
            if isinstance(row.get("hard_veto_list"), list):
                all_hard_vetoes.extend(row["hard_veto_list"])
            if isinstance(row.get("soft_veto_list"), list):
                all_soft_vetoes.extend(row["soft_veto_list"])

        if all_hard_vetoes:
            print(f"\n  Hard Veto 類型: {set(all_hard_vetoes)}")
        if all_soft_vetoes:
            print(f"  Soft Veto 類型: {set(all_soft_vetoes)}")

        # Performance Stats
        avg_time = successful["time_seconds"].mean()
        print(f"\n⏱️  平均時間: {avg_time:.1f}s")
        print(f"   總測試時間: {total_time:.1f}s")

        # Phase 2-3 Assessment
        print("\n" + "=" * 80)
        print("Phase 2-3 評估")
        print("=" * 80)

        improvements = []
        concerns = []

        # Check if D8_MEGA tier is working
        if d8_count > 0:
            improvements.append("✅ D8_MEGA tier 正常運作")
        else:
            concerns.append("🟡 D8_MEGA tier 未觸發 (可能無符合條件的樣本)")

        # Check if tier distribution is reasonable
        high_tier_count = d8_count + d7_count + d6_count
        high_tier_ratio = high_tier_count / len(successful) * 100 if len(successful) > 0 else 0

        if high_tier_ratio > 40:
            improvements.append(f"✅ 高階 Tier (D6+) 比例合理: {high_tier_ratio:.1f}%")
        else:
            concerns.append(f"⚠️  高階 Tier 比例偏低: {high_tier_ratio:.1f}%")

        # Check average time
        if avg_time < 60:
            improvements.append("✅ 平均時間可接受 (<60s)")
        else:
            concerns.append("⚠️  平均時間過高 (>60s)")

        print("\n改進:")
        for imp in improvements:
            print(f"  {imp}")

        if concerns:
            print("\n關注點:")
            for con in concerns:
                print(f"  {con}")

        # Decision
        print("\n" + "=" * 80)
        print("建議")
        print("=" * 80)

        if len(improvements) >= 2:
            print("✅ 繼續 Phase 4 (Position Sizing)")
            print("   Phase 2-3 更改顯示正面效果。")
            proceed = True
        elif len(improvements) >= 1:
            print("🟡 謹慎繼續 Phase 4")
            print("   觀察到一些改進，謹慎繼續。")
            proceed = True
        else:
            print("⚠️  檢查 Phase 2-3 更改再繼續")
            print("   未檢測到明顯改進。")
            proceed = False

    else:
        print("❌ 無成功分析。請檢查上方錯誤。")
        proceed = False

    # Save results
    output_file = Path("test_results_phase2_3.json")

    # Calculate failed count
    if "error" in df.columns:
        failed_count = len(df[df["error"].notna()])
    else:
        failed_count = 0

    with open(output_file, "w") as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": "Phase 2-3 (Rounds 7-8: Veto Logic + Tier Gates)",
            "total_samples": total_samples,
            "successful": len(successful) if len(df) > 0 else 0,
            "failed": failed_count,
            "results": results,
            "summary": {
                "avg_time_seconds": avg_time if len(successful) > 0 else 0,
                "d8_count": d8_count if len(successful) > 0 else 0,
                "d7_count": d7_count if len(successful) > 0 else 0,
                "d6_count": d6_count if len(successful) > 0 else 0,
                "d4_count": d4_count if len(successful) > 0 else 0,
                "total_time": total_time,
                "proceed_to_phase4": proceed if len(successful) > 0 else False
            }
        }, f, indent=2)

    print(f"\n💾 結果已保存至: {output_file}")
    print()

    return proceed if len(successful) > 0 else False

if __name__ == "__main__":
    proceed = run_test()
    sys.exit(0 if proceed else 1)
