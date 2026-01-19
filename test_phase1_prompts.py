#!/usr/bin/env python3
"""
Phase 1 Prompt Optimization Test
Tests Rounds 6-7 prompt updates on small sample.
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
from agentic_rag_bridge import run_single_call_from_context

def get_test_sample() -> List[Dict[str, Any]]:
    """Get a small sample of 2024 earnings calls for testing."""
    test_cases = [
        {"symbol": "AAPL", "year": 2024, "quarter": 1},
        {"symbol": "MSFT", "year": 2024, "quarter": 1},
        {"symbol": "GOOGL", "year": 2024, "quarter": 1},
        {"symbol": "NVDA", "year": 2024, "quarter": 1},
        {"symbol": "META", "year": 2024, "quarter": 1},
    ]
    return test_cases

def run_test():
    """Run Phase 1 prompt optimization test."""
    test_cases = get_test_sample()
    total_samples = len(test_cases)

    print("=" * 80)
    print("Phase 1 Prompt Optimization Test (Rounds 6-7)")
    print("=" * 80)
    print(f"Testing {total_samples} 2024 Q1 earnings calls")
    print(f"Focus: Validate new prompts working correctly")
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

            # Use run_single_call_from_context with context dict
            context = {
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "transcript_date": None,  # Will be fetched automatically
            }
            result = run_single_call_from_context(context)

            case_time = time.time() - case_start

            # Debug: print result keys
            if i == 1:  # Only for first case
                print(f"\n[DEBUG] Result keys: {list(result.keys())}")
                if "long_eligible_json" in result:
                    print(f"[DEBUG] long_eligible_json keys: {list(result['long_eligible_json'].keys())}")

            # Extract key metrics
            # Keys are capitalized in long_eligible_json
            long_eligible = result.get("long_eligible_json", {})
            direction_score = long_eligible.get("DirectionScore", result.get("direction_score", 0))
            confidence = result.get("confidence", 0)  # Top-level confidence
            trade_long = result.get("trade_long", False)
            tier = result.get("trade_long_tier", "N/A")

            # Count vetoes from computed lists
            soft_vetoes = result.get("computed_soft_vetoes", [])
            hard_vetoes = result.get("computed_hard_vetoes", [])

            results.append({
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "direction_score": direction_score,
                "confidence": confidence,
                "trade_long": trade_long,
                "tier": tier,
                "n_soft_vetoes": len(soft_vetoes) if isinstance(soft_vetoes, list) else 0,
                "n_hard_vetoes": len(hard_vetoes) if isinstance(hard_vetoes, list) else 0,
                "time_seconds": case_time
            })

            print(f"✓ D{direction_score} C{confidence} {tier} ({case_time:.1f}s)")

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
    print("Phase 1 Test Results")
    print("=" * 80)

    df = pd.DataFrame(results)
    # Fix: properly filter successful results
    if "error" in df.columns:
        successful = df[df["error"].isna()]
    else:
        successful = df

    if len(successful) > 0:
        # Direction Score Distribution
        print("\n📊 Direction Score Distribution:")
        direction_counts = successful["direction_score"].value_counts().sort_index(ascending=False)
        for score, count in direction_counts.items():
            pct = count / len(successful) * 100
            bar = "█" * max(1, int(pct / 5))
            print(f"  D{score}: {count:2d} ({pct:5.1f}%) {bar}")

        # Confidence Distribution
        print("\n🎯 Confidence Score Distribution:")
        confidence_counts = successful["confidence"].value_counts().sort_index(ascending=False)
        for conf, count in confidence_counts.items():
            pct = count / len(successful) * 100
            bar = "█" * max(1, int(pct / 5))
            print(f"  C{conf}: {count:2d} ({pct:5.1f}%) {bar}")

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

        # Veto Statistics
        avg_soft_vetoes = successful["n_soft_vetoes"].mean()
        avg_hard_vetoes = successful["n_hard_vetoes"].mean()
        print(f"\n⚠️  Average Soft Vetoes: {avg_soft_vetoes:.1f}")
        print(f"   Average Hard Vetoes: {avg_hard_vetoes:.1f}")

        # Performance Stats
        avg_time = successful["time_seconds"].mean()
        print(f"\n⏱️  Average Time per Call: {avg_time:.1f}s")
        print(f"   Total Test Time: {total_time:.1f}s")

        # Key Metrics vs Iteration 1
        print("\n" + "=" * 80)
        print("Comparison with Iteration 1 Baseline")
        print("=" * 80)

        d7_d6_count = len(successful[successful["direction_score"] >= 6])
        d7_d6_ratio = (d7_d6_count / len(successful) * 100) if len(successful) > 0 else 0

        d4_count = len(successful[successful["direction_score"] == 4])
        d4_ratio = (d4_count / len(successful) * 100) if len(successful) > 0 else 0

        print(f"Phase 1 Results:")
        print(f"  D7/D6 Ratio: {d7_d6_ratio:.1f}% (Baseline: 45.8%, Target: >50%)")
        print(f"  D4 Ratio: {d4_ratio:.1f}% (Baseline: 47.7%, Target: <40%)")

        # Assessment
        print("\n" + "=" * 80)
        print("Phase 1 Assessment")
        print("=" * 80)

        improvements = []
        concerns = []

        if d7_d6_ratio > 50:
            improvements.append("✅ D7/D6 ratio improved (target met)")
        elif d7_d6_ratio > 45.8:
            improvements.append("🟡 D7/D6 ratio slightly improved")
        else:
            concerns.append("⚠️  D7/D6 ratio not improved")

        if d4_ratio < 40:
            improvements.append("✅ D4 ratio reduced (target met)")
        elif d4_ratio < 47.7:
            improvements.append("🟡 D4 ratio slightly reduced")
        else:
            concerns.append("⚠️  D4 ratio not reduced")

        if avg_time < 60:
            improvements.append("✅ Average time acceptable (<60s)")
        else:
            concerns.append("⚠️  Average time too high (>60s)")

        print("\nImprovements:")
        for imp in improvements:
            print(f"  {imp}")

        if concerns:
            print("\nConcerns:")
            for con in concerns:
                print(f"  {con}")

        # Decision
        print("\n" + "=" * 80)
        print("Recommendation")
        print("=" * 80)

        if len(improvements) >= 2 and len(concerns) == 0:
            print("✅ PROCEED to Phase 2-3 (Veto Logic + Tier Gates)")
            print("   Phase 1 prompt optimization showing positive effects.")
            proceed = True
        elif len(improvements) >= 1:
            print("🟡 CAUTIOUSLY PROCEED to Phase 2-3")
            print("   Some improvements observed, continue with caution.")
            proceed = True
        else:
            print("⚠️  REVIEW Phase 1 changes before proceeding")
            print("   No clear improvements detected.")
            proceed = False

    else:
        print("❌ No successful analyses. Check errors above.")
        proceed = False

    # Save results
    output_file = Path("test_results_phase1.json")

    # Calculate failed count properly
    if "error" in df.columns:
        failed_count = len(df[df["error"].notna()])
    else:
        failed_count = 0

    with open(output_file, "w") as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": "Phase 1 (Rounds 6-7 Prompts)",
            "total_samples": total_samples,
            "successful": len(successful) if len(df) > 0 else 0,
            "failed": failed_count,
            "results": results,
            "summary": {
                "avg_time_seconds": avg_time if len(successful) > 0 else 0,
                "d7_d6_ratio": d7_d6_ratio if len(successful) > 0 else 0,
                "d4_ratio": d4_ratio if len(successful) > 0 else 0,
                "total_time": total_time,
                "proceed_to_phase2": proceed if len(successful) > 0 else False
            }
        }, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")
    print()

    return proceed if len(successful) > 0 else False

if __name__ == "__main__":
    proceed = run_test()
    sys.exit(0 if proceed else 1)
