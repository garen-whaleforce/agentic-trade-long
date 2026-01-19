# Round 8 Input - Tier Gate Optimization & Market Anchor Integration

**Date**: 2026-01-19
**Round**: 8 of 10 (Fast Iteration Mode)
**Accumulated Changes**: Rounds 6-7 (prompts + veto logic)

---

## Context

After Rounds 6-7 prompt and veto optimizations, we're now targeting tier gates and market anchor integration to further improve signal quality and position sizing.

**Current Performance (Iteration 1)**:
- CAGR: 20.05%
- Sharpe: 1.53
- Win Rate: 72.26%
- D7/D6 Ratio: 45.8%
- D4 Ratio: 47.7% (too high)

**Rounds 6-7 Expected Impact**:
- CAGR: 28-32% (projected)
- Sharpe: 1.7-1.9 (projected)
- D7/D6 Ratio: >55%
- D4 Ratio: <35%

**Ultimate Target**:
- CAGR: >35%
- Sharpe: >2.0

---

## Current 7-TIER Architecture

```python
# agentic_rag_bridge.py

# TIER 1: D7_CORE (Highest conviction)
if direction >= 7 and len(soft_vetoes) <= 1:
    return True, "D7_CORE", 1.0

# TIER 2: D6_STRICT
if direction == 6 and len(soft_vetoes) <= 1:
    return True, "D6_STRICT", 0.75

# TIER 3: D5_GATED (Momentum required)
if direction >= 5:
    if earnings_day_return >= 0.02 or pre_earnings_5d_return >= 0.03:
        return True, "D5_GATED", 0.50

# TIER 4: D4_ENTRY (Confirmation required)
if direction >= 4:
    if earnings_day_return >= 0.03 and pre_earnings_5d_return >= 0.05:
        return True, "D4_ENTRY", 0.30

# TIER 5-7: DISABLED (D4_OPP, D3_WIDE, D3_PROBE)
```

### Industry Blocks
```python
D6_BLOCKED_SECTORS = ["Technology", "Healthcare"]
D7_BLOCKED_SECTORS = ["Real Estate"]
```

---

## Market Anchors Available

```python
market_anchors = {
    "eps_surprise": 0.15,           # 15% earnings surprise
    "earnings_day_return": 0.08,     # +8% on earnings day
    "pre_earnings_5d_return": 0.12   # +12% in 5 days before
}
```

**Current Usage**: Only used for D5_GATED and D4_ENTRY gates (momentum filtering)

**Underutilized Potential**: `eps_surprise` not used in any tier gate logic

---

## Current V10 Position Sizing

```python
# v10_scoring.py

def compute_v10_position_size(
    tier: str,
    direction_score: int,
    confidence: int,
    reliability_score: float,
    evidence_score: float,
    contradiction_score: float,
    n_soft_vetoes: int,
    reaction_term: float = 0.0,
) -> float:

    # Tier-specific base sizes
    if tier == "D7_CORE":
        kelly_multiplier = 1.0
    elif tier == "D6_STRICT":
        kelly_multiplier = 0.75
    elif tier == "D5_GATED":
        kelly_multiplier = 0.50
    elif tier == "D4_ENTRY":
        kelly_multiplier = 0.30

    # Utility score
    utility = (
        0.3 * reliability_score +
        0.2 * evidence_score +
        0.1 * (10 - contradiction_score) / 10 +
        0.1 * reaction_term
    )

    # Soft veto penalty
    soft_veto_penalty = 0.90 ** n_soft_vetoes

    # Final size
    position_size = utility * kelly_multiplier * soft_veto_penalty * POSITION_SCALE
    return position_size

POSITION_SCALE = 5.5
```

**Observation**: Market anchors (eps_surprise, earnings_day_return) not used in position sizing

---

## Problems to Address

### Problem 1: D4 Over-Representation
**Current**: 47.7% of trades are D4 tier
**Issue**: D4 trades have lower win rate and lower returns
**Question**: Should we:
- Make D4 gates stricter?
- Disable D4 tier entirely?
- Add eps_surprise requirement to D4?

### Problem 2: Market Anchor Under-Utilization
**Current**: eps_surprise only available, not used in decision logic
**Issue**: Missing strong signal that correlates with future returns
**Question**: Should we:
- Add eps_surprise to tier gates (e.g., D7 requires eps_surprise > 0.10)?
- Use eps_surprise in position sizing?
- Use eps_surprise to override hard vetoes?

### Problem 3: Industry Block Logic
**Current**: D6/D7 have sector blocks
**Issue**: May be filtering out good trades in Tech/Healthcare
**Question**: Should we:
- Remove industry blocks?
- Make blocks conditional on other factors?
- Add eps_surprise exception (strong surprise overrides block)?

