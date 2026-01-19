#!/usr/bin/env python3
"""
V10 Enhanced Scoring Module
===========================
Implements ChatGPT Pro's 10-iteration optimization recommendations for:
- CAGR > 35%
- Sharpe > 2

Key Features:
1. Continuous utility scoring (not hard thresholds)
2. Uncertainty-adjusted sizing (fractional Kelly)
3. Cost and reaction penalties
4. Reliability-weighted alpha
5. Dynamic deployment targeting
"""

import math
import os
from typing import Any, Dict, Optional, Tuple

# =============================================================================
# V10 Configuration Parameters (from ChatGPT Pro 10-iteration optimization)
# =============================================================================

# ChatGPT Pro Round 7: Global risk budget scaling
# With Round 6 MaxDD ~0.7% vs target <20%, we're under-risked.
# 3.0x is a reasonable first jump to move CAGR ~11.7% -> ~30% (subject to caps).
RISK_BUDGET_SCALE = float(os.getenv("V10_RISK_BUDGET_SCALE", "3.0"))

# ChatGPT Pro Round 9: Tier-specific max scale
# Updated based on tier performance in Round 8
TIER_MAX_SCALE = {
    "D7_CORE": 3.0,      # Best tier - scale winners
    "D6_STRICT": 1.8,    # Re-enabled with moderate scaling
    "D5_GATED": 2.5,     # Good tier - slightly reduced
    "D4_ENTRY": 1.6,     # Moderate scaling
    "D4_OPP": 0.9,       # Round 9: reduced from 1.0 (was dragging performance)
    "D3_WIDE": 0.7,      # Shrink
    "D3_PROBE": 0.6,     # New: very small probe tier
}

# ChatGPT Pro Round 8: Utility scale parameters (replace strength_factor)
# Maps utility -> [UTIL_MIN_SCALE, UTIL_MAX_SCALE] instead of [0.25, 1.0]
UTIL_MIN_SCALE = float(os.getenv("V10_UTIL_MIN_SCALE", "1.0"))  # Never shrink below base
UTIL_MAX_SCALE = float(os.getenv("V10_UTIL_MAX_SCALE", "1.0"))  # Set to 1.0 to disable utility scaling for now
UTIL_MID = float(os.getenv("V10_UTIL_MID", "0.0"))  # Center point for utility sigmoid
UTIL_STEEPNESS = float(os.getenv("V10_UTIL_STEEPNESS", "1.0"))  # Steepness of sigmoid

# ChatGPT Pro Round 7: Dynamic sizing adjustments (kept for reference but may be modified)
DIR_BONUS_PER_POINT = float(os.getenv("V10_DIR_BONUS_PER_POINT", "0.06"))  # +6% size per DIR above tier min
SOFT_VETO_PENALTY_PER_POINT = float(os.getenv("V10_SOFT_VETO_PENALTY_PER_POINT", "0.12"))  # -12% size per soft veto
CONFIRM_BONUS = float(os.getenv("V10_CONFIRM_BONUS", "0.08"))  # +8% if confirmation present
HIGH_RISK_MULT = float(os.getenv("V10_HIGH_RISK_MULT", "0.60"))  # cut size if HIGH_RISK flagged

# Uncertainty penalty
# ChatGPT Pro Round 4: K_U *= 1.25 to boost alpha term
K_U = float(os.getenv("V10_K_U", "1.75"))  # Uncertainty penalty coefficient (was 1.4, now 1.4*1.25=1.75)
SIGMA_FLOOR = float(os.getenv("V10_SIGMA_FLOOR", "0.045"))  # 4.5% minimum volatility

# Risk and contradiction penalties
# ChatGPT Pro Round 4: K_R *= 0.60, K_C *= 0.75 to reduce penalty dominance
K_R = float(os.getenv("V10_K_R", "0.33"))  # Risk flag penalty (was 0.55, now 0.55*0.60=0.33)
K_C = float(os.getenv("V10_K_C", "0.34"))  # Contradiction penalty (was 0.45, now 0.45*0.75=0.34)

# Cost model coefficients
COST_B0 = float(os.getenv("V10_COST_B0", "6"))  # Base cost (bps)
COST_B1 = float(os.getenv("V10_COST_B1", "0.35"))  # Spread multiplier
COST_B2 = float(os.getenv("V10_COST_B2", "18"))  # Impact coefficient

# Reaction clip (avoid chasing)
REACTION_CLIP = float(os.getenv("V10_REACTION_CLIP", "0.08"))  # 8%

# Sizing parameters (fractional Kelly)
# ChatGPT Pro Round 2: Tier-based Kelly multipliers for better risk control
K_KELLY_BASE = float(os.getenv("V10_K_KELLY_BASE", "1.0"))  # Base Kelly fraction

# Tier-specific Kelly multipliers and max positions (ChatGPT Pro Round 2/4)
# Round 8: Added D8_MEGA tier with higher multiplier
D8_KELLY_MULT = float(os.getenv("V10_D8_KELLY_MULT", "1.20"))  # D8_MEGA: 120% (NEW - Round 8)
D7_KELLY_MULT = float(os.getenv("V10_D7_KELLY_MULT", "1.10"))  # D7_CORE: 110%
D6_KELLY_MULT = float(os.getenv("V10_D6_KELLY_MULT", "1.00"))  # D6_STRICT: 100% (Round 4: increased since D6 outperforms)
D5_KELLY_MULT = float(os.getenv("V10_D5_KELLY_MULT", "0.75"))  # D5_GATED: 75%
D4_KELLY_MULT = float(os.getenv("V10_D4_KELLY_MULT", "0.50"))  # D4_ENTRY: 50%
D4_OPP_KELLY_MULT = float(os.getenv("V10_D4_OPP_KELLY_MULT", "0.60"))  # D4_OPP: 60% (Round 5: new tier for PAYC-type)
D3_KELLY_MULT = float(os.getenv("V10_D3_KELLY_MULT", "0.35"))  # D3_WIDE: 35% (Round 4: new tier)

