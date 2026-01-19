#!/usr/bin/env python3
"""
Phase 7 Final Integration Test
測試 Rounds 6-10 完整整合 (所有 Phases 1-6)

測試重點：
1. 所有 Prompt 優化 (Phase 1)
2. Veto Logic (Phase 2)
3. Tier Gates (Phase 3)
4. Position Sizing (Phase 4)
5. Data Flow & Validation (Phase 6)
6. 整體系統協調
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from agentic_rag_bridge import run_single_call_from_context

def get_test_sample() -> List[Dict[str, Any]]:
    """Get diverse sample of 2024 earnings calls for comprehensive testing."""
    test_cases = [
        # High performers with strong EPS surprise
        {"symbol": "NVDA", "year": 2024, "quarter": 1, "expected": "D8_MEGA or D7_CORE"},
        {"symbol": "META", "year": 2024, "quarter": 1, "expected": "D7_CORE or D6_STRICT"},
        {"symbol": "GOOGL", "year": 2024, "quarter": 1, "expected": "D7_CORE or D6_STRICT"},
        {"symbol": "MSFT", "year": 2024, "quarter": 1, "expected": "D7_CORE or D6_STRICT"},

        # Moderate performers
        {"symbol": "AAPL", "year": 2024, "quarter": 1, "expected": "D6_STRICT or D4_ENTRY"},
        {"symbol": "AMZN", "year": 2024, "quarter": 1, "expected": "D7_CORE or D6_STRICT"},
        {"symbol": "TSLA", "year": 2024, "quarter": 1, "expected": "D6_STRICT or lower"},

        # Various sectors
        {"symbol": "JPM", "year": 2024, "quarter": 1, "expected": "Financials sector"},
        {"symbol": "JNJ", "year": 2024, "quarter": 1, "expected": "Healthcare sector"},
        {"symbol": "XOM", "year": 2024, "quarter": 1, "expected": "Energy sector"},

        # Additional tech coverage
        {"symbol": "AMD", "year": 2024, "quarter": 1, "expected": "Technology"},
        {"symbol": "NFLX", "year": 2024, "quarter": 1, "expected": "Communication Services"},

        # Consumer & Industrial
        {"symbol": "NKE", "year": 2024, "quarter": 1, "expected": "Consumer Discretionary"},
        {"symbol": "HD", "year": 2024, "quarter": 1, "expected": "Consumer Discretionary"},
        {"symbol": "BA", "year": 2024, "quarter": 1, "expected": "Industrials"},
    ]
    return test_cases

def run_test():
    """Run Phase 7 final integration test."""
    test_cases = get_test_sample()
    total_samples = len(test_cases)

    print("=" * 80)
    print("Phase 7 Final Integration Test (Rounds 6-10 Complete)")
    print("=" * 80)
    print(f"測試 {total_samples} 個 2024 Q1 財報電話會議")
    print(f"重點: 驗證所有 Phases 1-6 的完整整合")
    print("=" * 80)
    print()

    results = []
    start_time = time.time()
    errors = []

    for i, case in enumerate(test_cases, 1):
        symbol = case["symbol"]
        year = case["year"]
        quarter = case["quarter"]
        expected = case["expected"]

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

            # Extract comprehensive metrics
            long_eligible = result.get("long_eligible_json", {})
            direction_score = long_eligible.get("DirectionScore", 0)
            confidence = result.get("confidence", 0)
            trade_long = result.get("trade_long", False)
            tier = result.get("trade_long_tier", "N/A")

            # Market anchors
            market_anchors = result.get("market_anchors", {})
            eps_surprise = market_anchors.get("eps_surprise")
            earnings_day_return = market_anchors.get("earnings_day_return")
            pre_earnings_5d_return = market_anchors.get("pre_earnings_5d_return")

            # Veto info
            detailed_vetoes = result.get("detailed_vetoes", {})
            hard_vetoes = detailed_vetoes.get("hard_vetoes", [])
            soft_vetoes = detailed_vetoes.get("soft_vetoes", {})
            soft_veto_multiplier = detailed_vetoes.get("total_soft_veto_multiplier", 1.0)

            # Position sizing (if available)
            # Note: position_size might not be in result, depends on implementation

            results.append({
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "direction_score": direction_score,
                "confidence": confidence,
                "trade_long": trade_long,
                "tier": tier,
                "eps_surprise": eps_surprise,
                "earnings_day_return": earnings_day_return,
                "pre_earnings_5d_return": pre_earnings_5d_return,
                "n_hard_vetoes": len(hard_vetoes),
                "n_soft_vetoes": len(soft_vetoes),
                "soft_veto_multiplier": soft_veto_multiplier,
                "hard_veto_list": hard_vetoes,
                "soft_veto_list": list(soft_vetoes.keys()),
                "expected": expected,
                "time_seconds": case_time
            })

            # Print concise result
            eps_str = f"EPS={eps_surprise:.1%}" if eps_surprise is not None else "EPS=N/A"
            day_str = f"Day={earnings_day_return:+.1%}" if earnings_day_return is not None else "Day=N/A"
            veto_str = f"HV={len(hard_vetoes)} SV={len(soft_vetoes)}"
            print(f"✓ D{direction_score} {tier} {eps_str} {day_str} {veto_str} ({case_time:.1f}s)")

        except Exception as e:
            error_msg = str(e)[:200]
            print(f"✗ 錯誤: {error_msg}")
            errors.append({
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "error": error_msg
            })
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
    print("Phase 7 最終測試結果")
    print("=" * 80)

    df = pd.DataFrame(results)

    # Filter successful results
    if "error" in df.columns:
        successful = df[df["error"].isna()]
    else:
        successful = df

    if len(successful) > 0:
        # Key Statistics
        print(f"\n✅ 成功分析: {len(successful)}/{total_samples} ({len(successful)/total_samples*100:.1f}%)")
        if errors:
            print(f"❌ 失敗: {len(errors)}/{total_samples}")

        # Direction Score Distribution
        print("\n📊 Direction Score 分佈:")
        direction_counts = successful["direction_score"].value_counts().sort_index(ascending=False)
        for score, count in direction_counts.items():
            pct = count / len(successful) * 100
            bar = "█" * max(1, int(pct / 5))
            print(f"  D{score}: {count:2d} ({pct:5.1f}%) {bar}")

        # Confidence Distribution
        print("\n🎯 Confidence 分佈:")
        confidence_bins = pd.cut(successful["confidence"], bins=[0, 0.3, 0.5, 0.7, 1.0], labels=["Low", "Medium", "High", "VHigh"])
        conf_counts = confidence_bins.value_counts().sort_index()
        for conf, count in conf_counts.items():
            pct = count / len(successful) * 100
            print(f"  {conf}: {count} ({pct:.1f}%)")

        # Tier Distribution
        print("\n🏆 Tier 分佈 (Trade Long signals only):")
        trade_long_df = successful[successful["trade_long"]]
        if len(trade_long_df) > 0:
            tier_counts = trade_long_df["tier"].value_counts().sort_index(ascending=False)
            for tier, count in tier_counts.items():
                pct = count / len(trade_long_df) * 100
                print(f"  {tier}: {count} ({pct:.1f}%)")

            # Check for D8_MEGA
            d8_count = len(trade_long_df[trade_long_df["tier"] == "D8_MEGA"])
            d7_count = len(trade_long_df[trade_long_df["tier"] == "D7_CORE"])
            d6_count = len(trade_long_df[trade_long_df["tier"] == "D6_STRICT"])
            high_tier_count = d8_count + d7_count + d6_count
            high_tier_ratio = high_tier_count / len(trade_long_df) * 100 if len(trade_long_df) > 0 else 0

            print(f"\n  高階 Tier (D6+) 比例: {high_tier_ratio:.1f}% ({high_tier_count}/{len(trade_long_df)})")
        else:
            print("  無交易信號")

        # Trade Signals
        trade_count = successful["trade_long"].sum()
        print(f"\n✅ 交易信號: {trade_count}/{len(successful)} ({trade_count/len(successful)*100:.1f}%)")

        # Market Anchors Analysis
        print("\n💰 Market Anchors 分析:")
        eps_available = successful[successful["eps_surprise"].notna()]
        if len(eps_available) > 0:
            avg_eps = eps_available["eps_surprise"].mean()
            median_eps = eps_available["eps_surprise"].median()
            max_eps = eps_available["eps_surprise"].max()
            min_eps = eps_available["eps_surprise"].min()
            print(f"  EPS Surprise:")
            print(f"    平均: {avg_eps:.1%}")
            print(f"    中位數: {median_eps:.1%}")
            print(f"    範圍: {min_eps:.1%} ~ {max_eps:.1%}")

        day_ret_available = successful[successful["earnings_day_return"].notna()]
        if len(day_ret_available) > 0:
            avg_day = day_ret_available["earnings_day_return"].mean()
            positive_day = (day_ret_available["earnings_day_return"] > 0).sum()
            print(f"  Earnings Day Return:")
            print(f"    平均: {avg_day:+.1%}")
            print(f"    正回報: {positive_day}/{len(day_ret_available)} ({positive_day/len(day_ret_available)*100:.1f}%)")

        # Veto Statistics
        print("\n⚠️  Veto 統計:")
        avg_hard_vetoes = successful["n_hard_vetoes"].mean()
        avg_soft_vetoes = successful["n_soft_vetoes"].mean()
        avg_soft_multiplier = successful["soft_veto_multiplier"].mean()

        print(f"  平均 Hard Vetoes: {avg_hard_vetoes:.2f}")
        print(f"  平均 Soft Vetoes: {avg_soft_vetoes:.2f}")
        print(f"  平均 Soft Veto Multiplier: {avg_soft_multiplier:.3f}x")

        # Collect all veto types
        all_hard_vetoes = []
        all_soft_vetoes = []
        for _, row in successful.iterrows():
            if isinstance(row.get("hard_veto_list"), list):
                all_hard_vetoes.extend(row["hard_veto_list"])
            if isinstance(row.get("soft_veto_list"), list):
                all_soft_vetoes.extend(row["soft_veto_list"])

        if all_hard_vetoes:
            hard_veto_counts = pd.Series(all_hard_vetoes).value_counts()
            print(f"\n  Hard Veto 類型:")
            for veto, count in hard_veto_counts.items():
                print(f"    {veto}: {count}")

        if all_soft_vetoes:
            soft_veto_counts = pd.Series(all_soft_vetoes).value_counts()
            print(f"\n  Soft Veto 類型:")
            for veto, count in soft_veto_counts.items():
                print(f"    {veto}: {count}")

        # Performance Stats
        avg_time = successful["time_seconds"].mean()
        max_time = successful["time_seconds"].max()
        min_time = successful["time_seconds"].min()
        print(f"\n⏱️  性能統計:")
        print(f"  平均時間: {avg_time:.1f}s")
        print(f"  範圍: {min_time:.1f}s ~ {max_time:.1f}s")
        print(f"  總測試時間: {total_time:.1f}s ({total_time/60:.1f} min)")

        # Phase 7 Assessment
        print("\n" + "=" * 80)
        print("Phase 7 最終評估")
        print("=" * 80)

        improvements = []
        concerns = []
        warnings = []

        # Check Direction Score distribution
        d7_plus = len(successful[successful["direction_score"] >= 7])
        d7_plus_ratio = d7_plus / len(successful) * 100 if len(successful) > 0 else 0

        if d7_plus_ratio >= 30:
            improvements.append(f"✅ D7+ 比例良好: {d7_plus_ratio:.1f}% (目標 >30%)")
        elif d7_plus_ratio >= 20:
            warnings.append(f"🟡 D7+ 比例可接受: {d7_plus_ratio:.1f}% (目標 >30%)")
        else:
            concerns.append(f"⚠️  D7+ 比例偏低: {d7_plus_ratio:.1f}% (目標 >30%)")

        # Check trade signal rate
        trade_rate = trade_count / len(successful) * 100 if len(successful) > 0 else 0
        if 40 <= trade_rate <= 70:
            improvements.append(f"✅ 交易信號比例合理: {trade_rate:.1f}% (40-70%)")
        elif 30 <= trade_rate < 40 or 70 < trade_rate <= 80:
            warnings.append(f"🟡 交易信號比例邊界: {trade_rate:.1f}%")
        else:
            concerns.append(f"⚠️  交易信號比例異常: {trade_rate:.1f}%")

        # Check high tier ratio
        if len(trade_long_df) > 0:
            if high_tier_ratio >= 50:
                improvements.append(f"✅ 高階 Tier 比例良好: {high_tier_ratio:.1f}% (目標 >50%)")
            elif high_tier_ratio >= 40:
                warnings.append(f"🟡 高階 Tier 比例可接受: {high_tier_ratio:.1f}%")
            else:
                concerns.append(f"⚠️  高階 Tier 比例偏低: {high_tier_ratio:.1f}% (目標 >50%)")

        # Check average time
        if avg_time < 30:
            improvements.append(f"✅ 平均時間優秀: {avg_time:.1f}s")
        elif avg_time < 60:
            improvements.append(f"✅ 平均時間可接受: {avg_time:.1f}s")
        else:
            concerns.append(f"⚠️  平均時間過高: {avg_time:.1f}s (>60s)")

        # Check data completeness
        eps_completeness = len(eps_available) / len(successful) * 100 if len(successful) > 0 else 0
        if eps_completeness >= 80:
            improvements.append(f"✅ EPS 數據完整性: {eps_completeness:.1f}%")
        else:
            warnings.append(f"🟡 EPS 數據完整性: {eps_completeness:.1f}% (目標 >80%)")

        # Check veto detection
        if avg_soft_vetoes > 0 or len(all_soft_vetoes) > 0:
            improvements.append("✅ Veto 檢測正常運作")
        else:
            warnings.append("🟡 未檢測到 Soft Vetoes (可能正常)")

        # Display results
        if improvements:
            print("\n✅ 改進:")
            for imp in improvements:
                print(f"  {imp}")

        if warnings:
            print("\n🟡 警告:")
            for warn in warnings:
                print(f"  {warn}")

        if concerns:
            print("\n⚠️  關注點:")
            for con in concerns:
                print(f"  {con}")

        # Final Decision
        print("\n" + "=" * 80)
        print("最終建議")
        print("=" * 80)

        proceed = False
        if len(concerns) == 0 and len(improvements) >= 4:
            print("✅ 準備就緒：執行完整回測 (2017-2024)")
            print("   所有 Phases 1-6 整合良好，系統運作正常。")
            proceed = True
        elif len(concerns) <= 1 and len(improvements) >= 2:
            print("🟡 謹慎繼續：可執行完整回測")
            print("   大部分功能正常，但需監控提到的關注點。")
            proceed = True
        else:
            print("⚠️  建議檢查：先解決關注點再執行完整回測")
            print("   系統可能存在配置或邏輯問題。")
            proceed = False

    else:
        print("❌ 無成功分析。請檢查上方錯誤。")
        proceed = False

    # Save results
    output_file = Path("test_results_phase7_final.json")

    # Calculate failed count
    failed_count = len(errors)

    with open(output_file, "w") as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": "Phase 7 (Final Integration Test - Rounds 6-10)",
            "total_samples": total_samples,
            "successful": len(successful) if len(df) > 0 else 0,
            "failed": failed_count,
            "results": results,
            "errors": errors,
            "summary": {
                "avg_time_seconds": avg_time if len(successful) > 0 else 0,
                "d7_plus_ratio": d7_plus_ratio if len(successful) > 0 else 0,
                "trade_signal_ratio": trade_rate if len(successful) > 0 else 0,
                "high_tier_ratio": high_tier_ratio if len(successful) > 0 and len(trade_long_df) > 0 else 0,
                "total_time": total_time,
                "proceed_to_backtest": proceed if len(successful) > 0 else False
            }
        }, f, indent=2)

    print(f"\n💾 結果已保存至: {output_file}")
    print()

    return proceed if len(successful) > 0 else False

if __name__ == "__main__":
    proceed = run_test()
    sys.exit(0 if proceed else 1)
