# Round 6 Implementation - Prompt Optimization

**Date**: 2026-01-19
**Objective**: Implement ChatGPT Pro Round 6 recommendations
**Expected Impact**: CAGR +10-15% (target 30-35%), Sharpe +0.2-0.4 (target 1.7-2.0)

---

## Changes Implemented

### 1. Main Agent System Message ✅
**File**: `EarningsCallAgenticRag/agents/prompts/prompts.py`
**Lines**: 33-56

#### Key Improvements:
- ✅ Added explicit focus on **"true surprises"** vs priced-in results
- ✅ Added **Direction Score calibration** with specific thresholds:
  - D9-10: >20% earnings surprise, 10-15% price movement
  - D7-8: 10-20% earnings surprise, 5-10% price movement
  - D<6: In-line results, <5% price movement (AVOID)
- ✅ Emphasized **surprise-based analysis** over generic forward guidance
- ✅ Clearer distinction between strong/medium/weak signals

#### Before vs After:

**Before**:
```
- Use the full Direction scale appropriately (avoid clustering around 5-6)
- Be conservative: strong quarters alone don't guarantee price appreciation
```

**After**:
```
- For a Direction Score of 9-10: Only consider the strongest signals—substantial earnings surprises (>20% vs consensus), highly optimistic or pessimistic forward guidance, and clear market reactions (10-15% price movement).
- For Direction Score of 7-8: Signals that are moderately strong... Earnings surprise of 10-20%, moderate market movement (5-10%).
- For Direction Scores below 6: Avoid signals that are unclear, marginal, or without sufficient conviction.
```

---

### 2. Extraction System Message ✅
**File**: `EarningsCallAgenticRag/agents/prompts/prompts.py`
**Lines**: 62-80

#### Key Improvements:
- ✅ Reorganized fact categories to emphasize **Surprise** and **Market Reaction**
- ✅ Added explicit **Surprise** category (>10% deviation from consensus)
- ✅ Added **Tone** and **Market Reaction** as first-class categories
- ✅ Instructions to assess conviction level (Direction Score) for each fact
- ✅ Clearer guidance on what constitutes a "surprise"

#### New Fact Categories:
1. **Surprise** (NEW) - Results significantly beating/missing consensus
2. **Guidance** - Forward-looking statements
3. **Tone** (NEW) - Management sentiment, confidence level
4. **Market Reaction** (NEW) - Stock price movement, analyst reactions
5. **Warning Sign** - Operational red flags
6. **Risk Disclosure** - New risks, competitive threats

---

### 3. Model Configuration ✅
**File**: `EarningsCallAgenticRag/utils/config.py`
**Current**: Already using `cli-gpt-5.2-high` for MAIN_MODEL

No changes needed - configuration already optimal per ChatGPT Pro recommendation.

---

## Expected Behavioral Changes

### Signal Distribution Shift (Projected)

| Tier | Current (Iter 1) | Target (Round 6) | Change |
|------|------------------|------------------|--------|
| D7 CORE | 226 (25.6%) | 280-320 (35-40%) | +54-94 trades |
| D6 STRICT | 178 (20.2%) | 150-180 (19-22%) | -28 to +2 trades |
| D5 GATED | 58 (6.6%) | 40-60 (5-7%) | -18 to +2 trades |
| D4 ENTRY | 421 (47.7%) | 250-300 (31-37%) | -121 to -171 trades |

**Key Change**: Shift from D4-dominated to D7-dominated signal distribution.

### Trade Quality Improvement

| Metric | Current | Target | Mechanism |
|--------|---------|--------|-----------|
| Avg Return/Trade | ~20% | ~25-28% | Focus on high-conviction signals |
| Profit Factor | 2.57 | 3.0-3.5 | Filter out marginal trades |
| Win Rate | 72.26% | 70-75% | Maintain acceptable range |

---

## Risk Assessment

### Potential Downside Risks

1. **Fewer Total Trades**
   - Risk: May drop from 328 to 250-280 trades
   - Mitigation: Higher quality should compensate with better returns per trade

2. **Calibration Adjustment Period**
   - Risk: LLM may need time to adapt to new scoring guidelines
   - Mitigation: Monitor first 50-100 signals for calibration drift

3. **Win Rate Volatility**
   - Risk: More aggressive D7/D8 assignments may increase variance
   - Mitigation: Veto system still provides safety net

### Upside Opportunities

1. **D7 Tier Expansion**
   - Opportunity: 30-40% more D7 signals = 50-90 high-quality trades
   - Impact: Could add 5-10% CAGR alone

2. **D4 Noise Reduction**
   - Opportunity: Filtering 120-170 marginal D4 trades
   - Impact: Reduce volatility, improve Sharpe by 0.1-0.2

3. **Better Surprise Detection**
   - Opportunity: New "Surprise" fact category catches market-moving events
   - Impact: Improved direction accuracy by 5-10%

---

## Next Steps

### Immediate (This Session)
- [x] Update Main Agent System Message
- [x] Update Extraction System Message
- [x] Verify model configuration
- [ ] Execute full backtest (2017-2024)
- [ ] Compare results vs Iteration 1
- [ ] Document findings

### Round 7 Preparation
- [ ] Analyze Round 6 results
- [ ] Identify remaining gaps
- [ ] Prepare prompt for ChatGPT Pro Round 7
- [ ] Focus on remaining issues (likely veto logic or tier gates)

---

## Success Metrics

### Primary Targets
- CAGR: **25-30%** (current: 20.05%, ultimate: 35%)
- Sharpe: **1.6-1.8** (current: 1.53, ultimate: 2.0)
- Win Rate: **70-75%** (current: 72.26%)

### Secondary Metrics
- Total Trades: 250-300 (current: 328)
- Max Drawdown: <-22% (current: -17.87%)
- Profit Factor: >3.0 (current: 2.57)
- D7 Ratio: >35% (current: 25.6%)

---

## Backtest Command

```bash
cd /Users/garen.lee/Coding/agentic-trade-long/backtest_tools

# Prepare signals with updated prompts
python prepare_signals.py \
  --start_year 2017 \
  --end_year 2024 \
  --output_dir ../tuning_results \
  --output_file signals_round6.csv

# Execute backtest
python parameter_tuning.py \
  --signals_file ../tuning_results/signals_round6.csv \
  --config_name round6 \
  --output_dir ../tuning_results/backtest_round6
```

---

## Implementation Log

| Timestamp | Action | Status |
|-----------|--------|--------|
| 2026-01-19 11:58 | ChatGPT Pro Round 6 submitted | ✅ Complete |
| 2026-01-19 11:59 | ChatGPT Pro analysis received | ✅ Complete |
| 2026-01-19 12:00 | Main Agent System Message updated | ✅ Complete |
| 2026-01-19 12:00 | Extraction System Message updated | ✅ Complete |
| 2026-01-19 12:00 | Model configuration verified | ✅ Complete |
| 2026-01-19 12:01 | Backtest execution | ⏳ Pending |

---

## References

- Input: [round6_input.md](round6_input.md)
- Output: [round6_output.md](round6_output.md)
- ChatGPT Pro Chat: https://chatgpt.com/g/g-p-696dabef404481919b8b7897c7099e2a-agentic-trade-optimization/c/696dabfa-32e8-8321-a648-5cb38d1a9a50