# Tier-specific max positions
# Round 10: D7_MAX_POS increased to 40% (was 25%), becomes new MAX_POSITION_SIZE
D8_MAX_POS = float(os.getenv("V10_D8_MAX_POS", "0.50"))  # D8_MEGA: 50% (NEW - Round 8)
D7_MAX_POS = float(os.getenv("V10_D7_MAX_POS", "0.40"))  # D7: 40% (Round 10: was 25%)
D6_MAX_POS = float(os.getenv("V10_D6_MAX_POS", "0.30"))  # D6: 30% (Round 10: was 18%)
D5_MAX_POS = float(os.getenv("V10_D5_MAX_POS", "0.20"))  # D5: 20% (Round 10: was 18%)
D4_MAX_POS = float(os.getenv("V10_D4_MAX_POS", "0.15"))  # D4_ENTRY: 15% (unchanged)
D4_OPP_MAX_POS = float(os.getenv("V10_D4_OPP_MAX_POS", "0.18"))  # D4_OPP: 18% (was 6%)
D3_MAX_POS = float(os.getenv("V10_D3_MAX_POS", "0.08"))  # D3: 8% (was 4%)

# Tier-specific min positions (ChatGPT Pro Round 7: increased floors)
# Round 8: Added D8_MEGA tier
D8_MIN_POS = float(os.getenv("V10_D8_MIN_POS", "0.12"))  # D8_MEGA: min 12% (NEW - Round 8)
D7_MIN_POS = float(os.getenv("V10_D7_MIN_POS", "0.10"))  # D7: min 10% (was 3%)
D6_MIN_POS = float(os.getenv("V10_D6_MIN_POS", "0.06"))  # D6: min 6% (was 2.5%)
D5_MIN_POS = float(os.getenv("V10_D5_MIN_POS", "0.06"))  # D5: min 6% (was 2%)
D4_MIN_POS = float(os.getenv("V10_D4_MIN_POS", "0.04"))  # D4_ENTRY: min 4% (was 1%)
D4_OPP_MIN_POS = float(os.getenv("V10_D4_OPP_MIN_POS", "0.04"))  # D4_OPP: min 4% (was 1.5%)
D3_MIN_POS = float(os.getenv("V10_D3_MIN_POS", "0.03"))  # D3: min 3% (was 0.5%)

# Tier-specific base positions (ChatGPT Pro Round 9: updated based on tier performance)
# Round 8: Added D8_MEGA tier
D8_BASE_POS = float(os.getenv("V10_D8_BASE_POS", "0.12"))  # D8_MEGA: base 12% (NEW - Round 8)
D7_BASE_POS = float(os.getenv("V10_D7_BASE_POS", "0.105"))  # R4: 10.5% (was 11%) → 26.25% after 2.5x scale
D6_BASE_POS = float(os.getenv("V10_D6_BASE_POS", "0.0"))  # R4: 0% - D6 disabled
D5_BASE_POS = float(os.getenv("V10_D5_BASE_POS", "0.075"))  # R3: 7.5% (was 9%) → 18.75% after 2.5x scale
D4_BASE_POS = float(os.getenv("V10_D4_BASE_POS", "0.05"))  # D4_ENTRY: base 5% (unchanged)
D4_OPP_BASE_POS = float(os.getenv("V10_D4_OPP_BASE_POS", "0.035"))  # D4_OPP: base 3.5% (was 6% - REDUCED)
D3_BASE_POS = float(os.getenv("V10_D3_BASE_POS", "0.03"))  # D3: base 3% (was 4%)
D3_PROBE_BASE_POS = float(os.getenv("V10_D3_PROBE_BASE_POS", "0.02"))  # D3_PROBE: base 2% (NEW)

# Direction hard floor (ChatGPT Pro Round 4: only block DIR <= 2)
DIR_HARD_FLOOR = int(os.getenv("V10_DIR_HARD_FLOOR", "2"))

# Sigmoid mapping parameters (ChatGPT Pro Round 3: ensures non-negative sizing)
SIGMOID_SLOPE = float(os.getenv("V10_SIGMOID_SLOPE", "5.0"))  # Slope S
SIGMOID_CENTER = float(os.getenv("V10_SIGMOID_CENTER", "0.0"))  # Center U0
UTILITY_HARD_CUTOFF = float(os.getenv("V10_UTILITY_CUTOFF", "-0.75"))  # Below this: no trade

# ChatGPT Pro Round 5: Tier-specific utility floors (to filter out low-quality trades)
D6_MIN_UTILITY = float(os.getenv("V10_D6_MIN_UTILITY", "-0.10"))  # D6: utility must be > -0.10
D4_OPP_MIN_UTILITY = float(os.getenv("V10_D4_OPP_MIN_UTILITY", "-0.20"))  # D4_OPP: utility must be > -0.20

# ChatGPT Pro Round 5: D6 quality gate as soft penalty instead of hard block
D6_QUALITY_PENALTY_MULT = float(os.getenv("V10_D6_QUALITY_PENALTY_MULT", "0.65"))  # 65% size when quality gate fails
D6_QUALITY_FLOOR = float(os.getenv("V10_D6_QUALITY_FLOOR", "0.045"))  # Hard floor at 4.5% even with penalty

# ChatGPT Pro Round 9: D6 re-enabled with tighter constraints
D6_ENABLED = os.getenv("V10_D6_ENABLED", "1") == "1"  # Re-enabled by default

# ChatGPT Pro Round 9: Min utility thresholds per tier (filter out low-quality trades)
D7_MIN_UTILITY = float(os.getenv("V10_D7_MIN_UTILITY", "0.60"))
D6_MIN_UTILITY_R9 = float(os.getenv("V10_D6_MIN_UTILITY_R9", "0.58"))
D5_MIN_UTILITY = float(os.getenv("V10_D5_MIN_UTILITY", "0.56"))
D4_ENTRY_MIN_UTILITY = float(os.getenv("V10_D4_ENTRY_MIN_UTILITY", "0.54"))
D4_OPP_MIN_UTILITY_R9 = float(os.getenv("V10_D4_OPP_MIN_UTILITY_R9", "0.58"))  # Tighter than before
D3_WIDE_MIN_UTILITY = float(os.getenv("V10_D3_WIDE_MIN_UTILITY", "0.60"))
D3_PROBE_MIN_UTILITY = float(os.getenv("V10_D3_PROBE_MIN_UTILITY", "0.62"))

# ChatGPT Pro Round 9: D4_OPP now requires confirmation (was optional before)
D4_OPP_REQUIRE_CONFIRMATION = os.getenv("V10_D4_OPP_REQUIRE_CONFIRMATION", "1") == "1"

