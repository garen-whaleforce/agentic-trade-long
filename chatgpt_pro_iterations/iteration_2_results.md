# Iteration 2 Results

**Date**: 2026-01-19

## Parameter Changes Applied

Based on ChatGPT Pro recommendations:

| Parameter | Iteration 1 | Iteration 2 |
|-----------|-------------|-------------|
| D4_MIN_EPS | 0.02 | 0.03 |
| D4_MIN_POSITIVES | 2 | 3 |
| D4_MAX_SOFT_VETOES | 1 | 0 |
| D6_REQUIRE_LOW_RISK | False | True |

## Backtest Results Comparison

| Metric | Baseline | Iteration 1 | Iteration 2 | Target |
|--------|----------|-------------|-------------|--------|
| **CAGR** | 14.16% | 20.05% | 17.43% | >35% |
| **Sharpe** | 1.91 | 1.53 | 1.41 | >2 |
| **Win Rate** | 86.11% | 72.26% | 74.42% | 70-75% |
| **Total Trades** | 180 | 328 | 301 | More |
| **Max Drawdown** | -16.95% | -17.87% | -21.52% | - |
| **Annual Vol** | 7.06% | 12.41% | 11.90% | - |
| **Avg Exposure** | 23.03% | 43.89% | 40.00% | - |
| **Profit Factor** | 4.06 | 2.57 | 2.54 | - |

## Trade Distribution by Tier

| Tier | Iteration 1 | Iteration 2 |
|------|-------------|-------------|
| D7_CORE | 226 | 226 |
| D6_STRICT | 178 | 125 |
| D5_GATED | 58 | 58 |
| D4_ENTRY | 421 | 218 |

## Analysis

### Negative Outcomes
1. **CAGR dropped** from 20.05% to 17.43%
2. **Sharpe dropped** from 1.53 to 1.41
3. **Max drawdown worsened** from -17.87% to -21.52%
4. Tightening D4 reduced trade count but hurt performance

### Root Cause
- D4 trades that were filtered out may have included some winners
- D6 low risk requirement filtered out potentially profitable trades
- Fewer trades = less diversification = higher volatility impact

### Key Learning
- Tightening filters doesn't always improve performance
- Need to focus on increasing CAGR, not just improving win rate
- May need to RELAX HIGH_RISK block (1,134 signals blocked)

## Next Steps (Iteration 3)
- Consider relaxing HIGH_RISK block
- Focus on increasing trade count while maintaining quality
- Explore different D4/D5 configurations
