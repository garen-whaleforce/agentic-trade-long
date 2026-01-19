#!/usr/bin/env python3
"""
Simplified validation test using direct agentic_rag_bridge call.
Avoids complex dependencies.
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

# Import only what we need
from agentic_rag_bridge import agentic_rag_earnings_analysis

def get_2024_sample() -> List[Dict[str, Any]]:
    """Get a small sample of 2024 earnings calls for testing."""
    test_cases = [
        {"symbol": "AAPL", "year": 2024, "quarter": 1},
        {"symbol": "MSFT", "year": 2024, "quarter": 1},
        {"symbol": "GOOGL", "year": 2024, "quarter": 1},
        {"symbol": "AMZN", "year": 2024, "quarter": 1},
        {"symbol": "META", "year": 2024, "quarter": 1},
    ]
    return test_cases

def run_test():
    """Run quick validation test."""
    test_cases = get_2024_sample()
    total_samples = len(test_cases)

    print("=" * 80)
    print("Round 6 Prompt Validation Test (Simplified)")
    print("=" * 80)
    print(f"Testing {total_samples} 2024 Q1 earnings calls")
    print("=" * 80)
    print()

    results = []
    start_time = time.time()

    for i, case in enumerate(test_cases, 1):
        symbol = case["symbol"]
        year = case["year"]
        quarter = case["quarter"]

        print(f"[{i}/{total_samples}] Analyzing {symbol} {year}Q{quarter}...", end=" ", flush=True)

        try:
            case_start = time.time()

            # Use direct agentic_rag_bridge call
            result = agentic_rag_earnings_analysis(
                symbol=symbol,
                year=year,
                quarter=quarter,
                transcript_date=None,  # Will be fetched automatically
                credentials_file="credentials.json"
            )

            case_time = time.time() - case_start

            # Extract key metrics from long_eligible_json
            long_eligible = result.get("long_eligible_json", {})
            direction_score = long_eligible.get("direction_score", 0)
            trade_long = long_eligible.get("trade_long", False)
            tier = long_eligible.get("trade_long_tier", "N/A")
            soft_vetoes = long_eligible.get("soft_vetoes", [])
            hard_vetoes = long_eligible.get("hard_vetoes", [])

            results.append({
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "direction_score": direction_score,
                "trade_long": trade_long,
                "tier": tier,
                "soft_vetoes": len(soft_vetoes) if isinstance(soft_vetoes, list) else 0,
                "hard_vetoes": len(hard_vetoes) if isinstance(hard_vetoes, list) else 0,
                "time_seconds": case_time
            })

            print(f"✓ D{direction_score} {tier} ({case_time:.1f}s)")

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"✗ Error: {error_msg}")
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
    print("Test Results Summary")
    print("=" * 80)

    df = pd.DataFrame(results)
    successful = df[~df.get("error", pd.Series()).notna()]

    if len(successful) > 0:
        # Direction Score Distribution
        print("\n📊 Direction Score Distribution:")
        direction_counts = successful["direction_score"].value_counts().sort_index(ascending=False)
        for score, count in direction_counts.items():
            pct = count / len(successful) * 100
            bar = "█" * max(1, int(pct / 5))
            print(f"  D{score}: {count:2d} ({pct:5.1f}%) {bar}")

        # Tier Distribution
        print("\n📈 Tier Distribution (Trade Long signals only):")
        trade_long_df = successful[successful["trade_long"]]
        if len(trade_long_df) > 0:
            tier_counts = trade_long_df["tier"].value_counts()
            for tier, count in tier_counts.items():
                pct = count / len(trade_long_df) * 100
                print(f"  {tier}: {count} ({pct:.1f}%)")

        # Trade Signals
        trade_long_count = successful["trade_long"].sum()
        print(f"\n✅ Trade Long Signals: {trade_long_count}/{len(successful)} ({trade_long_count/len(successful)*100:.1f}%)")

        # Performance Stats
        avg_time = successful["time_seconds"].mean()
        print(f"\n⏱️  Average Time per Call: {avg_time:.1f}s")
        print(f"   Total Test Time: {total_time:.1f}s")

        # Extrapolation to Full Backtest
        print("\n" + "=" * 80)
        print("Full Backtest Estimation (2017-2024)")
        print("=" * 80)

        estimated_calls = 16000
        estimated_time_hours = (estimated_calls * avg_time) / 3600
        estimated_cost_usd = estimated_calls * 0.05

        print(f"Estimated Total Calls: ~{estimated_calls:,}")
        print(f"Estimated Time: ~{estimated_time_hours:.1f} hours ({estimated_time_hours/24:.1f} days)")
        print(f"Estimated Cost (LLM API): ~${estimated_cost_usd:.2f}")

        # Comparison with Iteration 1
        print("\n" + "=" * 80)
        print("Comparison with Iteration 1")
        print("=" * 80)

        d7_d6_count = len(successful[successful["direction_score"] >= 6])
        d7_d6_ratio = (d7_d6_count / len(successful) * 100) if len(successful) > 0 else 0

        d4_count = len(successful[successful["direction_score"] == 4])
        d4_ratio = (d4_count / len(successful) * 100) if len(successful) > 0 else 0

        print(f"Current Test:")
        print(f"  D7/D6 Ratio: {d7_d6_ratio:.1f}% (Target: >45%, Iter1: 45.8%)")
        print(f"  D4 Ratio: {d4_ratio:.1f}% (Target: <35%, Iter1: 47.7%)")

        if d7_d6_ratio > 45:
            print("  ✅ D7/D6 ratio IMPROVED")
        elif d7_d6_ratio > 40:
            print("  🟡 D7/D6 ratio slightly below target")
        else:
            print("  ❌ D7/D6 ratio needs significant improvement")

        if d4_ratio < 35:
            print("  ✅ D4 ratio REDUCED")
        elif d4_ratio < 45:
            print("  🟡 D4 ratio acceptable")
        else:
            print("  ❌ D4 ratio still too high")

        # Decision
        print("\n" + "=" * 80)
        print("Recommendation")
        print("=" * 80)

        if d7_d6_ratio > 45 and d4_ratio < 40:
            print("✅ PROCEED with Option A (Full Backtest)")
            print("   Prompt improvements are working as expected.")
        elif d7_d6_ratio > 40 or d4_ratio < 45:
            print("🟡 CONSIDER minor adjustments before Option A")
            print("   Results are promising but could be optimized further.")
        else:
            print("❌ DO NOT proceed with Option A yet")
            print("   Prompt changes need more work. Consult ChatGPT Pro for Round 7.")

    else:
        print("❌ No successful analyses. Check errors above.")
        print("\n❌ DO NOT proceed with Option A")
        print("   Fix dependency/configuration issues first.")

    # Save results
    output_file = Path("test_results_round6.json")
    with open(output_file, "w") as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "prompt_version": "Round 6 (2026-01-19)",
            "total_samples": total_samples,
            "successful": len(successful),
            "failed": len(df[df.get("error", pd.Series()).notna()]),
            "results": results,
            "summary": {
                "avg_time_seconds": avg_time if len(successful) > 0 else 0,
                "d7_d6_ratio": d7_d6_ratio if len(successful) > 0 else 0,
                "d4_ratio": d4_ratio if len(successful) > 0 else 0,
                "total_time": total_time
            }
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")
    print()

if __name__ == "__main__":
    run_test()