# ChatGPT Pro Round 10: Critical fixes for utility inversion
# The reaction penalty was SUBTRACTING earnings moves, but momentum says moves CONTINUE
# Solution: Make reaction DIRECTION-ALIGNED (add if aligned, subtract if misaligned)
ENABLE_D4_OPP = os.getenv("V10_ENABLE_D4_OPP", "0") == "1"  # DISABLED - negative expectancy
ENABLE_D3_WIDE = os.getenv("V10_ENABLE_D3_WIDE", "0") == "1"  # DISABLED - focus on D6/D7
USE_UTILITY_GATE = os.getenv("V10_USE_UTILITY_GATE", "0") == "1"  # DISABLED - utility is backwards
MIN_DIRECTION_TO_TRADE = int(os.getenv("V10_MIN_DIRECTION_TO_TRADE", "6"))  # Focus on D6+ only
REACTION_MODE = os.getenv("V10_REACTION_MODE", "MOMENTUM_ALIGNED")  # NEW: aligned with direction
REACTION_WEIGHT = float(os.getenv("V10_REACTION_WEIGHT", "0.60"))  # Weight for reaction term
REACTION_MISMATCH_BLOCK = float(os.getenv("V10_REACTION_MISMATCH_BLOCK", "0.06"))  # Block if 6%+ opposite

# ChatGPT Pro Round 11: Enable D5_GATED with momentum alignment
# ChatGPT Pro Round 12 (R2): Stricter gating - MIN_DIRECTION=6 to reduce marginal trades
ENABLE_D5_GATED = os.getenv("V10_ENABLE_D5_GATED", "1") == "1"  # Enabled but requires DIR>=6
MIN_DIRECTION_TO_TRADE_R11 = int(os.getenv("V10_MIN_DIRECTION_TO_TRADE_R11", "6"))  # R2: raised from 5 to 6

# ChatGPT Pro Round 14 (R4): D6 formally disabled (unreachable threshold)
D6_MIN_DIRECTION_TO_TRADE = int(os.getenv("V10_D6_MIN_DIRECTION_TO_TRADE", "999"))  # R4: D6 disabled

# ChatGPT Pro Round 15 (R5): Tighter tail-loss limiter - tightened from -18% to -15%
HARD_STOP_LOSS_PCT = float(os.getenv("V10_HARD_STOP_LOSS_PCT", "-0.15"))  # R5: -15% hard stop (was -18%)

# ChatGPT Pro Round 11: Sector-specific blocks
# D6 Tech: WDAY lost -9.33%, but ORCL (D7 Tech) +40.44% - so only block D6 Tech, not D7
# D6 Healthcare: 0% WR in OOS sample (BSX -2.18%, RMD -0.28% as D7)
D6_BLOCKED_SECTORS = os.getenv("V10_D6_BLOCKED_SECTORS", "Technology,Healthcare").split(",")

# ChatGPT Pro Round 12 (R2): D7 sector blocks - Real Estate underperforms (BXP -21.49%)
D7_BLOCKED_SECTORS = os.getenv("V10_D7_BLOCKED_SECTORS", "Real Estate").split(",")

# ChatGPT Pro Round 11: D5 requires momentum alignment (earnings move >= +3% aligned with direction)
# ChatGPT Pro Round 12 (R2): Raised to 4% to be more selective
D5_MIN_ALIGNED_MOVE = float(os.getenv("V10_D5_MIN_ALIGNED_MOVE", "0.04"))  # R2: 4% minimum aligned move (was 3%)

# ChatGPT Pro Round 11: Position size scale factor to achieve CAGR >30%
# Round 10: Reduced from 5.5 to 5.0 for better Sharpe ratio (target >2.0)
POSITION_SCALE = float(os.getenv("V10_POSITION_SCALE", "5.0"))

# Soft veto penalty (ChatGPT Pro Round 2: gentler 0.90 with floor)
SOFT_VETO_PENALTY = float(os.getenv("V10_SOFT_VETO_PENALTY", "0.90"))  # 0.90x per soft veto (was 0.85)
SOFT_VETO_FLOOR = float(os.getenv("V10_SOFT_VETO_FLOOR", "0.70"))  # Min multiplier floor

# Legacy compatibility
D7_MULTIPLIER = D7_KELLY_MULT
D6_MULTIPLIER = D6_KELLY_MULT
D5_MULTIPLIER = D5_KELLY_MULT
MAX_POSITION_SIZE = D7_MAX_POS  # Default to highest tier

# Deployment targets
TARGET_GROSS_BASE = float(os.getenv("V10_TARGET_GROSS", "0.60"))  # 60% target exposure
MIN_ENB = int(os.getenv("V10_MIN_ENB", "12"))  # Minimum effective number of bets

# Quality gates
MIN_EVIDENCE_D6 = float(os.getenv("V10_MIN_EVIDENCE_D6", "0.70"))
MIN_EVIDENCE_D7 = float(os.getenv("V10_MIN_EVIDENCE_D7", "0.60"))
MAX_CONTRADICTION_D6 = float(os.getenv("V10_MAX_CONTRADICTION_D6", "0.25"))
MAX_CONTRADICTION_D7 = float(os.getenv("V10_MAX_CONTRADICTION_D7", "0.40"))
MIN_NUMERIC_D6 = float(os.getenv("V10_MIN_NUMERIC_D6", "0.55"))
MIN_NUMERIC_D7 = float(os.getenv("V10_MIN_NUMERIC_D7", "0.40"))


def compute_evidence_score(long_json: Optional[Dict[str, Any]]) -> float:
    """
    Compute evidence score from LLM output quality indicators.

    Evidence score measures how well-supported the conclusions are:
    - Presence of numeric data (guidance ranges, margin numbers)
    - Explicit positive/negative signals with reasoning
    - Consistency between different parts of the analysis

    Returns: float 0.0-1.0
    """
    if not long_json:
        return 0.0

    score = 0.0
    max_score = 0.0

    # Check for DirectionScore presence and validity
    direction_score = long_json.get("DirectionScore")
    if direction_score is not None:
        max_score += 0.2
        if 1 <= int(direction_score) <= 10:
            score += 0.2

    # Check for positive/negative signals with YES/NO values
    positive_fields = ["GuidanceRaised", "DemandAcceleration", "MarginExpansion",
                       "FCFImprovement", "VisibilityImproving"]
    negative_fields = ["GuidanceCut", "DemandSoftness", "MarginWeakness",
                       "CashBurn", "VisibilityWorsening"]

    # Count how many fields have explicit YES/NO (not missing)
    explicit_count = 0
    for field in positive_fields + negative_fields:
        max_score += 0.06
        val = str(long_json.get(field, "")).upper()
        if val in ["YES", "NO"]:
            score += 0.06
            explicit_count += 1

    # Bonus for having multiple explicit signals (consistency indicator)
    if explicit_count >= 8:
        score += 0.1
    elif explicit_count >= 5:
        score += 0.05
    max_score += 0.1

    # Normalize to 0-1
    return min(1.0, score / max_score) if max_score > 0 else 0.0


