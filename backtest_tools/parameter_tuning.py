#!/usr/bin/env python3
"""
Parameter Tuning Script for Iteration Optimization

Reads signals_fixed_dates.csv with cached LLM outputs and re-applies
trade_long logic with configurable parameters.

NO LOOKAHEAD: Uses only eps_surprise, earnings_day_return, direction_score
(all known at trade decision time).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd


def compute_risk(
    eps_surprise: Optional[float],
    earnings_day_return: Optional[float],
    pre_earnings_5d_return: Optional[float],
    risk_eps_miss_threshold: float = 0.0,
    risk_day_low: float = -3.0,
    risk_runup_high: float = 15.0,
    risk_runup_low: float = 5.0,
) -> str:
    """Compute risk level from market anchors."""
    # High risk conditions
    if eps_surprise is not None and eps_surprise <= risk_eps_miss_threshold:
        return "high"
    if earnings_day_return is not None and earnings_day_return < risk_day_low:
        return "high"
    if pre_earnings_5d_return is not None and pre_earnings_5d_return > risk_runup_high:
        return "high"

    # Low risk conditions
    eps_ok = eps_surprise is None or eps_surprise > 0
    day_ok = earnings_day_return is None or earnings_day_return > 0
    runup_ok = pre_earnings_5d_return is None or pre_earnings_5d_return < risk_runup_low

    if eps_ok and day_ok and runup_ok:
        return "low"

    return "medium"


def compute_vetoes(row: pd.Series) -> Tuple[int, int, int]:
    """Compute positives, hard vetoes, soft vetoes from LongEligible fields."""
    positive_fields = ["le_GuidanceRaised", "le_DemandAcceleration", "le_MarginExpansion",
                       "le_FCFImprovement", "le_VisibilityImproving"]
    hard_veto_fields = ["le_GuidanceCut"]  # Only GuidanceCut is hard veto
    soft_veto_fields = ["le_DemandSoftness", "le_MarginWeakness", "le_VisibilityWorsening", "le_CashBurn"]

    def _is_yes(val):
        return str(val).upper() == "YES"

    positives = sum(1 for f in positive_fields if _is_yes(row.get(f)))
    hard_vetoes = sum(1 for f in hard_veto_fields if _is_yes(row.get(f)))
    soft_vetoes = sum(1 for f in soft_veto_fields if _is_yes(row.get(f)))

    return positives, hard_vetoes, soft_vetoes


def compute_trade_long(
    row: pd.Series,
    params: Dict[str, Any],
) -> Tuple[bool, str, str]:
    """
    Compute trade_long based on configurable parameters.

    Returns: (trade_long, block_reason, tier)
    """
    direction_score = row.get("le_DirectionScore")
    if pd.isna(direction_score):
        return False, "NO_DIRECTION", ""

    direction_score = int(direction_score)
    sector = str(row.get("sector", "")).lower()

    # Get market anchors
    eps_surprise = row.get("eps_surprise") if pd.notna(row.get("eps_surprise")) else None
    earnings_day_ret = row.get("earnings_day_return") if pd.notna(row.get("earnings_day_return")) else None
    pre_5d = row.get("pre_earnings_5d_return") if pd.notna(row.get("pre_earnings_5d_return")) else None

    # Compute risk
    risk = compute_risk(
        eps_surprise, earnings_day_ret, pre_5d,
        risk_eps_miss_threshold=params.get("risk_eps_miss", 0.0),
        risk_day_low=params.get("risk_day_low", -3.0),
        risk_runup_high=params.get("risk_runup_high", 15.0),
    )

    # Compute vetoes
    positives, hard_vetoes, soft_vetoes = compute_vetoes(row)

    # Global gates
    if params.get("block_high_risk", True) and risk == "high":
        return False, "HIGH_RISK", ""

    if params.get("block_hard_vetoes", True) and hard_vetoes > 0:
        return False, "HARD_VETOES", ""

    # Sector exclusions
    is_energy = "energy" in sector
    is_materials = "material" in sector

    if is_energy and params.get("exclude_energy", False):
        return False, "ENERGY_EXCLUDED", ""
    if is_materials and params.get("exclude_materials", False):
        return False, "MATERIALS_EXCLUDED", ""

    # =========== D7 CORE ===========
    if direction_score >= 7 and params.get("d7_enabled", True):
        max_soft = params.get("d7_max_soft_vetoes", 1)
        if soft_vetoes > max_soft:
            return False, "D7_TOO_MANY_SOFT", ""

        min_eps = params.get("d7_min_eps", 0.0)
        if eps_surprise is None or eps_surprise < min_eps:
            return False, "D7_EPS_LOW", ""

        min_day = params.get("d7_min_day_ret", 1.0)
        if earnings_day_ret is None or earnings_day_ret < min_day:
            return False, "D7_DAY_LOW", ""

        return True, "", "D7_CORE"

    # =========== D6 STRICT ===========
    if direction_score >= 6 and params.get("d6_enabled", True):
        max_soft = params.get("d6_max_soft_vetoes", 2)
        if soft_vetoes > max_soft:
            return False, "D6_TOO_MANY_SOFT", ""

        # D6 sector exclusion
        d6_exclude = params.get("d6_exclude_sectors", ["technology"])
        if any(ex.lower() in sector for ex in d6_exclude):
            return False, "D6_SECTOR_EXCLUDED", ""

        # D6 requires low risk (or relaxed)
        if params.get("d6_require_low_risk", True) and risk != "low":
            return False, "D6_RISK_NOT_LOW", ""

        min_eps = params.get("d6_min_eps", 0.0)
        if eps_surprise is None or eps_surprise < min_eps:
            return False, "D6_EPS_LOW", ""

        min_pos = params.get("d6_min_positives", 1)
        if positives < min_pos:
            return False, "D6_POSITIVES_LOW", ""

        min_day = params.get("d6_min_day_ret", 0.5)
        if earnings_day_ret is None or earnings_day_ret < min_day:
            return False, "D6_DAY_LOW", ""

        return True, "", "D6_STRICT"

    # =========== D5 GATED ===========
    if direction_score >= 5 and params.get("d5_enabled", True):
        max_soft = params.get("d5_max_soft_vetoes", 2)
        if soft_vetoes > max_soft:
            return False, "D5_TOO_MANY_SOFT", ""

        min_pos = params.get("d5_min_positives", 1)
        if positives < min_pos:
            return False, "D5_POSITIVES_LOW", ""

        min_eps = params.get("d5_min_eps", 0.0)
        if eps_surprise is None or eps_surprise < min_eps:
            return False, "D5_EPS_LOW", ""

        return True, "", "D5_GATED"

    # =========== D4 ENTRY ===========
    if direction_score >= 4 and params.get("d4_enabled", True):
        max_soft = params.get("d4_max_soft_vetoes", 1)
        if soft_vetoes > max_soft:
            return False, "D4_TOO_MANY_SOFT", ""

        # D4 needs confirmation: positives >= 2 OR eps >= 2%
        has_pos = positives >= params.get("d4_min_positives", 2)
        has_eps = eps_surprise is not None and eps_surprise >= params.get("d4_min_eps", 0.02)
        if not (has_pos or has_eps):
            return False, "D4_NO_CONFIRM", ""

        return True, "", "D4_ENTRY"

    # =========== D3 WIDE ===========
    if direction_score >= 3 and params.get("d3_enabled", True):
        # D3 requires NO soft vetoes
        if soft_vetoes > 0:
            return False, "D3_HAS_SOFT", ""

        # D3 needs strong confirmation
        has_pos = positives >= params.get("d3_min_positives", 2)
        has_eps = eps_surprise is not None and eps_surprise >= params.get("d3_min_eps", 0.02)
        if not (has_pos or has_eps):
            return False, "D3_NO_CONFIRM", ""

        return True, "", "D3_WIDE"

    return False, "DIR_TOO_LOW", ""


def tune_signals(
    signals_df: pd.DataFrame,
    params: Dict[str, Any],
) -> pd.DataFrame:
    """Apply parameter tuning to signals DataFrame."""
    result = signals_df.copy()

    # Reset trade_long columns
    result["trade_long"] = False
    result["trade_long_tier"] = ""
    result["long_block_reason_new"] = ""

    for idx, row in result.iterrows():
        trade_long, reason, tier = compute_trade_long(row, params)
        result.at[idx, "trade_long"] = trade_long
        result.at[idx, "trade_long_tier"] = tier
        result.at[idx, "long_block_reason_new"] = reason

    return result


def analyze_results(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze tuning results."""
    total = len(df)
    trade_long_count = df["trade_long"].sum()

    tier_counts = df[df["trade_long"]]["trade_long_tier"].value_counts().to_dict()
    block_counts = df[~df["trade_long"]]["long_block_reason_new"].value_counts().head(10).to_dict()

    # Win rate analysis (NO LOOKAHEAD in decision, but OK for analysis)
    if "actual_return_30d_pct" in df.columns:
        trades = df[df["trade_long"]]
        if len(trades) > 0:
            wins = (trades["actual_return_30d_pct"] > 0).sum()
            win_rate = wins / len(trades)
            avg_return = trades["actual_return_30d_pct"].mean()
            median_return = trades["actual_return_30d_pct"].median()
        else:
            win_rate = avg_return = median_return = 0
    else:
        win_rate = avg_return = median_return = None

    return {
        "total_signals": total,
        "trade_long_count": int(trade_long_count),
        "trade_long_pct": trade_long_count / total * 100,
        "tier_counts": tier_counts,
        "block_reasons": block_counts,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "median_return": median_return,
        "params": params,
    }


