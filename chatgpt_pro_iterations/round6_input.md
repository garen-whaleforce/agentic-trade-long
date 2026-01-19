# ChatGPT Pro Round 6 - Deep Optimization Request

**Date**: 2026-01-19
**Objective**: Achieve CAGR > 35% AND Sharpe > 2.0
**Current Best**: CAGR 20.05%, Sharpe 1.53 (Iteration 1)
**Gap to Target**: CAGR +14.95%, Sharpe +0.47

---

## Executive Summary

We have completed 5 iterations of parameter tuning, achieving 41.6% CAGR improvement but still falling short of targets. The core issue is **signal quality ceiling** - our current LLM prompts generate too many marginal trades (D4/D5 tier) that dilute returns.

**Key Insight from Previous Iterations**:
- Parameter tuning alone cannot bridge the gap
- Need to improve **LLM prompt quality** to generate better signals
- D4/D5 tiers (47.7% of trades) have lower quality but necessary for volume

---

## Current System Architecture

### Multi-Agent RAG Pipeline

```
Transcript Input
    ↓
MainAgent.extract() - Extract facts from earnings call
    ↓
MainAgent.delegate() - Route facts to specialized agents
    ↓
├── ComparativeAgent - Peer comparison analysis
├── HistoricalEarningsAgent - Historical guidance validation
└── HistoricalPerformanceAgent - Historical stock performance
    ↓
MainAgent.summarise() - Generate Direction Score (0-10) & Vetoes
    ↓
7-TIER Signal Generation (D7→D6→D5→D4→D3)
    ↓
V10 Enhanced Scoring - Position sizing based on tier + utility
    ↓
Final Trade Signal
```

---

## Current LLM Prompts (Critical Section)

### Main Agent System Message

```
You are a seasoned portfolio manager specializing in post-earnings stock price prediction over a 30-trading-day horizon.

Your expertise includes:
- Interpreting management tone and forward guidance
- Comparing results against investor expectations
- Weighing bullish vs bearish catalysts for medium-term price movements
- Calibrating conviction levels (Direction 0-10) based on evidence strength

Key principles:
- Be conservative: strong quarters alone don't guarantee price appreciation
- Forward guidance and tone often matter more than reported results
- Consider sustainability of catalysts over 30 days, not just immediate reactions
- Use the full Direction scale appropriately (avoid clustering around 5-6)

Critical asymmetric insights:
- Weak guidance or cautious tone predicts price DECLINE more reliably than strong results predict gains
- Be especially skeptical when "record" or "beat" quarters are accompanied by ANY hint of deceleration
- Markets often "sell the news" on expected beats - focus on TRUE surprises vs already-priced-in expectations
- Negative signals (margin compression, guidance cuts, cautious tone) deserve 2x the weight of positive signals
- When in doubt between UP and DOWN, lean toward DOWN - the base rate for post-earnings declines is higher than most expect
```

### Extraction System Message

```
You are a precise fact extraction specialist for earnings call transcripts.

Your role:
- Extract concrete, verifiable facts from earnings calls
- Categorize each fact into: Result, Forward-Looking, Risk Disclosure, Sentiment, Macro, or Warning Sign
- Include specific numbers, percentages, and metrics whenever available
- Preserve the exact wording of management guidance and outlook statements
- Pay special attention to Warning Signs (inventory build-up, DSO increases, churn, restructuring, margin pressure)

Quality standards:
- Each fact should be self-contained and understandable without additional context
- Prefer quantitative facts over vague qualitative statements
- Capture both positive and negative information objectively
- Prioritize Warning Signs as they are highly predictive of negative price movements
```

### Comparative Agent System Message

```
You are a peer comparison analyst specializing in sector-relative performance analysis.

Your role:
- Compare the company's metrics and guidance against peer companies in the same sector
- Identify whether the company is outperforming, underperforming, or in-line with peers
- Highlight competitive advantages or disadvantages revealed in the earnings call
- Assess sector-wide trends that may affect the 30-day price outlook

Output requirements:
- Be specific about which peers you're comparing against
- Quantify differences where possible (e.g., "Revenue growth of 15% vs peer average of 8%")
- Conclude with an Impact Score (0-10) indicating peer comparison's effect on 30-day outlook
```