def compute_contradiction_score(long_json: Optional[Dict[str, Any]]) -> float:
    """
    Compute contradiction score - measures internal inconsistency.

    High contradiction means the analysis has conflicting signals,
    which reduces reliability and should reduce position size.

    Returns: float 0.0-1.0 (higher = more contradictions = worse)
    """
    if not long_json:
        return 1.0  # No data = maximum uncertainty

    contradictions = 0
    checks = 0

    # Check for contradictory positive/negative pairs
    contradiction_pairs = [
        ("GuidanceRaised", "GuidanceCut"),
        ("DemandAcceleration", "DemandSoftness"),
        ("MarginExpansion", "MarginWeakness"),
        ("FCFImprovement", "CashBurn"),
        ("VisibilityImproving", "VisibilityWorsening"),
    ]

    for pos_field, neg_field in contradiction_pairs:
        pos_val = str(long_json.get(pos_field, "")).upper()
        neg_val = str(long_json.get(neg_field, "")).upper()

        checks += 1
        # Both YES = contradiction
        if pos_val == "YES" and neg_val == "YES":
            contradictions += 1

    # Check direction score vs overall signal consistency
    direction_score = int(long_json.get("DirectionScore", 5))
    positives = sum(1 for f in ["GuidanceRaised", "DemandAcceleration", "MarginExpansion",
                                 "FCFImprovement", "VisibilityImproving"]
                    if str(long_json.get(f, "")).upper() == "YES")
    negatives = sum(1 for f in ["GuidanceCut", "DemandSoftness", "MarginWeakness",
                                 "CashBurn", "VisibilityWorsening"]
                    if str(long_json.get(f, "")).upper() == "YES")

    checks += 1
    # High direction score but many negatives = contradiction
    if direction_score >= 7 and negatives >= 2:
        contradictions += 1
    # Low direction score but many positives = contradiction
    if direction_score <= 4 and positives >= 2:
        contradictions += 1

    return contradictions / checks if checks > 0 else 0.0


def compute_numeric_coverage(long_json: Optional[Dict[str, Any]]) -> float:
    """
    Compute numeric coverage - measures presence of quantitative data.

    Higher numeric coverage means the analysis is based on concrete numbers
    rather than vague qualitative assessments.

    Returns: float 0.0-1.0
    """
    if not long_json:
        return 0.0

    # For now, use a heuristic based on field completeness
    # In full implementation, this would parse actual numeric values from transcript

    total_fields = 0
    filled_fields = 0

    key_fields = ["DirectionScore", "GuidanceRaised", "DemandAcceleration",
                  "MarginExpansion", "FCFImprovement", "VisibilityImproving",
                  "GuidanceCut", "DemandSoftness", "MarginWeakness",
                  "CashBurn", "VisibilityWorsening"]

    for field in key_fields:
        total_fields += 1
        val = long_json.get(field)
        if val is not None and str(val).upper() not in ["", "NA", "N/A", "NONE"]:
            filled_fields += 1

    return filled_fields / total_fields if total_fields > 0 else 0.0


def compute_reliability_score(
    evidence_score: float,
    contradiction_score: float,
    numeric_coverage: float,
    consistency: float = 0.8  # Default assumption if not computed
) -> float:
    """
    Compute overall reliability score.

    Reliability = how much we trust this signal for sizing decisions.

    Formula (V10): rel = 0.35*consistency + 0.35*evidence + 0.15*numeric + 0.15*(1-contradiction)
    """
    return (
        0.35 * consistency +
        0.35 * evidence_score +
        0.15 * numeric_coverage +
        0.15 * (1.0 - contradiction_score)
    )


def estimate_cost_bps(
    adv_usd: Optional[float] = None,
    spread_bps: Optional[float] = None,
    trade_usd: float = 50000  # Default trade size
) -> float:
    """
    Estimate transaction cost in basis points.

    Formula (V10): cost_bps = b0 + b1*spread + b2*(trade$/ADV$)
    """
    # Default values if not provided
    if adv_usd is None:
        adv_usd = 20_000_000  # $20M default ADV
    if spread_bps is None:
        spread_bps = 10  # 10 bps default spread

    impact = trade_usd / adv_usd if adv_usd > 0 else 0.01

    cost = COST_B0 + COST_B1 * spread_bps + COST_B2 * impact
    return cost


def compute_reaction_term(
    pre_entry_return: Optional[float],
    direction: str = "LONG",
    clip: float = REACTION_CLIP,
    weight: float = REACTION_WEIGHT,
    mode: str = REACTION_MODE
) -> float:
    """
    ChatGPT Pro Round 10: Momentum-aligned reaction term.

    OLD (buggy): Always subtract reaction, penalizing winning momentum plays.
    NEW: If earnings move aligns with trade direction, BOOST utility. If misaligned, PENALIZE.

    Args:
        pre_entry_return: Earnings day return (positive = stock went up)
        direction: "LONG" or "SHORT"
        clip: Maximum reaction term magnitude
        weight: Scaling factor
        mode: "MOMENTUM_ALIGNED" (new) or "PENALTY" (old behavior)

    Returns:
        reaction_term to ADD to mu_raw (can be positive or negative)
    """
    if pre_entry_return is None:
        return 0.0

    if mode == "MOMENTUM_ALIGNED":
        # Direction sign: +1 for LONG, -1 for SHORT
        d = 1 if str(direction).upper() == "LONG" else -1

        # Aligned move: positive if earnings move aligns with trade direction
        # LONG + positive earnings = good (positive aligned_move)
        # LONG + negative earnings = bad (negative aligned_move)
        # SHORT + negative earnings = good (positive aligned_move)
        # SHORT + positive earnings = bad (negative aligned_move)
        aligned_move = d * pre_entry_return

        # Scale and clip
        reaction_term = aligned_move * weight
        reaction_term = max(-clip, min(clip, reaction_term))

        return reaction_term
    else:
        # Legacy penalty mode (always subtracts)
        clipped = max(-clip, min(clip, pre_entry_return))
        return -clipped  # Negative because caller adds this


def compute_reaction_penalty(
    pre_entry_return: Optional[float],
    clip: float = REACTION_CLIP
) -> float:
    """
    Legacy wrapper - use compute_reaction_term() instead.
    Kept for backwards compatibility.
    """
    return compute_reaction_term(pre_entry_return, "LONG", clip, 1.0, "PENALTY") * -1


