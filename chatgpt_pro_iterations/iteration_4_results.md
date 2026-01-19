# Iteration 4 Results

**Date**: 2026-01-19

## Tests Performed

Testing different position sizes using Iteration 1's signal filters.

| Test | Max Positions | Position Size | CAGR | Sharpe | Trades | Max DD |
|------|---------------|---------------|------|--------|--------|--------|
| Iter 1 (baseline) | 10 | 10% | **20.05%** | **1.53** | 328 | -17.87% |
| Iter 4a | 8 | 12.5% | 19.57% | 1.45 | 271 | **-16.93%** |
| Iter 4b | 6 | 16.7% | 19.35% | 1.38 | 213 | -17.40% |

## Analysis

### Outcome
- Larger position sizes did NOT improve performance
- CAGR dropped from 20.05% to 19.57% (8 pos) and 19.35% (6 pos)
- Sharpe also dropped
- Fewer trades due to higher per-position requirement

### Key Insight
**10 positions (10% each) remains optimal**
- More diversification = better risk-adjusted returns
- Fewer positions = fewer opportunities captured
- The trade count dropped significantly (328 → 271 → 213)

### Why Larger Positions Didn't Help
1. Fewer concurrent positions = fewer trades per quarter
2. CAP per quarter (12) becomes harder to fill with larger positions
3. Diversification benefit outweighs concentration benefit

## Best Configuration Still: Iteration 1
- CAGR: 20.05%
- Sharpe: 1.53
- 10 positions, 10% each
- 328 trades over 8 years