---

## Performance History (Iterations 1-5)

| Iteration | Key Change | CAGR | Sharpe | Win Rate | Trades | Result |
|-----------|------------|------|--------|----------|--------|--------|
| Baseline | Conservative (D7/D6 only) | 14.16% | 1.91 | 86.11% | 180 | Too conservative |
| **Iter 1** | **Enable D4/D5, Relax filters** | **20.05%** | **1.53** | **72.26%** | **328** | **✅ Best** |
| Iter 2 | Tighten D4 filters | 17.43% | 1.41 | 74.42% | 301 | ❌ Worse |
| Iter 3 | Relax HIGH_RISK, Enable D3 | 19.01% | 1.40 | 69.91% | 339 | ❌ Worse |
| Iter 4 | Test position sizing (8/6 pos) | 19.57% | 1.45 | 71.85% | 271 | ❌ Worse |
| Iter 5 | Final analysis (no backtest) | - | - | - | - | Strategic roadmap |

### Trade Distribution (Iteration 1)

| Tier | Count | % | Quality Assessment |
|------|-------|---|-------------------|
| D4_ENTRY | 421 | 47.7% | **Lower quality, necessary for volume** |
| D7_CORE | 226 | 25.6% | High quality |
| D6_STRICT | 178 | 20.2% | Medium-high quality |
| D5_GATED | 58 | 6.6% | Medium quality |

**Problem**: D4_ENTRY dominates but has lower win rate and return per trade.

---

## Current Configuration (Iteration 1 - Best)

```python
# Tier Configuration
D7_ENABLED = True
D6_ENABLED = True
D5_ENABLED = True  # Changed from False
D4_ENABLED = True  # Changed from False
D3_ENABLED = False  # Keep disabled - insufficient quality

# D7 CORE Parameters
D7_MIN_DAY_RET = 1.0  # Relaxed from 1.5%
D7_REQUIRE_EPS_POS = True
D7_BLOCKED_SECTORS = ["Real Estate"]

# D6 STRICT Parameters
D6_MIN_EPS_SURPRISE = 0.5
D6_REQUIRE_LOW_RISK = False  # Changed from True
D6_EXCLUDE_SECTORS = []  # Removed Technology restriction

# Risk Control
RISK_DAY_LOW = -5.0  # Relaxed from -3.0%
RISK_EPS_MISS = 0.0
RISK_RUNUP_HIGH = 15.0

# Position Management
MAX_POSITIONS = 10  # Changed from 12
POSITION_SIZE = 0.10  # 10% per position
```

---

## Root Cause Analysis

### Why Can't We Reach 35% CAGR?

**Mathematical Constraint**:
- Current: 328 trades over 8 years = 41 trades/year
- Average return per trade: ~20%
- CAGR formula limited by trade count × quality

**To reach 35% CAGR, we need**:
```
Option A: More trades (70+ per year)
  → Requires relaxing filters further
  → Risk: Win rate drops below 65%, Sharpe < 1.3

Option B: Higher return per trade (35%+ avg)
  → Requires BETTER SIGNAL QUALITY
  → This is the path forward ✅

Option C: Larger position sizes
  → Already tested in Iteration 4
  → Result: FAILED (fewer trades, worse returns)
```

### The Signal Quality Problem

**Evidence**:
1. D4_ENTRY trades (47.7%) have ~12-15% avg return vs D7 (25%+)
2. Profit factor dropped from 4.06 to 2.57 when enabling D4/D5
3. Volatility nearly doubled (7% → 12%)

**Root Cause**: Current LLM prompts don't distinguish between:
- Strong conviction signals (should be D7)
- Medium conviction signals (should be D5-D6)
- Weak conviction signals (currently classified as D4, should be filtered)

---

## Request to ChatGPT Pro

**Primary Goal**: Redesign LLM prompts to improve signal quality and reach CAGR > 35%, Sharpe > 2.0

### Specific Questions

1. **Prompt Engineering**:
   - How can we improve the Main Agent System Message to generate more D7/D6 signals?
   - Should we add explicit conviction calibration examples?
   - Should we add negative examples (what NOT to rate as high direction)?