def passes_reaction_alignment_gate(
    pre_entry_return: Optional[float],
    direction: str = "LONG",
    mismatch_threshold: float = REACTION_MISMATCH_BLOCK
) -> Tuple[bool, str]:
    """
    ChatGPT Pro Round 10: Block trades where earnings move strongly opposes direction.

    If you want to go LONG but the stock dropped 6%+ on earnings, skip.
    If you want to go SHORT but the stock rose 6%+ on earnings, skip.

    Args:
        pre_entry_return: Earnings day return (percentage as decimal, e.g., 0.10 = 10%)
        direction: "LONG" or "SHORT"
        mismatch_threshold: Block if aligned_move <= -threshold

    Returns:
        (passes, reason): (True, "") if passes, (False, "REACTION_MISMATCH") if blocked
    """
    if pre_entry_return is None:
        return (True, "")

    d = 1 if str(direction).upper() == "LONG" else -1
    aligned_move = d * pre_entry_return

    # If earnings reaction is meaningfully against your direction, skip
    if aligned_move <= -mismatch_threshold:
        return (False, "REACTION_MISMATCH")

    return (True, "")


def compute_v10_utility(
    mu_raw: float,
    sigma: float,
    uncertainty: float,
    risk_flag: float,
    contradiction: float,
    reliability: float,
    reaction_penalty: float = 0.0,
    cost_bps: float = 0.0
) -> float:
    """
    Compute V10 utility score for ranking and selection.

    Formula (V10):
        mu_net = mu_raw - reaction_penalty - cost/10000
        denom = sqrt(sigma^2 + (k_u * uncertainty)^2 + sigma_floor^2)
        score_raw = (mu_net * reliability) / denom
        utility = clip(score_raw, -3, 3) - k_r*risk_flag - k_c*contradiction
    """
    # Compute net expected return
    mu_net = mu_raw - reaction_penalty - (cost_bps / 10000)

    # Compute denominator with uncertainty penalty
    denom = math.sqrt(
        sigma ** 2 +
        (K_U * uncertainty) ** 2 +
        SIGMA_FLOOR ** 2
    )

    # Compute raw score with reliability adjustment
    if denom > 0:
        score_raw = (mu_net * reliability) / denom
    else:
        score_raw = 0.0

    # Clip and apply penalties
    score_clipped = max(-3.0, min(3.0, score_raw))
    utility = score_clipped - K_R * risk_flag - K_C * contradiction

    return utility


def dir_mult(dir_score: int) -> float:
    """
    Direction multiplier for position sizing (ChatGPT Pro Round 4).
    Makes DIR a continuous size scaler rather than a kill-switch.

    DIR=4 => ~0.50, DIR=3 => ~0.22, DIR=6 => ~0.92, DIR=7 => ~0.97
    """
    sigmoid_arg = 1.25 * (dir_score - 4.0)
    return 1.0 / (1.0 + math.exp(-sigmoid_arg))


def utility_scale(utility: float, min_scale: float = UTIL_MIN_SCALE,
                  max_scale: float = UTIL_MAX_SCALE) -> float:
    """
    ChatGPT Pro Round 8: Maps utility -> [min_scale, max_scale] smoothly.

    Key difference from Round 7's strength_factor:
    - Round 7: multiplied by (0.25 + 0.75*sigmoid) -> could shrink to 0.25x
    - Round 8: maps to [1.0, 3.0] -> never shrinks below 1x base

    This fixes the regression where 3x scaling was being canceled out.
    """
    if utility is None or min_scale >= max_scale:
        return 1.0

    # Sigmoid centered at UTIL_MID with steepness UTIL_STEEPNESS
    u = (utility - UTIL_MID) * UTIL_STEEPNESS
    s = 1.0 / (1.0 + math.exp(-u))  # 0..1

    return min_scale + (max_scale - min_scale) * s