# Predefined parameter presets
PRESETS = {
    "baseline": {
        "d7_enabled": True, "d7_min_eps": 0.0, "d7_min_day_ret": 1.5, "d7_max_soft_vetoes": 1,
        "d6_enabled": True, "d6_min_eps": 0.0, "d6_min_positives": 1, "d6_min_day_ret": 1.0,
        "d6_require_low_risk": True, "d6_exclude_sectors": ["technology"],
        "d5_enabled": False, "d4_enabled": False, "d3_enabled": False,
        "block_high_risk": True, "block_hard_vetoes": True,
        "risk_day_low": -3.0,
    },
    "iteration1": {
        # ChatGPT Pro Iteration 1 recommendations
        "d7_enabled": True, "d7_min_eps": 0.0, "d7_min_day_ret": 1.0, "d7_max_soft_vetoes": 1,
        "d6_enabled": True, "d6_min_eps": 0.005, "d6_min_positives": 1, "d6_min_day_ret": 0.5,
        "d6_require_low_risk": False, "d6_exclude_sectors": [],
        "d5_enabled": True, "d5_min_eps": 0.0, "d5_min_positives": 1, "d5_max_soft_vetoes": 2,
        "d4_enabled": True, "d4_min_eps": 0.02, "d4_min_positives": 2, "d4_max_soft_vetoes": 1,
        "d3_enabled": False,
        "block_high_risk": True, "block_hard_vetoes": True,
        "risk_day_low": -5.0,  # Relaxed from -3%
    },
    "iteration2": {
        # ChatGPT Pro Iteration 2: Tighten D4, re-enable D6 risk check
        "d7_enabled": True, "d7_min_eps": 0.0, "d7_min_day_ret": 1.0, "d7_max_soft_vetoes": 1,
        "d6_enabled": True, "d6_min_eps": 0.005, "d6_min_positives": 1, "d6_min_day_ret": 0.5,
        "d6_require_low_risk": True, "d6_exclude_sectors": [],  # Re-enabled low risk
        "d5_enabled": True, "d5_min_eps": 0.0, "d5_min_positives": 1, "d5_max_soft_vetoes": 2,
        "d4_enabled": True, "d4_min_eps": 0.03, "d4_min_positives": 3, "d4_max_soft_vetoes": 0,  # Tightened
        "d3_enabled": False,
        "block_high_risk": True, "block_hard_vetoes": True,
        "risk_day_low": -5.0,
    },
    "iteration3": {
        # ChatGPT Pro Iteration 3: Revert to Iter1 base + relax HIGH_RISK
        "d7_enabled": True, "d7_min_eps": 0.0, "d7_min_day_ret": 1.0, "d7_max_soft_vetoes": 1,
        "d6_enabled": True, "d6_min_eps": 0.005, "d6_min_positives": 1, "d6_min_day_ret": 0.5,
        "d6_require_low_risk": False, "d6_exclude_sectors": [],
        "d5_enabled": True, "d5_min_eps": 0.0, "d5_min_positives": 1, "d5_max_soft_vetoes": 2,
        "d4_enabled": True, "d4_min_eps": 0.02, "d4_min_positives": 2, "d4_max_soft_vetoes": 1,  # Back to Iter1
        "d3_enabled": True, "d3_min_eps": 0.0, "d3_min_positives": 2,  # Enable D3
        "block_high_risk": True, "block_hard_vetoes": True,
        "risk_eps_miss": -0.05,  # Allow 5% EPS miss (was 0)
        "risk_day_low": -7.0,    # Allow -7% day return (was -5%)
        "risk_runup_high": 20.0, # Allow 20% pre-runup (was 15%)
    },
    "aggressive": {
        # More aggressive: enable all tiers, relaxed risk
        "d7_enabled": True, "d7_min_eps": 0.0, "d7_min_day_ret": 0.5, "d7_max_soft_vetoes": 2,
        "d6_enabled": True, "d6_min_eps": 0.0, "d6_min_positives": 0, "d6_min_day_ret": 0.0,
        "d6_require_low_risk": False, "d6_exclude_sectors": [],
        "d5_enabled": True, "d5_min_eps": 0.0, "d5_min_positives": 0, "d5_max_soft_vetoes": 3,
        "d4_enabled": True, "d4_min_eps": 0.0, "d4_min_positives": 1, "d4_max_soft_vetoes": 2,
        "d3_enabled": True, "d3_min_eps": 0.0, "d3_min_positives": 1,
        "block_high_risk": False,  # Don't block high risk
        "block_hard_vetoes": True,
        "risk_day_low": -10.0,
    },
}