2. **Fact Extraction**:
   - Are we extracting the right types of facts?
   - Should we add more emphasis on "surprise" elements vs "expected" elements?
   - How to better capture management tone and non-verbal signals?

3. **Comparative Analysis**:
   - How to make peer comparisons more predictive?
   - Should we add sector momentum context?
   - How to weight relative performance vs absolute performance?

4. **Direction Score Calibration**:
   - Current problem: Too many scores cluster around 4-6
   - How to use the full 0-10 scale more effectively?
   - Should we add explicit calibration anchors (e.g., "Direction 8 = top 10% conviction")?

5. **Veto Logic**:
   - Are we missing critical warning signs?
   - Should soft vetoes be weighted differently?
   - How to detect "hidden" guidance cuts?

6. **Multi-Model Approach**:
   - Should we use GPT-5.2 for main analysis and GPT-4o-mini for fact extraction?
   - Or should we try Claude Opus 4.5 for better reasoning?
   - Would ensemble approach (multiple models voting) improve quality?

### Constraints

**Must maintain**:
- Win rate 70-75% (acceptable range: 68-77%)
- Max drawdown < -25%
- No lookahead bias (LOOKAHEAD_ASSERTIONS=true)
- No overfitting (changes only based on Tune Set 2019-2023)

**Can adjust**:
- LLM prompts (system messages, user prompts, examples)
- Model selection (GPT-5.2, Claude Opus 4.5, etc.)
- Fact extraction categories
- Agent delegation logic
- Direction score interpretation

---

## Available Data & Context

### Market Anchors (Available at Decision Time)
- eps_surprise (EPS beat/miss %)
- earnings_day_return (stock return on earnings day)
- pre_earnings_5d_return (5-day momentum before earnings)

### Historical Context (Via Neo4j)
- Past earnings call facts
- Historical financial statements
- Peer company data

### Models Available (via LiteLLM)
- GPT-5.2 / GPT-5.1 / GPT-5
- GPT-5-mini / GPT-5-nano
- GPT-4o / GPT-4o-mini
- Claude Opus 4.5 / Claude Sonnet 4.5
- Gemini 3 Pro / Gemini 3 Flash
- o3 / o3-batch (Reasoning mode)

---

## Success Criteria

**Round 6 Target**:
- CAGR: 25%+ (stretch: 30%+)
- Sharpe: 1.7+ (stretch: 1.9+)
- Win Rate: 70-75%
- Total Trades: 250-400

**Ultimate Target** (by Round 10):
- CAGR: 35%+
- Sharpe: 2.0+
- Win Rate: 70-75%

---

## Output Format Request

Please provide:

1. **Diagnosis**: What are the 3 most critical problems with current prompts?

2. **Specific Prompt Improvements**:
   - Exact text for revised Main Agent System Message
   - Exact text for revised Extraction System Message
   - Any new prompt sections to add

3. **Model Selection Recommendation**:
   - Which model(s) for which tasks?
   - Any ensemble approaches?

4. **Expected Impact**:
   - Estimated CAGR improvement
   - Estimated Sharpe improvement
   - Trade-offs and risks

5. **Implementation Priority**:
   - What to change first (highest impact)
   - What to test in A/B fashion

---

## Additional Context

### Why This Matters

Current Iteration 1 (20% CAGR) is **good but not great**:
- Outperforms most quant strategies
- But falls short of institutional quality (30%+ CAGR)
- Sharpe 1.53 is acceptable but not exceptional

**The Opportunity**:
- We have strong infrastructure (7-TIER, V10 scoring, multi-agent RAG)
- We have quality data (transcripts, Neo4j knowledge graph, market anchors)
- We just need better **signal extraction** from the same data

### Files Available

If you need to see the full prompt implementation:
- `EarningsCallAgenticRag/agents/prompts/prompts.py` (870 lines)
- `EarningsCallAgenticRag/agents/mainAgent.py`
- `agentic_rag_bridge.py` (7-TIER implementation)
- `v10_scoring.py` (Position sizing logic)

---

**Please provide your deep analysis and specific, actionable recommendations.**
