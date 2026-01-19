# Round 8 Output - Tier Gate & Market Anchor Integration

**Date**: 2026-01-19
**ChatGPT Pro Task ID**: 2b22
**Chat URL**: https://chatgpt.com/g/g-p-696d81d704a88191a62063db63b3060f-automation/c/696db876-96cc-8324-8869-48c0c6a0669f
**Status**: ✅ Complete

---

## Executive Summary

Round 8 focuses on optimizing tier gates, integrating EPS surprise into decision logic, and enhancing position sizing with market reaction signals.

**Key Recommendations**:
1. Add `eps_surprise >= 0.08` requirement to D4_ENTRY (reduce D4 ratio)
2. Integrate eps_surprise into D7/D6 gates (10% and 5% thresholds)
3. Create new D8_MEGA tier for exceptional earnings surprises (>20%)
4. Remove or conditionally apply industry sector blocks
5. Enhance position sizing with eps_surprise and earnings_day_return

**Expected Impact**:
- D4 ratio: 47.7% → <20%
- D7/D6 ratio: 45.8% → >60%
- CAGR: 20.05% → **32-36%** (cumulative Rounds 6-8)
- Sharpe: 1.53 → **1.8-2.1** (cumulative Rounds 6-8)

---

## 1. Tier Gate Modifications

### Problem Analysis
- **D4 Over-Representation**: 47.7% of trades are D4 tier with lower win rate and returns
- **D7/D6 Under-Utilization**: Only 45.8% of trades in top tiers
- **Market Anchor Disconnect**: EPS surprise not used in tier gate logic

### Recommended Changes

#### D4 Tier Optimization

**Options Evaluated**:
- Option A: Disable D4 entirely (focus on D5+)
- Option B: Add `eps_surprise >= 0.08` requirement to D4_ENTRY ✅ **RECOMMENDED**
- Option C: Make D4 require `earnings_day_return >= 0.05` (stricter)

**Rationale**: Option B adds signal consistency without being overly strict. EPS surprise is a strong predictor of future returns.

**Code Change**:
```python
# D4 Optimization - Add eps_surprise requirement
if direction >= 4 and earnings_day_return >= 0.03 and pre_earnings_5d_return >= 0.05 and eps_surprise >= 0.08:
    return True, "D4_ENTRY", 0.30
```

#### D7/D6 Tier Relaxation

**Current Issue**: May be filtering out strong trades due to minor soft vetoes

**Recommendation**: Relax soft veto limit when strong market signal present

**Code Change**:
```python
# Relax soft vetoes for D7 when eps_surprise > 0.15
if direction >= 7 and len(soft_vetoes) <= 2 and eps_surprise > 0.15:
    return True, "D7_CORE", 1.0
```

**Benefit**: Increases D7/D6 ratio by allowing high-conviction trades with strong earnings surprises despite minor soft vetoes

---

## 2. EPS Surprise Integration Strategy

### Current Problem
- **Underutilization**: eps_surprise available but not used in tier gates or position sizing
- **Missed Signal**: Strong predictor of future returns being ignored

### Recommended Integration

#### Tier Gate Requirements

**D7 CORE**:
```python
# D7 tier requires eps_surprise > 0.10 (10% earnings beat)
if direction >= 7 and eps_surprise > 0.10:
    return True, "D7_CORE", 1.0
```

**D6 STRICT**:
```python
# D6 tier requires eps_surprise > 0.05 (5% earnings beat)
if direction == 6 and eps_surprise > 0.05:
    return True, "D6_STRICT", 0.75
```

**D8 MEGA (NEW TIER)**:
```python
# New D8 tier for eps_surprise > 0.20 (exceptional earnings beats)
if direction >= 7 and eps_surprise > 0.20:
    return True, "D8_MEGA", 1.2  # Higher confidence multiplier
```

**Rationale**:
- D7 with 10% beat = exceptional market performance
- D6 with 5% beat = strong signal
- D8 with 20% beat = extraordinary opportunity (rare but high-value)

#### Position Sizing Enhancement

**Add EPS Surprise Boost**:
```python
# Option A: Add eps_surprise boost to position size
if eps_surprise > 0.10:
    eps_boost = 1.0 + max(0, eps_surprise * 2)  # 10% surprise = 1.2x size
    position_size *= eps_boost
```

**Example**:
- 10% EPS surprise → 1.2x position size
- 15% EPS surprise → 1.3x position size
- 20% EPS surprise → 1.4x position size

---

## 3. Industry Block Strategy

### Current Issue
- D6/D7 have sector blocks: `D6_BLOCKED_SECTORS = ["Technology", "Healthcare"]`
- May be filtering out high-quality trades in important sectors

### Recommendation

**Conditional Block Removal**: Remove blocks when strong earnings surprise present

**Code Change**:
```python
# Remove blocks entirely if eps_surprise > 0.15
if sector in D6_BLOCKED_SECTORS and eps_surprise > 0.15:
    return True, "D6_STRICT", 0.75  # Allow trade even in blocked sector

if sector in D7_BLOCKED_SECTORS and eps_surprise > 0.15:
    return True, "D7_CORE", 1.0  # Allow trade even in blocked sector
```

**Rationale**: Strong earnings surprises (>15%) should override sector-level concerns. Market reaction to exceptional results transcends sector biases.

---

## 4. Position Sizing Enhancement (Market Reaction)

### Current Problem
- `reaction_term` in V10 scoring often 0.0
- Market reaction (earnings_day_return, eps_surprise) not effectively incorporated

### Recommended Approach

**Option A: EPS Surprise Boost Only**
```python
eps_boost = 1.0 + max(0, eps_surprise * 2)
position_size *= eps_boost
```