def compute_v10_position_size(
    utility: float,
    tier: str,
    mu_hat: float,
    sigma_hat: float,
    uncertainty_hat: float,
    soft_veto_count: int = 0,
    direction_score: int = 5,
    has_confirmation: bool = False,
    high_risk: bool = False
) -> float:
    """
    Compute V10 position size using fractional Kelly with uncertainty discount.

    ChatGPT Pro Round 7 Updates:
    - RISK_BUDGET_SCALE = 3.0 to use unused MaxDD headroom
    - DIR_BONUS_PER_POINT: +6% size per DIR above tier min
    - SOFT_VETO_PENALTY_PER_POINT: -12% size per soft veto
    - CONFIRM_BONUS: +8% if confirmation present
    - HIGH_RISK_MULT: 0.60x if high_risk flagged
    - Significantly increased min/max position bounds

    ChatGPT Pro Round 4 Updates:
    - Direction multiplier: dir_mult = sigmoid(1.25 * (DIR - 4))
    - D3_WIDE tier with 0.5-4% sizing
    - Position = base * strength * dir_mult * risk_mult
    - Increased D6 caps since D6 outperforms D7

    Formula (V10 Round 7):
        pos = base_pos * RISK_BUDGET_SCALE
        pos *= (1 + DIR_BONUS * max(0, dir - tier_min_dir))
        pos *= (1 - SOFT_VETO_PENALTY * soft_veto_count)
        pos *= (1 + CONFIRM_BONUS) if has_confirmation
        pos *= HIGH_RISK_MULT if high_risk
        final_weight = clip(pos, min_pos, max_pos)
    """
    # Hard cutoff: only block extremely negative utility (ChatGPT Pro Round 3)
    if sigma_hat <= 0 or utility < UTILITY_HARD_CUTOFF:
        return 0.0

    # Tier-specific multipliers, max, min and base positions (Round 7)
    # Round 8: Added D8_MEGA tier
    tier_min_dir = 5  # Default tier minimum direction
    if tier == "D8_MEGA":
        kelly_mult = D8_KELLY_MULT
        max_pos = D8_MAX_POS
        min_pos = D8_MIN_POS
        base_pos = D8_BASE_POS
        tier_min_dir = 7  # Same as D7
    elif tier == "D7_CORE":
        kelly_mult = D7_KELLY_MULT
        max_pos = D7_MAX_POS
        min_pos = D7_MIN_POS
        base_pos = D7_BASE_POS
        tier_min_dir = 7
    elif tier == "D6_CORE" or tier == "D6_STRICT":
        kelly_mult = D6_KELLY_MULT
        max_pos = D6_MAX_POS
        min_pos = D6_MIN_POS
        base_pos = D6_BASE_POS
        tier_min_dir = 6
    elif tier == "D5_GATED":
        kelly_mult = D5_KELLY_MULT
        max_pos = D5_MAX_POS
        min_pos = D5_MIN_POS
        base_pos = D5_BASE_POS
        tier_min_dir = 5
    elif tier == "D4_ENTRY":
        kelly_mult = D4_KELLY_MULT
        max_pos = D4_MAX_POS
        min_pos = D4_MIN_POS
        base_pos = D4_BASE_POS
        tier_min_dir = 4
    elif tier == "D4_OPP":
        kelly_mult = D4_OPP_KELLY_MULT
        max_pos = D4_OPP_MAX_POS
        min_pos = D4_OPP_MIN_POS
        base_pos = D4_OPP_BASE_POS
        tier_min_dir = 4
    elif tier == "D3_WIDE":
        kelly_mult = D3_KELLY_MULT
        max_pos = D3_MAX_POS
        min_pos = D3_MIN_POS
        base_pos = D3_BASE_POS
        tier_min_dir = 3
    elif tier == "D3_PROBE":
        # ChatGPT Pro Round 9: Very small probe tier for high DIR blocked by soft vetoes
        kelly_mult = D3_KELLY_MULT * 0.5  # Half of D3_WIDE
        max_pos = 0.04  # Max 4%
        min_pos = 0.01  # Min 1%
        base_pos = D3_PROBE_BASE_POS  # 2%
        tier_min_dir = 6  # High DIR requirement for probe
    else:
        kelly_mult = D7_KELLY_MULT  # Default
        max_pos = D7_MAX_POS
        min_pos = D7_MIN_POS
        base_pos = D7_BASE_POS
        tier_min_dir = 7

    # ChatGPT Pro Round 8: Get tier-specific max scale (don't over-scale losing tiers)
    tier_max_scale = TIER_MAX_SCALE.get(tier, 1.0)

    # ChatGPT Pro Round 8: Use utility_scale() to get [1.0, tier_max_scale] multiplier
    # Key fix: Round 7's strength_factor (0.25-1.0) was CANCELING OUT the 3x RISK_BUDGET_SCALE
    # Round 8: utility_scale maps to [1.0, tier_max_scale] so it NEVER shrinks below base
    u_scale = utility_scale(utility, min_scale=1.0, max_scale=tier_max_scale)

    # Start from base position, apply tier-limited utility scaling
    pos = base_pos * u_scale

    # Round 7: DIR bonus for DIR above tier minimum
    dir_excess = max(0, direction_score - tier_min_dir)
    pos *= (1.0 + DIR_BONUS_PER_POINT * dir_excess)

    # Round 7: Soft veto penalty (even if allowed by gate)
    pos *= (1.0 - SOFT_VETO_PENALTY_PER_POINT * max(0, soft_veto_count))

    # Round 7: Confirmation bonus
    if has_confirmation:
        pos *= (1.0 + CONFIRM_BONUS)

    # Round 7: High risk multiplier
    if high_risk:
        pos *= HIGH_RISK_MULT

    # ChatGPT Pro Round 11: Apply position scale factor to achieve CAGR >30%
    pos *= POSITION_SCALE

    # Clip to tier-specific bounds with min floor (scaled)
    scaled_min = min_pos * POSITION_SCALE
    scaled_max = max_pos * POSITION_SCALE
    final_weight = max(scaled_min, min(pos, scaled_max))

    return final_weight


