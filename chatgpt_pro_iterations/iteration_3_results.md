# Iteration 3 Results

**Date**: 2026-01-19

## Parameter Changes Applied

Based on ChatGPT Pro recommendations:

| Parameter | Iteration 1 | Iteration 3 |
|-----------|-------------|-------------|
| RISK_EPS_MISS | 0.0 | -0.05 (allow 5% miss) |
| RISK_DAY_LOW | -5.0% | -7.0% |
| RISK_RUNUP_HIGH | 15% | 20% |
| D3_ENABLED | False | True |

## Backtest Results Comparison

| Metric | Baseline | Iter 1 | Iter 2 | Iter 3 | Target |
|--------|----------|--------|--------|--------|--------|
| **CAGR** | 14.16% | **20.05%** | 17.43% | 19.01% | >35% |
| **Sharpe** | 1.91 | **1.53** | 1.41 | 1.40 | >2 |
| **Win Rate** | 86.11% | 72.26% | 74.42% | 69.91% | 70-75% |
| **Trades** | 180 | 328 | 301 | 339 | More |
| **Max DD** | -16.95% | -17.87% | -21.52% | -18.40% | - |

## Analysis

### Outcome
- More trades (339 vs 328) but CAGR dropped slightly
- Win rate dropped below target (69.91% < 70%)
- Relaxing HIGH_RISK didn't help as expected

### Key Insight
**Iteration 1 remains the best performer**
- CAGR: 20.05% (highest)
- Sharpe: 1.53 (highest)
- Win Rate: 72.26% (within target)

### Root Cause
- Relaxed HIGH_RISK allowed through lower quality trades
- D3_WIDE tier added 19 trades but they may be low quality
- More trades ≠ better performance

## Best Configuration So Far: Iteration 1
