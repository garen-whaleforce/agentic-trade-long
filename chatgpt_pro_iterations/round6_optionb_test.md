# Round 6 Option B - Quick Validation Test

**Date**: 2026-01-19
**Type**: Quick validation test (不是完整回測)
**Purpose**: 評估 Round 6 prompt 更新的效果、時間成本

---

## Test Scope

### Samples
- **Time Period**: 2024 Q1
- **Companies**: 10 major companies (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, JPM, V, WMT)
- **Total Calls**: 10 earnings calls

### Why These Companies?
- Large cap, high-quality transcripts
- Diverse sectors (Tech, Finance, Retail)
- Well-known earnings patterns
- Good benchmark for prompt effectiveness

---

## Test Objectives

### 1. Validate Prompt Changes ✅
**Check if new prompts are working correctly**:
- Are facts being categorized with new categories (Surprise, Tone, Market Reaction)?
- Is Direction Score calibration clearer?
- Are surprise elements being weighted properly?

### 2. Direction Score Distribution 📊
**Target**: Shift from D4-dominated to D7/D6-dominated

| Metric | Iteration 1 | Target (Round 6) | Validation |
|--------|-------------|------------------|------------|
| D7/D6 Ratio | 45.8% | **>45%** | TBD |
| D4 Ratio | 47.7% | **<35%** | TBD |
| D5 Ratio | 6.6% | 5-7% | TBD |

### 3. Time & Cost Estimation ⏱️💰
**Extrapolate to full backtest** (2017-2024, ~16,000 calls):

| Metric | Per Call | Full Backtest |
|--------|----------|---------------|
| Time | TBD | TBD hours |
| API Cost | ~$0.05 | ~$800 |

### 4. Signal Quality Indicators 🎯
- Trade Long signals count
- Tier distribution (D7 vs D6 vs D5 vs D4)
- Veto distribution (hard vs soft)

---

## Success Criteria

### Minimum Requirements (to proceed with Option A)
- ✅ Test completes without errors
- ✅ D7/D6 ratio >= 45%
- ✅ D4 ratio <= 40%
- ✅ Average time per call < 60 seconds
- ✅ No prompt parsing errors

### Ideal Outcomes
- 🎯 D7/D6 ratio >= 50%
- 🎯 D4 ratio <= 30%
- 🎯 More Trade Long signals from D7 tier
- 🎯 Clear separation between strong/weak signals

---

## Test Script

**File**: `test_round6_prompts.py`

**Features**:
- Analyzes 10 2024 Q1 earnings calls
- Tracks Direction Score distribution
- Measures time per call
- Saves results to JSON
- Provides full backtest estimation

**Output**:
- Console summary with visualizations
- `test_results_round6.json` - Detailed results
- `test_round6_output.log` - Full log

---

## Decision Matrix

Based on test results, decide next action:

### Scenario A: Success ✅
**Criteria**: D7/D6 >45%, D4 <40%, no errors
**Action**: Proceed with Option A (full backtest)
**Timeline**: 3-6 hours
**Investment**: ~$800 API cost

### Scenario B: Partial Success 🟡
**Criteria**: D7/D6 40-45%, D4 40-45%
**Action**:
1. Analyze which prompts need tweaking
2. Make minor adjustments
3. Re-run Option B test
4. If improved, proceed with Option A

### Scenario C: Failure ❌
**Criteria**: D7/D6 <40%, D4 >50%, or major errors
**Action**:
1. Review prompt changes carefully
2. Consult ChatGPT Pro for Round 7 without backtest
3. Fix fundamental issues before full backtest

---

## Risk Assessment

### Low Risk ✅
- Only testing 10 calls (~5-10 minutes)
- Minimal API cost (~$0.50)
- Can quickly identify issues
- No impact on production

### High Value 💎
- Validates prompt changes before expensive full backtest
- Provides cost/time estimates for planning
- Early feedback for Round 7 optimization
- Reduces risk of wasted effort

---

## Timeline

| Step | Duration | Status |
|------|----------|--------|
| Test script creation | 5 min | ✅ Complete |
| Test execution | 5-10 min | ⏳ Running |
| Results analysis | 5 min | ⏳ Pending |
| Decision making | 2 min | ⏳ Pending |
| **Total** | **~20 min** | |

---

## Expected Output Format

```
================================================================================
Round 6 Prompt Validation Test
================================================================================
Testing 10 2024 Q1 earnings calls
Purpose: Validate new prompts, estimate time/cost for full backtest
================================================================================

[1/10] Analyzing AAPL 2024Q1... ✓ D8 D7_CORE (45.2s)
[2/10] Analyzing MSFT 2024Q1... ✓ D7 D7_CORE (38.1s)
...

================================================================================
Test Results Summary
================================================================================

📊 Direction Score Distribution:
  D9: 1 (10.0%) ████
  D8: 2 (20.0%) ████████
  D7: 3 (30.0%) ████████████
  D6: 2 (20.0%) ████████
  D5: 1 (10.0%) ████
  D4: 1 (10.0%) ████

📈 Tier Distribution:
  D7_CORE: 6 (60.0%)
  D6_STRICT: 3 (30.0%)
  D5_GATED: 1 (10.0%)

✅ Trade Long Signals: 10/10 (100.0%)

⏱️  Average Time per Call: 42.3s
   Total Test Time: 423.0s

================================================================================
Full Backtest Estimation (2017-2024)
================================================================================
Estimated Total Calls: ~16,000
Estimated Time: ~188 hours
Estimated Cost (LLM API): ~$800.00

================================================================================
Comparison with Iteration 1 (Parameter Tuning)
================================================================================
Current Test:
  D7/D6 Ratio: 50.0% (Target: >45%, Iter1: 45.8%)
  D4 Ratio: 10.0% (Target: <35%, Iter1: 47.7%)
  ✅ D7/D6 ratio IMPROVED
  ✅ D4 ratio REDUCED

💾 Detailed results saved to: test_results_round6.json
```

---

## Next Actions

After test completion:

1. **Review Results** - Analyze Direction Score distribution
2. **Compare with Targets** - Check if improvements achieved
3. **Estimate Resources** - Confirm time/cost for Option A
4. **Make Decision** - Proceed with Option A or adjust approach
5. **Document Findings** - Update iteration tracker

---

## References

- Prompt Changes: [round6_implementation.md](round6_implementation.md)
- ChatGPT Pro Analysis: [round6_output.md](round6_output.md)
- Test Script: `test_round6_prompts.py`
- Results: `test_results_round6.json` (generated after test)
