# ChatGPT Pro Iterations Summary

**Project**: Agentic Trade Long Strategy Optimization
**Date Range**: 2026-01-19
**Goal**: Increase CAGR from 14.16% to 35%+ while maintaining Sharpe > 2.0
**Optimization Method**: ChatGPT Pro iterative deep research

---

## Executive Summary

After 4 iterations of systematic optimization:

| Metric | Baseline | Best (Iter 1) | Change | Target | Status |
|--------|----------|---------------|--------|--------|--------|
| **CAGR** | 14.16% | **20.05%** | +5.89% (+41.6%) | >35% | 🟡 Partial |
| **Sharpe Ratio** | 1.91 | 1.53 | -0.38 (-19.9%) | >2.0 | 🔴 Below |
| **Win Rate** | 86.11% | 72.26% | -13.85% | 70-75% | ✅ Achieved |
| **Total Trades** | 180 | 328 | +148 (+82.2%) | More | ✅ Achieved |
| **Max Drawdown** | -16.95% | -17.87% | -0.92% | Minimize | 🟡 Acceptable |
| **Annual Vol** | 7.06% | 12.41% | +5.35% (+75.8%) | - | ⚠️ Increased |
| **Avg Exposure** | 23.03% | 43.89% | +20.86% (+90.6%) | - | ✅ Improved |

**Key Finding**: Iteration 1 provides the best trade-off, achieving +41.6% CAGR improvement while keeping win rate in target range. However, Sharpe ratio declined due to increased volatility.

---

## Iteration Timeline

```
Baseline (v1.1-live-safe)
  ↓ Relax D7/D6 filters, Enable D4/D5
Iteration 1 ✅ BEST
  ↓ Tighten D4 filters, Add D6 risk requirement
Iteration 2 ❌ WORSE
  ↓ Relax HIGH_RISK, Enable D3
Iteration 3 ❌ WORSE
  ↓ Test position sizing (8 pos, 6 pos)
Iteration 4 ❌ WORSE
```

---

## Baseline Configuration (v1.1-live-safe)

### Performance Metrics
- **CAGR**: 14.16% (Target: >35%)
- **Sharpe Ratio**: 1.91 (Target: >2.0)
- **Win Rate**: 86.11% (Target: 70-75%)
- **Total Trades**: 180 (8 years) = 22.5 trades/year
- **Max Drawdown**: -16.95%
- **Annual Volatility**: 7.06%
- **Average Exposure**: 23.03%
- **Profit Factor**: 4.06

### Strategy Configuration
| Parameter | Value |
|-----------|-------|
| D7_MIN_DAY_RET | 1.5% |
| D6_MIN_EPS_SURPRISE | 0.0% |
| D6_REQUIRE_LOW_RISK | True |
| D6_EXCLUDE_SECTORS | Technology |
| D5_ENABLED | False |
| D4_ENABLED | False |
| RISK_DAY_LOW | -3% |
| MAX_POSITIONS | 12 |
| POSITION_SIZE | 8.33% (1/12) |

### Problem Analysis
1. **CAGR too low**: Only 22.5 trades/year, low capital utilization
2. **Win rate too high**: Filters too strict, missing opportunities
3. **Low exposure**: Only 23% average, underutilizing capital

---

## Iteration 1: Relax Filters & Enable D4/D5 ✅ BEST RESULT

### Parameter Changes
| Parameter | Baseline | Iteration 1 |
|-----------|----------|-------------|
| D7_MIN_DAY_RET | 1.5% | 1.0% ✓ |
| D6_MIN_EPS_SURPRISE | 0.0% | 0.5% ✗ |
| D6_REQUIRE_LOW_RISK | True | False ✓ |
| D6_EXCLUDE_SECTORS | Technology | None ✓ |
| D5_ENABLED | False | True ✓ |
| D4_ENABLED | False | True ✓ |
| RISK_DAY_LOW | -3% | -5% ✓ |
| MAX_POSITIONS | 12 | 10 ✓ |

### Performance Results
| Metric | Baseline | Iteration 1 | Change |
|--------|----------|-------------|--------|
| **CAGR** | 14.16% | **20.05%** | +5.89% (+41.6%) ✅ |
| **Sharpe** | 1.91 | 1.53 | -0.38 (-19.9%) ❌ |
| **Win Rate** | 86.11% | 72.26% | -13.85% ✅ (in range) |
| **Trades** | 180 | 328 | +148 (+82.2%) ✅ |
| **Max DD** | -16.95% | -17.87% | -0.92% 🟡 |
| **Annual Vol** | 7.06% | 12.41% | +5.35% ⚠️ |
| **Avg Exposure** | 23.03% | 43.89% | +20.86% ✅ |
| **Profit Factor** | 4.06 | 2.57 | -1.49 ⚠️ |

