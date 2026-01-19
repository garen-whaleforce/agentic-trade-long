#!/usr/bin/env python3
"""
Quick validation test for Round 6 prompt updates.
Tests a small sample of 2024 earnings calls to verify:
1. Direction Score distribution improved (more D7/D6, fewer D4)
2. Prompts working as expected
3. Time and cost estimation for full backtest
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from analysis_engine import analyze_earnings
from dotenv import load_dotenv

load_dotenv()

def get_2024_sample() -> List[Dict[str, Any]]:
    """Get a small sample of 2024 earnings calls for testing."""
    # Sample of 2024 earnings calls (you can adjust this)
    test_cases = [
        {"symbol": "AAPL", "year": 2024, "quarter": 1},
        {"symbol": "MSFT", "year": 2024, "quarter": 1},
        {"symbol": "GOOGL", "year": 2024, "quarter": 1},
        {"symbol": "AMZN", "year": 2024, "quarter": 1},
        {"symbol": "META", "year": 2024, "quarter": 1},
        {"symbol": "NVDA", "year": 2024, "quarter": 1},
        {"symbol": "TSLA", "year": 2024, "quarter": 1},
        {"symbol": "JPM", "year": 2024, "quarter": 1},
        {"symbol": "V", "year": 2024, "quarter": 1},
        {"symbol": "WMT", "year": 2024, "quarter": 1},
    ]
    return test_cases

def run_test():
    """Run quick validation test."""
    test_cases = get_2024_sample()
    total_samples = len(test_cases)

    print("=" * 80)
    print("Round 6 Prompt Validation Test")
    print("=" * 80)
    print(f"Testing {total_samples} 2024 Q1 earnings calls")
    print(f"Purpose: Validate new prompts, estimate time/cost for full backtest")
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

            # Analyze earnings call with new prompts
            result = analyze_earnings(
                symbol=symbol,
                year=year,
                quarter=quarter,
                use_backtest_services=False  # Skip backtest validation for speed
            )

            case_time = time.time() - case_start

            # Extract key metrics
            direction_score = result.get("direction_score", 0)
            trade_long = result.get("trade_long", False)
            tier = result.get("trade_long_tier", "N/A")
            soft_vetoes = len(result.get("soft_vetoes", []))
            hard_vetoes = len(result.get("hard_vetoes", []))

            results.append({
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "direction_score": direction_score,
                "trade_long": trade_long,
                "tier": tier,
                "soft_vetoes": soft_vetoes,
                "hard_vetoes": hard_vetoes,
                "time_seconds": case_time
            })

            print(f"✓ D{direction_score} {tier} ({case_time:.1f}s)")

        except Exception as e:
            print(f"✗ Error: {str(e)[:50]}")
            results.append({
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "error": str(e),
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
            bar = "█" * int(pct / 5)
            print(f"  D{score}: {count:2d} ({pct:5.1f}%) {bar}")

        # Tier Distribution
        print("\n📈 Tier Distribution:")
        tier_counts = successful[successful["trade_long"]]["tier"].value_counts()
        for tier, count in tier_counts.items():
            pct = count / len(successful[successful["trade_long"]]) * 100 if len(successful[successful["trade_long"]]) > 0 else 0
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

        # Assuming ~2000 earnings calls per year, 8 years = 16,000 calls
        estimated_calls = 16000
        estimated_time_hours = (estimated_calls * avg_time) / 3600
        estimated_cost_usd = estimated_calls * 0.05  # Rough estimate: $0.05 per call

        print(f"Estimated Total Calls: ~{estimated_calls:,}")
        print(f"Estimated Time: ~{estimated_time_hours:.1f} hours")
        print(f"Estimated Cost (LLM API): ~${estimated_cost_usd:.2f}")

        # Comparison with Iteration 1
        print("\n" + "=" * 80)
        print("Comparison with Iteration 1 (Parameter Tuning)")
        print("=" * 80)

        d7_d6_ratio = len(successful[successful["direction_score"] >= 6]) / len(successful) * 100
        d4_ratio = len(successful[successful["direction_score"] == 4]) / len(successful) * 100

        print(f"Current Test:")
        print(f"  D7/D6 Ratio: {d7_d6_ratio:.1f}% (Target: >45%, Iter1: 45.8%)")
        print(f"  D4 Ratio: {d4_ratio:.1f}% (Target: <35%, Iter1: 47.7%)")

        if d7_d6_ratio > 45:
            print("  ✅ D7/D6 ratio IMPROVED")
        else:
            print("  ⚠️  D7/D6 ratio needs work")

        if d4_ratio < 35:
            print("  ✅ D4 ratio REDUCED")
        else:
            print("  ⚠️  D4 ratio still high")

    else:
        print("❌ No successful analyses. Check errors above.")

    # Save results
    output_file = Path("test_results_round6.json")
    with open(output_file, "w") as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_samples": total_samples,
            "successful": len(successful),
            "results": results,
            "summary": {
                "avg_time_seconds": avg_time if len(successful) > 0 else 0,
                "d7_d6_ratio": d7_d6_ratio if len(successful) > 0 else 0,
                "d4_ratio": d4_ratio if len(successful) > 0 else 0,
            }
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")
    print()

if __name__ == "__main__":
    run_test()
