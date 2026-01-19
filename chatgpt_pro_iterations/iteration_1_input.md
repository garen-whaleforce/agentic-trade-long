# Iteration 1 Input - ChatGPT Pro Analysis
**Date**: 2026-01-19
**Task ID**: TBD

## Current Baseline Metrics (v1.1-live-safe)

| Metric | Current Value | Target | Gap |
|--------|---------------|--------|-----|
| **CAGR** | 14.16% | >35% | -20.84% |
| **Sharpe Ratio** | 1.91 | >2 | -0.09 |
| **Win Rate** | 86.11% | 70-75% | Already exceeded |
| **Max Drawdown** | -16.95% | - | - |
| **Total Trades** | 180 (8 years) | - | ~22.5/year |
| **Avg Exposure** | 23.03% | - | Very low |

## Current Strategy Configuration

### Tier Rules
- **D7 CORE** (Direction >= 7): MIN_DAY_RET=1.5%, REQUIRE_EPS_POS=1
- **D6 STRICT** (Direction = 6): MIN_EPS_SURPRISE=0.0, MIN_DAY_RET=1.0%

### Position Sizing
- CAP per Quarter: 12 (First-N)
- Max Concurrent Positions: 12
- Allocation: 1/12 Equal Weight (8.33% per position)
- Holding Period: 30 trading days

## Problem Analysis

1. **CAGR too low (14.16% vs 35% target)**
   - Root cause: Only 180 trades over 8 years (22.5/year avg)
   - Average exposure only 23% (position size too conservative)
   - Many quarters have fewer than 12 trades

2. **Win rate too high (86% vs 70-75% target)**
   - Current filters are too strict
   - Missing potentially profitable trades
   - Trade-off: higher win rate but fewer trades = lower CAGR

## Available Data

| Year | Total Samples | trade_long=True | Trades Executed |
|------|---------------|-----------------|-----------------|
| 2017 | 1,336 | ~50 | 37 |
| 2018 | 1,831 | ~45 | 30 |
| 2019 | 1,857 | ~8 | 3 |
| 2020 | 1,904 | ~20 | 12 |
| 2021 | 1,927 | ~40 | 28 |
| 2022 | 1,945 | ~35 | 25 |
| 2023 | 1,958 | ~35 | 25 |
| 2024 | 1,978 | ~20 | 15 |
| 2025 | 1,526 | ~8 | 4 |

## Request to ChatGPT Pro

Priority: **CAGR > Sharpe > Win Rate**

Please analyze and provide SPECIFIC recommendations:

1. **How to increase CAGR from 14% to 35%+?**
   - Should we lower Direction Score threshold (D5, D4)?
   - Should we relax entry filters (MIN_DAY_RET, EPS_SURPRISE)?
   - Should we increase position size per trade?

2. **Trade-off analysis**:
   - If we accept win rate dropping to 70-75%, how many more trades can we make?
   - What's the optimal balance between trade quantity and quality?

3. **Specific parameter recommendations**:
   - New tier thresholds for D5, D4
   - New entry filters (MIN_DAY_RET, MIN_EPS_SURPRISE)
   - New position sizing (CAP per quarter, allocation %)

4. **Risk considerations**:
   - How to maintain Sharpe > 2 while increasing CAGR?
   - Max acceptable drawdown increase?

Please provide CONCRETE numbers, not general advice.