### Trade Distribution
| Tier | Count | % |
|------|-------|---|
| D4_ENTRY | 421 | 47.7% |
| D7_CORE | 226 | 25.6% |
| D6_STRICT | 178 | 20.2% |
| D5_GATED | 58 | 6.6% |

### Analysis
✅ **Successes**:
- CAGR increased by 41.6% (14.16% → 20.05%)
- Trade count nearly doubled (+82%)
- Win rate within target range (70-75%)
- Capital utilization improved (23% → 44%)

❌ **Trade-offs**:
- Sharpe ratio dropped below target (1.53 < 2.0)
- Volatility nearly doubled (7% → 12%)
- Profit factor declined (4.06 → 2.57)

### Root Cause
- D4_ENTRY tier (47.7% of trades) has lower quality but increases volume
- Relaxing risk requirements introduced more volatile positions
- Higher exposure = more market correlation

---

## Iteration 2: Tighten D4 Filters ❌ WORSE

### Parameter Changes
| Parameter | Iteration 1 | Iteration 2 |
|-----------|-------------|-------------|
| D4_MIN_EPS | 0.02 | 0.03 ✗ |
| D4_MIN_POSITIVES | 2 | 3 ✗ |
| D4_MAX_SOFT_VETOES | 1 | 0 ✗ |
| D6_REQUIRE_LOW_RISK | False | True ✗ |

### Performance Results
| Metric | Iter 1 | Iter 2 | Change |
|--------|--------|--------|--------|
| **CAGR** | 20.05% | 17.43% | -2.62% ❌ |
| **Sharpe** | 1.53 | 1.41 | -0.12 ❌ |
| **Win Rate** | 72.26% | 74.42% | +2.16% 🟡 |
| **Trades** | 328 | 301 | -27 ❌ |
| **Max DD** | -17.87% | -21.52% | -3.65% ❌ |

### Trade Distribution
| Tier | Iter 1 | Iter 2 | Change |
|------|--------|--------|--------|
| D7_CORE | 226 | 226 | 0 |
| D6_STRICT | 178 | 125 | -53 |
| D5_GATED | 58 | 58 | 0 |
| D4_ENTRY | 421 | 218 | -203 |

### Analysis
❌ **All metrics worsened**:
- CAGR dropped 13% (20.05% → 17.43%)
- Max drawdown increased (-17.87% → -21.52%)
- Trade count decreased (328 → 301)

### Key Learning
- Tightening D4 filters removed potentially profitable trades
- D6 low risk requirement too restrictive
- **Lesson**: More selective ≠ better performance

---

## Iteration 3: Relax HIGH_RISK Block ❌ WORSE

### Parameter Changes
| Parameter | Iteration 1 | Iteration 3 |
|-----------|-------------|-------------|
| RISK_EPS_MISS | 0.0 | -0.05 (allow 5% miss) |
| RISK_DAY_LOW | -5.0% | -7.0% |
| RISK_RUNUP_HIGH | 15% | 20% |
| D3_ENABLED | False | True |

### Performance Results
| Metric | Iter 1 | Iter 3 | Change |
|--------|--------|--------|--------|
| **CAGR** | 20.05% | 19.01% | -1.04% ❌ |
| **Sharpe** | 1.53 | 1.40 | -0.13 ❌ |
| **Win Rate** | 72.26% | 69.91% | -2.35% ⚠️ (below target) |
| **Trades** | 328 | 339 | +11 🟡 |
| **Max DD** | -17.87% | -18.40% | -0.53% 🟡 |

### Analysis
❌ **More trades, worse performance**:
- Trade count increased but CAGR dropped
- Win rate fell below target (69.91% < 70%)
- Relaxed HIGH_RISK allowed lower quality trades

### Key Learning
- **Lesson**: More trades ≠ better performance
- D3_WIDE tier (19 trades) has insufficient quality
- HIGH_RISK filter serves important purpose

---

## Iteration 4: Test Position Sizing ❌ WORSE

### Tests Performed
Using Iteration 1's signal filters with different position sizing:

| Test | Max Positions | Position Size | CAGR | Sharpe | Trades | Max DD |
|------|---------------|---------------|------|--------|--------|--------|
| **Iter 1** | 10 | 10% | **20.05%** | **1.53** | 328 | -17.87% |
| Iter 4a | 8 | 12.5% | 19.57% | 1.45 | 271 | -16.93% |
| Iter 4b | 6 | 16.7% | 19.35% | 1.38 | 213 | -17.40% |

### Analysis
❌ **Larger positions hurt performance**:
- CAGR dropped with larger position sizes
- Fewer concurrent positions = fewer total trades
- Trade count fell significantly (328 → 271 → 213)

### Key Learning
- **10 positions (10% each) is optimal**
- Diversification benefit > concentration benefit
- CAP per quarter (12) harder to fill with larger positions

---

## Key Insights

### What Worked ✅
1. **Enabling D4/D5 tiers** - Increased trade volume substantially
2. **Relaxing D7 day return threshold** (1.5% → 1.0%)
3. **Removing sector blocks** - Technology sector has good opportunities
4. **10 concurrent positions** - Optimal diversification
5. **Relaxing risk filters moderately** (day low: -3% → -5%)

### What Didn't Work ❌
1. **Tightening D4 filters** - Removed good trades
2. **Re-enabling D6 low risk requirement** - Too restrictive
3. **Relaxing HIGH_RISK too much** - Quality degradation
4. **Enabling D3 tier** - Low quality trades
5. **Larger position sizes** - Reduced trade count, worse returns

### The Trade-off Dilemma
```
High Selectivity              Low Selectivity
(Baseline)                    (Iteration 1)
    │                              │
    ├─ Win Rate: 86%               ├─ Win Rate: 72%
    ├─ CAGR: 14%                   ├─ CAGR: 20%
    ├─ Sharpe: 1.91                ├─ Sharpe: 1.53
    ├─ Trades: 180                 ├─ Trades: 328
    └─ Exposure: 23%               └─ Exposure: 44%

    Too Conservative               Better Balance
    Underutilizing Capital         Higher Returns
```

**Conclusion**: Cannot achieve both 35% CAGR AND 2.0 Sharpe simultaneously with current signal quality. Must choose priority.

---

## Recommended Next Steps

### Option A: Accept Iteration 1 (Balanced Approach)
**Configuration**: Iteration 1 parameters
**Expected**: CAGR 20%, Sharpe 1.5, Win Rate 72%
**Rationale**: Best trade-off between returns and risk

### Option B: Push for Higher CAGR (Aggressive)
**Potential Changes**:
1. Enable D3_WIDE tier with quality filters
2. Increase MAX_POSITIONS to 12
3. Relax D5 gates further
**Risk**: Sharpe may drop below 1.4

### Option C: Improve Signal Quality (Conservative)
**Potential Changes**:
1. Enhance LLM analysis prompts
2. Add more sophisticated veto logic
3. Improve historical agent context
**Timeline**: Requires significant R&D

### Option D: Dynamic Position Sizing (Advanced)
**Concept**: Variable position sizes based on confidence
- D7 trades: 12-15%
- D6 trades: 8-10%
- D5/D4 trades: 5-7%
**Risk**: Complex to implement and backtest

---

## Files Generated

### Iteration 1
- `tuning_results/signals_iteration1.csv` - 882 signals
- `tuning_results/backtest_iteration1/` - Full backtest results

### Iteration 2
- `tuning_results/signals_iteration2.csv` - 627 signals
- `tuning_results/backtest_iteration2/` - Full backtest results

### Iteration 3
- `tuning_results/signals_iteration3.csv` - 945 signals
- `tuning_results/backtest_iteration3/` - Full backtest results

### Iteration 4
- `tuning_results/signals_iteration4a.csv` - 882 signals (8 pos)
- `tuning_results/signals_iteration4b.csv` - 882 signals (6 pos)
- `tuning_results/backtest_iteration4a/` - Full backtest results
- `tuning_results/backtest_iteration4b/` - Full backtest results

---

## Conclusion

**Best Configuration**: Iteration 1
**Achievement**: +41.6% CAGR improvement (14.16% → 20.05%)
**Remaining Gap**: Still 15% below 35% target
**Trade-off**: Sharpe ratio declined from 1.91 to 1.53

**Critical Decision Required**: Choose between:
1. Accept 20% CAGR with 1.5 Sharpe (realistic)
2. Push for 35% CAGR (may require accepting Sharpe < 1.5)
3. Invest in improving signal quality (long-term solution)

**Recommendation**: Deploy Iteration 1 configuration for live trading while continuing R&D on signal quality improvements.