def main():
    ap = argparse.ArgumentParser(description="Parameter tuning for trade_long logic")
    ap.add_argument("--signals", default="signals_fixed_dates.csv", help="Input signals CSV")
    ap.add_argument("--preset", choices=list(PRESETS.keys()), help="Use predefined preset")
    ap.add_argument("--outdir", default="tuning_results", help="Output directory")
    ap.add_argument("--analyze-only", action="store_true", help="Only analyze, don't save")
    args = ap.parse_args()

    signals_path = Path(args.signals)
    if not signals_path.exists():
        signals_path = Path(__file__).parent / args.signals

    print(f"Loading signals from: {signals_path}")
    df = pd.read_csv(signals_path)
    print(f"Loaded {len(df)} signals")

    params = PRESETS.get(args.preset, PRESETS["baseline"])
    print(f"\nUsing preset: {args.preset or 'baseline'}")
    print(f"Parameters: {json.dumps(params, indent=2)}")

    # Apply tuning
    tuned_df = tune_signals(df, params)

    # Analyze
    analysis = analyze_results(tuned_df, params)

    print(f"\n=== Results ===")
    print(f"Trade Long Count: {analysis['trade_long_count']} ({analysis['trade_long_pct']:.1f}%)")
    print(f"Tier Distribution: {analysis['tier_counts']}")
    print(f"Top Block Reasons: {analysis['block_reasons']}")

    if analysis["win_rate"] is not None:
        print(f"\nBacktest Preview (NO LOOKAHEAD in decision):")
        print(f"  Win Rate: {analysis['win_rate']*100:.1f}%")
        print(f"  Avg Return: {analysis['avg_return']:.2f}%")
        print(f"  Median Return: {analysis['median_return']:.2f}%")

    if not args.analyze_only:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        preset_name = args.preset or "baseline"
        out_signals = outdir / f"signals_{preset_name}.csv"
        out_analysis = outdir / f"analysis_{preset_name}.json"

        # Save only trade_long=True signals for backtest
        backtest_signals = tuned_df[tuned_df["trade_long"]][["symbol", "reaction_date", "trade_long", "trade_long_tier"]].copy()
        backtest_signals.to_csv(out_signals, index=False)

        with open(out_analysis, "w") as f:
            json.dump(analysis, f, indent=2, default=str)

        print(f"\nSaved to: {outdir}")
        print(f"  - {out_signals.name}: {len(backtest_signals)} trade_long signals")
        print(f"  - {out_analysis.name}: analysis results")


if __name__ == "__main__":
    main()