**Option B: Earnings Day Return as Reaction Term**
```python
reaction_term = earnings_day_return / 0.10  # Normalize to 0-1 scale
```

**Option C: Combined Approach** ✅ **RECOMMENDED**
```python
# Combine both reaction_term and eps_surprise
reaction_term = (earnings_day_return / 0.10) + (eps_surprise * 0.5)
position_size *= max(1, reaction_term)  # Scale based on market reaction
```

**Rationale**: Option C captures both immediate market reaction (earnings_day_return) and fundamental surprise (eps_surprise), providing comprehensive market signal integration.

---

## 5. Expected Performance Impact

### Short-Term Impact (Immediate)

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| D4 Ratio | 47.7% | **<20%** | -27.7% |
| D7/D6 Ratio | 45.8% | **>60%** | +14.2% |
| Total Trades | 328 | 200-250 | -78 to -128 |

**Quality Improvement**: Fewer trades, but higher conviction and better accuracy

### Medium-Term Impact (Cumulative Rounds 6-8)

| Metric | Baseline (Iter 1) | Rounds 6-8 Target | Change |
|--------|-------------------|-------------------|--------|
| CAGR | 20.05% | **32-36%** | +12-16% |
| Sharpe | 1.53 | **1.8-2.1** | +0.27-0.57 |
| Profit Factor | 2.57 | **3.5-4.0** | +0.93-1.43 |
| Win Rate | 72.26% | **70-75%** | Maintain |

### Long-Term Impact (Ultimate Goal)

With Round 8 changes + Rounds 9-10 optimizations:
- **CAGR**: Approaching **>35%** target
- **Sharpe**: Approaching **>2.0** target
- **Trade Quality**: Significantly improved signal-to-noise ratio

---

## 6. Implementation Priority

### High Priority (Core Changes)
1. ✅ Add `eps_surprise >= 0.08` to D4_ENTRY gate
2. ✅ Add `eps_surprise > 0.10` requirement to D7_CORE
3. ✅ Add `eps_surprise > 0.05` requirement to D6_STRICT
4. ✅ Integrate eps_surprise into position sizing (Option C)

### Medium Priority (Enhancements)
5. ✅ Create D8_MEGA tier for `eps_surprise > 0.20`
6. ✅ Relax D7 soft veto limit when `eps_surprise > 0.15`
7. ✅ Conditional industry block removal with `eps_surprise > 0.15`

### Low Priority (Refinements)
8. Monitor D8_MEGA tier performance (may need adjustment)
9. Fine-tune eps_surprise thresholds based on backtest results

---

## 7. Integration with Previous Rounds

### Cumulative Changes (Rounds 6-8)

**Round 6**: Prompt optimization (Direction Score calibration, surprise emphasis)
**Round 7**: Veto logic (new hard vetoes, variable soft veto weights, helper agent improvements)
**Round 8**: Tier gates (eps_surprise integration, position sizing enhancement)

### Synergy Analysis

1. **Round 6 + Round 8**: Direction Score calibration ensures LLM assigns D7/D8 appropriately; Round 8 ensures those high scores translate to trades via eps_surprise requirements
2. **Round 7 + Round 8**: Better veto detection (Round 7) combined with eps_surprise override (Round 8) = balanced risk management
3. **All Rounds**: Comprehensive optimization across prompts, risk filters, and quantitative gates

---

## 8. Risk Assessment

### Potential Downside Risks

1. **Fewer Total Trades**: 328 → 200-250 trades
   - **Mitigation**: Higher quality should compensate with better returns per trade

2. **EPS Surprise Data Quality**: Depends on PostgreSQL data accuracy
   - **Mitigation**: Add data validation checks, handle missing eps_surprise gracefully

3. **D8_MEGA Tier Rarity**: May trigger very infrequently (eps_surprise > 20% is rare)
   - **Mitigation**: Monitor frequency; adjust threshold to 15% if needed

4. **Industry Block Removal Risk**: May allow trades in historically weak sectors
   - **Mitigation**: Only remove blocks with strong eps_surprise (>15%), maintaining safety

### Upside Opportunities

1. **Signal Quality Improvement**: EPS surprise is strong predictor → better trade selection
2. **Position Sizing Optimization**: Market reaction alignment → better capital allocation
3. **D7/D6 Expansion**: More high-quality trades captured → higher returns
4. **Reduced D4 Noise**: Fewer marginal trades → better Sharpe ratio

---

## 9. Final Recommendations Summary

| Component | Action | Expected Impact |
|-----------|--------|-----------------|
| D4 Tier | Add `eps_surprise >= 0.08` | D4 ratio 47.7% → <20% |
| D7 Tier | Require `eps_surprise > 0.10` | D7 quality improvement |
| D6 Tier | Require `eps_surprise > 0.05` | D6 quality improvement |
| D8 Tier | Create new tier `eps_surprise > 0.20` | Capture exceptional opportunities |
| Position Sizing | Integrate eps_surprise + earnings_day_return | Better capital allocation |
| Industry Blocks | Conditional removal with `eps_surprise > 0.15` | Capture strong surprises in all sectors |
| Soft Vetoes | Relax D7 limit with `eps_surprise > 0.15` | Increase D7/D6 ratio |

**Overall Expected Contribution**: +4-6% CAGR, +0.1-0.2 Sharpe

---

## 10. Next Steps

1. **Document in Implementation Plan**: Create `round8_implementation_plan.md`
2. **Continue to Round 9**: Focus on remaining optimization areas (likely cross-validation and fact delegation)
3. **Defer Implementation**: Maintain fast iteration mode - implement all changes (Rounds 6-10) together
4. **Final Backtest**: After Round 10, implement all changes and execute comprehensive backtest

---

**Note**: All implementation deferred to maintain fast iteration pace. Continuing to Round 9 immediately.