### Problem 4: Position Sizing Doesn't Use Market Reaction
**Current**: V10 scoring uses reaction_term but it's often 0.0
**Issue**: Not incorporating actual market reaction (earnings_day_return, eps_surprise)
**Question**: Should we:
- Pass earnings_day_return as reaction_term?
- Add eps_surprise boost to position size?
- Scale position size with abs(eps_surprise)?

### Problem 5: D7/D6 Gates Too Conservative
**Current**: D7 requires direction ≥ 7 + soft_vetoes ≤ 1
**Issue**: May be missing strong trades due to minor soft vetoes
**Question**: Should we:
- Relax soft veto limit for D7 if eps_surprise > 0.15?
- Allow D7 with 2 soft vetoes if strong market reaction?
- Add "D7_SURPRISE" tier for exceptional eps_surprise?

---

## Round 8 Optimization Request

**Focus Areas**:
1. **Tier Gate Calibration**: Should D4 be stricter, disabled, or require eps_surprise?
2. **EPS Surprise Integration**: How to incorporate eps_surprise into tier gates and position sizing?
3. **Industry Block Refinement**: Keep, remove, or make conditional?
4. **Market Anchor Position Sizing**: Should position size scale with eps_surprise or earnings_day_return?
5. **D7/D6 Relaxation**: Should we allow more D7/D6 trades with strong market anchors?

**Specific Questions**:

1. **D4 Tier Optimization**:
   - Option A: Disable D4 entirely (focus on D5+)
   - Option B: Add eps_surprise >= 0.08 requirement to D4_ENTRY
   - Option C: Make D4 require earnings_day_return >= 0.05 (stricter)
   - Which is best?

2. **EPS Surprise Integration**:
   - Should D7 require eps_surprise > 0.10 (10% beat)?
   - Should D6 require eps_surprise > 0.05 (5% beat)?
   - Should we add "D8_MEGA" tier for eps_surprise > 0.20?

3. **Industry Block Strategy**:
   - Keep as is?
   - Remove blocks if eps_surprise > 0.15 (strong surprise overrides)?
   - Remove blocks entirely and rely on prompts?

4. **Position Sizing Enhancement**:
   ```python
   # Option A: Add eps_surprise boost
   eps_boost = 1.0 + max(0, eps_surprise * 2)  # 10% surprise = 1.2x size
   position_size *= eps_boost

   # Option B: Use earnings_day_return as reaction_term
   reaction_term = earnings_day_return / 0.10  # Normalize to 0-1 scale

   # Option C: Both
   ```
   Which approach is best?

5. **Trade-off Analysis**:
   - If we make gates stricter → fewer trades but higher quality
   - If we integrate eps_surprise → more D7/D6, fewer D4
   - What's the optimal balance for CAGR >35%, Sharpe >2.0?

---

## Expected Outcomes

**Round 8 Target Contribution**:
- Reduce D4 ratio from 47.7% → <20%
- Increase D7/D6 ratio from 45.8% → >60%
- Better position sizing based on market reaction
- Fewer false positives from industry-specific quirks

**Cumulative Impact (Rounds 6-8)**:
- CAGR: 20.05% → **32-36%** (approaching target)
- Sharpe: 1.53 → **1.8-2.1** (approaching target)
- Total Trades: 328 → 200-250 (higher quality)
- Profit Factor: 2.57 → 3.5-4.0

---

## Implementation Constraints

**Must Not Break**:
- Lookahead protection (no future data)
- Veto system integrity
- V10 scoring framework

**Can Modify**:
- Tier gate thresholds
- Industry block logic
- Position sizing formulas
- Market anchor usage

---

## Data Context

**Available at Decision Time**:
- direction_score (from MainAgent)
- soft_vetoes, hard_vetoes (from veto detection)
- eps_surprise (from PostgreSQL)
- earnings_day_return (from PostgreSQL)
- pre_earnings_5d_return (from PostgreSQL)
- sector (from company metadata)

**NOT Available**:
- T+30 return (future data - forbidden)
- Post-earnings stock performance (lookahead)

---

## Request to ChatGPT Pro

Please analyze the current tier gate architecture and market anchor integration strategy, then provide:

1. **Specific tier gate modifications** (code-level recommendations)
2. **EPS surprise integration strategy** (where and how to use)
3. **Industry block refinement** (keep/modify/remove decision with rationale)
4. **Position sizing enhancement** (formula updates to incorporate market reaction)
5. **Expected performance impact** (quantified if possible)

Focus on **actionable changes** that can be directly implemented in `agentic_rag_bridge.py` and `v10_scoring.py`.

---

## Success Metrics

**This round successful if**:
- Clear tier gate optimization strategy provided
- EPS surprise integration method specified
- Position sizing enhancement formula given
- Expected to contribute +4-6% CAGR, +0.1-0.2 Sharpe

**Cumulative success if (Rounds 6-8)**:
- CAGR approaching 35%
- Sharpe approaching 2.0
- D7/D6 ratio >60%
