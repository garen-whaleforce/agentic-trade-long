# Iteration 1 Results

**Date**: 2026-01-19

## Parameter Changes Applied

Based on ChatGPT Pro recommendations:

| Parameter | Baseline | Iteration 1 |
|-----------|----------|-------------|
| D7_MIN_DAY_RET | 1.5% | 1.0% |
| D6_MIN_EPS_SURPRISE | 0.0% | 0.5% |
| D6_REQUIRE_LOW_RISK | True | False |
| D6_EXCLUDE_SECTORS | Technology | None |
| D5_ENABLED | False | True |
| D4_ENABLED | False | True |
| RISK_DAY_LOW | -3% | -5% |
| MAX_POSITIONS | 12 | 10 |

## Backtest Results Comparison

| Metric | Baseline | Iteration 1 | Change | Target |
|--------|----------|-------------|--------|--------|
| **CAGR** | 14.16% | 20.05% | +5.89% | >35% |
| **Sharpe** | 1.91 | 1.53 | -0.38 | >2 |
| **Win Rate** | 86.11% | 72.26% | -13.85% | 70-75% |
| **Total Trades** | 180 | 328 | +148 | More |
| **Max Drawdown** | -16.95% | -17.87% | -0.92% | - |
| **Annual Vol** | 7.06% | 12.41% | +5.35% | - |
| **Avg Exposure** | 23.03% | 43.89% | +20.86% | - |
| **Profit Factor** | 4.06 | 2.57 | -1.49 | - |

## Trade Distribution by Tier

| Tier | Count | % |
|------|-------|---|
| D4_ENTRY | 421 | 47.7% |
| D7_CORE | 226 | 25.6% |
| D6_STRICT | 178 | 20.2% |
| D5_GATED | 58 | 6.6% |

## Analysis

### Positive Outcomes
1. **CAGR increased by 41.6%** (14.16% → 20.05%)
2. **Trade count increased by 82%** (180 → 328)
3. **Win rate within target range** (72.26% in 70-75%)
4. **Exposure increased** - utilizing more capital

### Negative Outcomes
1. **Sharpe dropped below target** (1.53 < 2.0)
2. **Volatility nearly doubled** (7.06% → 12.41%)
3. **Profit factor dropped** (4.06 → 2.57)

### Root Cause Analysis
- D4_ENTRY tier contributes 47.7% of trades but likely has lower quality
- Relaxing D6 risk requirements introduced more volatile trades
- Higher exposure means more correlation to market drawdowns

## Files Generated
- `tuning_results/signals_iteration1.csv` - 882 signals
- `tuning_results/backtest_iteration1/` - Full backtest results