def compute_v10_trade_signal(
    long_json: Optional[Dict[str, Any]],
    sector: Optional[str] = None,
    market_anchors: Optional[Dict[str, Any]] = None,
    sigma_20d: float = 0.02,  # Default 2% daily vol = ~32% annual
    pre_entry_return: float = 0.0,
    adv_usd: Optional[float] = None
) -> Dict[str, Any]:
    """
    Compute V10 enhanced trade signal with utility scoring.

    Returns comprehensive signal dict with:
    - trade_long: bool
    - tier: str (D6_CORE, D7_CORE, or empty)
    - utility: float (continuous score for ranking)
    - position_size: float (recommended position size 0-5%)
    - all intermediate scores for debugging/analysis
    """
    result = {
        "trade_long": False,
        "tier": "",
        "block_reason": "",
        "utility": 0.0,
        "position_size": 0.0,
        # Intermediate scores
        "evidence_score": 0.0,
        "contradiction_score": 1.0,
        "numeric_coverage": 0.0,
        "reliability_score": 0.0,
        "risk_flag": 1.0,
        "reaction_penalty": 0.0,
        "cost_bps": 0.0,
        "mu_raw": 0.0,
        "sigma": sigma_20d,
        "uncertainty": 1.0,
    }

    if not long_json:
        result["block_reason"] = "NO_JSON"
        return result

    # Extract direction score
    try:
        direction_score = int(long_json.get("DirectionScore", 0))
    except (ValueError, TypeError):
        result["block_reason"] = "INVALID_DIRECTION"
        return result

    # Compute quality scores
    evidence_score = compute_evidence_score(long_json)
    contradiction_score = compute_contradiction_score(long_json)
    numeric_coverage = compute_numeric_coverage(long_json)
    reliability_score = compute_reliability_score(
        evidence_score, contradiction_score, numeric_coverage
    )

    result["evidence_score"] = evidence_score
    result["contradiction_score"] = contradiction_score
    result["numeric_coverage"] = numeric_coverage
    result["reliability_score"] = reliability_score

    # Compute risk from market anchors
    risk_flag = 0.0
    if market_anchors:
        eps_surprise = market_anchors.get("eps_surprise")
        earnings_day_ret = market_anchors.get("earnings_day_return")
        pre_earnings_5d = market_anchors.get("pre_earnings_5d_return")

        # Risk indicators (normalized to 0-1)
        if eps_surprise is not None and eps_surprise < 0:
            risk_flag += 0.3
        if earnings_day_ret is not None and earnings_day_ret < -3:
            risk_flag += 0.4
        if pre_earnings_5d is not None and pre_earnings_5d > 15:
            risk_flag += 0.3

        risk_flag = min(1.0, risk_flag)

    result["risk_flag"] = risk_flag

    # Check for vetoes (ChatGPT Pro Round 2: CashBurn moved to soft)
    # Hard vetoes (always block): only GuidanceCut
    hard_veto_fields = ["GuidanceCut"]
    hard_veto_count = sum(1 for f in hard_veto_fields
                          if str(long_json.get(f, "")).upper() == "YES")

    # Soft vetoes (reduce size but don't block): includes CashBurn now
    soft_veto_fields = ["DemandSoftness", "MarginWeakness", "VisibilityWorsening", "CashBurn"]
    soft_veto_count = sum(1 for f in soft_veto_fields
                          if str(long_json.get(f, "")).upper() == "YES")

    result["hard_veto_count"] = hard_veto_count
    result["soft_veto_count"] = soft_veto_count

    if hard_veto_count > 0:
        result["block_reason"] = "HARD_VETOES"
        return result

    # High risk = block
    if risk_flag >= 0.7:
        result["block_reason"] = "HIGH_RISK"
        return result

    # Compute expected return (mu_raw) from direction score
    # ChatGPT Pro Round 6: Lower floor to DIR >= 3 to allow D3_WIDE and D4_OPP
    if direction_score >= 3:
        # DIR=3->0.75%, 4->1.5%, 5->2.5%, 6->5%, 7->7.5%, 8->10%, 9->12.5%, 10->15%
        if direction_score >= 5:
            mu_raw = (direction_score - 4) * 0.025
        else:
            mu_raw = (direction_score - 2) * 0.0075  # Lower expected return for D3/D4
    else:
        result["block_reason"] = "DIR_TOO_LOW"
        return result

    result["mu_raw"] = mu_raw

    # ChatGPT Pro Round 11: Use new minimum direction (5 for D5_GATED, was 6 in R10)
    effective_min_dir = MIN_DIRECTION_TO_TRADE_R11 if ENABLE_D5_GATED else MIN_DIRECTION_TO_TRADE
    if direction_score < effective_min_dir:
        result["block_reason"] = f"DIR_BELOW_MIN_{effective_min_dir}"
        return result

    # ChatGPT Pro Round 10: Reaction alignment gate
    # Block if earnings move is strongly opposite to trade direction
    passes_alignment, align_reason = passes_reaction_alignment_gate(
        pre_entry_return,
        direction="LONG",  # All trades are LONG in this system
        mismatch_threshold=REACTION_MISMATCH_BLOCK
    )
    if not passes_alignment:
        result["block_reason"] = align_reason
        return result

    # ChatGPT Pro Round 10: Use momentum-aligned reaction term instead of penalty
    reaction_term = compute_reaction_term(
        pre_entry_return,
        direction="LONG",
        clip=REACTION_CLIP,
        weight=REACTION_WEIGHT,
        mode=REACTION_MODE
    )
    result["reaction_penalty"] = reaction_term  # Keep same key for compatibility
    result["reaction_mode"] = REACTION_MODE

    # Legacy: compute old-style reaction penalty for comparison (not used)
    reaction_penalty = reaction_term  # Use the new term

    # Compute cost
    cost_bps = estimate_cost_bps(adv_usd=adv_usd)
    result["cost_bps"] = cost_bps

    # Compute uncertainty
    uncertainty = 1.0 - reliability_score
    result["uncertainty"] = uncertainty

    # Compute utility
    # ChatGPT Pro Round 10: For momentum-aligned mode, reaction_term is already signed correctly
    # (positive for aligned moves, negative for misaligned)
    # The utility formula is: mu_net = mu_raw - reaction_penalty
    # So we pass -reaction_term to get: mu_net = mu_raw - (-reaction_term) = mu_raw + reaction_term
    if REACTION_MODE == "MOMENTUM_ALIGNED":
        # Pass negative so the subtraction becomes addition
        effective_reaction = -reaction_term
    else:
        # Legacy mode: reaction_term is already a penalty to subtract
        effective_reaction = reaction_term

    utility = compute_v10_utility(
        mu_raw=mu_raw,
        sigma=sigma_20d,
        uncertainty=uncertainty,
        risk_flag=risk_flag,
        contradiction=contradiction_score,
        reliability=reliability_score,
        reaction_penalty=effective_reaction,
        cost_bps=cost_bps
    )
    result["utility"] = utility

    # Determine tier based on direction score, quality gates, and soft veto budget
    # ChatGPT Pro Round 1: D7 (soft<=1), D6 (soft<=2), D5 (soft<=1)
    tier = ""
    if direction_score >= 7:
        # ChatGPT Pro Round 12 (R2): Block D7 for certain sectors (e.g., Real Estate - BXP -21.49%)
        if sector and sector in D7_BLOCKED_SECTORS:
            result["block_reason"] = f"D7_SECTOR_BLOCKED_{sector.upper()[:4]}"
            return result

        # D7 CORE tier: allow at most 1 soft veto
        if soft_veto_count > 1:
            result["block_reason"] = "D7_TOO_MANY_SOFT_VETOES"
            return result
        if evidence_score >= MIN_EVIDENCE_D7 and contradiction_score <= MAX_CONTRADICTION_D7:
            tier = "D7_CORE"
        else:
            result["block_reason"] = "D7_QUALITY_GATE"
            return result
    elif direction_score == 6:
        # ChatGPT Pro Round 9: D6 re-enabled with tighter constraints
        if not D6_ENABLED:
            result["block_reason"] = "D6_DISABLED"
            return result

        # ChatGPT Pro Round 11: Block D6 for certain sectors
        # Tech (WDAY -9.33%) and Healthcare (0% WR) underperform at D6
        if sector and sector in D6_BLOCKED_SECTORS:
            result["block_reason"] = f"D6_SECTOR_BLOCKED_{sector.upper()[:4]}"
            return result

        # ChatGPT Pro Round 9: D6→D7 PROMOTION RULE
        # If DIR==6 AND soft_veto==0 AND confirmation>=2 → treat as D7 for sizing
        positives = sum(1 for f in ["GuidanceRaised", "DemandAcceleration", "MarginExpansion",
                                     "FCFImprovement", "VisibilityImproving"]
                        if str(long_json.get(f, "")).upper() == "YES")
        if soft_veto_count == 0 and positives >= 2:
            if evidence_score >= MIN_EVIDENCE_D7 and contradiction_score <= MAX_CONTRADICTION_D7:
                # Promoted to D7 sizing
                tier = "D7_CORE"
                result["promoted_from_d6"] = True
            else:
                # Stay at D6
                pass

        # Regular D6 path if not promoted
        if not tier:
            # Round 9: tighter soft_veto limit (was <= 2, now <= 1)
            if soft_veto_count > 1:
                result["block_reason"] = "D6_TOO_MANY_SOFT_VETOES"
                return result
            if (evidence_score >= MIN_EVIDENCE_D6 and
                contradiction_score <= MAX_CONTRADICTION_D6 and
                numeric_coverage >= MIN_NUMERIC_D6):
                # Additional check: eps surprise should be positive for D6
                if market_anchors:
                    eps = market_anchors.get("eps_surprise", 0)
                    if eps is not None and eps < 0.02:  # Need at least 2% EPS surprise
                        result["block_reason"] = "D6_EPS_LOW"
                        return result
                tier = "D6_STRICT"
            else:
                result["block_reason"] = "D6_QUALITY_GATE"
                return result
    elif direction_score >= 5:
        # D5 GATED tier (ChatGPT Pro Round 11: enabled with momentum alignment)
        if not ENABLE_D5_GATED:
            result["block_reason"] = "D5_DISABLED"
            return result

        if soft_veto_count > 2:
            result["block_reason"] = "D5_TOO_MANY_SOFT_VETOES"
            return result

        # ChatGPT Pro Round 11: D5 requires MOMENTUM ALIGNMENT
        # Only take D5 if earnings day move is >= 3% aligned with direction
        # PAYC example: +21.35% earnings day → momentum aligned → +36.14% return
        if market_anchors:
            earnings_day_ret = market_anchors.get("earnings_day_return", 0) or 0
            # For LONG trades, need positive earnings day return
            aligned_move = earnings_day_ret / 100  # Convert to decimal
            if aligned_move < D5_MIN_ALIGNED_MOVE:
                result["block_reason"] = f"D5_NO_MOMENTUM_{int(aligned_move*100)}PCT"
                return result

        # D5 has lower quality gate requirements
        if evidence_score >= 0.5 and contradiction_score <= 0.5:
            # D5 requires positive EPS
            if market_anchors:
                eps = market_anchors.get("eps_surprise", 0)
                if eps is None or eps <= 0:
                    result["block_reason"] = "D5_EPS_NOT_POSITIVE"
                    return result
            tier = "D5_GATED"
        else:
            result["block_reason"] = "D5_QUALITY_GATE"
            return result
    elif direction_score >= 4:
        # ChatGPT Pro Round 10: D4 tiers DISABLED by default (negative expectancy)
        if not ENABLE_D4_OPP:
            result["block_reason"] = "D4_DISABLED_R10"
            return result

        # ChatGPT Pro Round 6: D4_OPP (more permissive) - captures PAYC-type winners
        # soft_veto <= 2, positives >= 1 OR eps >= 1%
        eps = market_anchors.get("eps_surprise", 0) if market_anchors else 0
        positives = sum(1 for f in ["GuidanceRaised", "DemandAcceleration", "MarginExpansion",
                                     "FCFImprovement", "VisibilityImproving"]
                        if str(long_json.get(f, "")).upper() == "YES")

        # Try D4_ENTRY first (stricter)
        if soft_veto_count <= 1 and evidence_score >= 0.6 and contradiction_score <= 0.3:
            if market_anchors:
                day_ret = market_anchors.get("earnings_day_return", 0)
                if eps is not None and eps >= 0.02 and day_ret is not None and day_ret > 0:
                    tier = "D4_ENTRY"

        # Fall back to D4_OPP (ChatGPT Pro Round 9: now requires confirmation)
        if not tier:
            # Round 9: D4_OPP now requires confirmation (positives >= 1 OR eps >= 1%)
            has_opp_confirmation = positives >= 1 or (eps is not None and eps >= 0.01)
            if D4_OPP_REQUIRE_CONFIRMATION and not has_opp_confirmation:
                result["block_reason"] = "D4_OPP_NO_CONFIRMATION"
                return result
            if soft_veto_count <= 2 and has_opp_confirmation:
                tier = "D4_OPP"
            else:
                result["block_reason"] = "D4_NO_CONFIRMATION"
                return result
    elif direction_score >= 3:
        # ChatGPT Pro Round 10: D3 tier DISABLED by default (focus on D6/D7 only)
        if not ENABLE_D3_WIDE:
            result["block_reason"] = "D3_DISABLED_R10"
            return result

        # ChatGPT Pro Round 8: D3_WIDE - reverted to soft_veto==0 (relaxation didn't help)
        # positives >= 2 OR eps >= 2%
        eps = market_anchors.get("eps_surprise", 0) if market_anchors else 0
        positives = sum(1 for f in ["GuidanceRaised", "DemandAcceleration", "MarginExpansion",
                                     "FCFImprovement", "VisibilityImproving"]
                        if str(long_json.get(f, "")).upper() == "YES")

        # Round 8: Revert to soft_veto == 0 (Round 7's relaxation to <=1 didn't help)
        if soft_veto_count > 0:
            # ChatGPT Pro Round 9: D3_PROBE for high DIR blocked by soft vetoes
            # If DIR >= 6 AND soft_veto <= 3 AND confirmation >= 2 → allow as tiny probe
            if direction_score >= 6 and soft_veto_count <= 3 and positives >= 2:
                tier = "D3_PROBE"
            else:
                result["block_reason"] = "D3_TOO_MANY_SOFT_VETOES"
                return result
        else:
            # Normal D3_WIDE path
            if positives >= 2 or (eps is not None and eps >= 0.02):
                tier = "D3_WIDE"
            else:
                result["block_reason"] = "D3_NO_CONFIRMATION"
                return result

    if not tier:
        result["block_reason"] = "NO_TIER_MATCHED"
        return result

    # Determine if confirmation was present (for D4_ENTRY, D5_GATED tiers)
    has_confirmation = tier in ["D4_ENTRY", "D5_GATED"]

    # Compute position size (ChatGPT Pro Round 7: includes dynamic sizing)
    position_size = compute_v10_position_size(
        utility=utility,
        tier=tier,
        mu_hat=mu_raw - reaction_penalty - cost_bps/10000,
        sigma_hat=sigma_20d,
        uncertainty_hat=uncertainty,
        soft_veto_count=soft_veto_count,
        direction_score=direction_score,
        has_confirmation=has_confirmation,
        high_risk=(risk_flag >= 0.4)  # Round 7: use high_risk multiplier instead of blocking
    )

    result["trade_long"] = True
    result["tier"] = tier
    result["position_size"] = position_size

    return result


# =============================================================================
# Export functions for use in agentic_rag_bridge
# =============================================================================

__all__ = [
    "compute_v10_trade_signal",
    "compute_evidence_score",
    "compute_contradiction_score",
    "compute_numeric_coverage",
    "compute_reliability_score",
    "compute_v10_utility",
    "compute_v10_position_size",
]
