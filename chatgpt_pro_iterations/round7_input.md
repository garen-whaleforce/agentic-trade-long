# ChatGPT Pro Round 7 - Veto & Helper Agents Optimization

**Date**: 2026-01-19
**Objective**: Optimize veto logic and helper agent prompts
**Previous**: Round 6 improved Main Agent + Extraction prompts
**Target**: Continue towards CAGR > 35%, Sharpe > 2.0

---

## Round 6 Accomplishments ✅

### Implemented Changes
1. **Main Agent System Message** - Enhanced with explicit Direction Score calibration
2. **Extraction System Message** - Added Surprise/Tone/Market Reaction categories

### Expected Impact (from ChatGPT Pro analysis)
- CAGR improvement: +10-15% (target 25-30%)
- D7/D6 ratio increase: from 45.8% to >50%
- D4 ratio decrease: from 47.7% to <35%

---

## Current System Architecture

```
Transcript → Extraction → Fact Delegation → Helper Agents → Main Agent Summary
                                ↓
                    ┌───────────┼───────────┐
                    ↓           ↓           ↓
            Comparative  HistoricalEarnings  HistoricalPerformance
                    ↓           ↓           ↓
              Analysis → Summarized → Direction Score + Vetoes
                                          ↓
                                    7-TIER Signal Generation
```

---

## Round 7 Focus: Veto Logic & Helper Agents

### Problem Areas Identified

#### 1. Veto System Needs Refinement 🚫

**Current Veto Mechanism**:
```python
Hard Vetoes (Block trade):
- GuidanceCut: Company lowers guidance

Soft Vetoes (Reduce position 0.9x per veto):
- DemandSoftness: Weak demand signals
- MarginWeakness: Margin compression
- VisibilityWorsening: Reduced visibility
- CashBurn: Excessive cash burn
```

**Issues**:
1. Only 1 hard veto (GuidanceCut) - may miss other critical risks
2. Soft vetoes apply uniformly (0.9x) - should vary by severity
3. No veto for "Hidden guidance cuts" (cautious tone without explicit cut)
4. Insufficient detection of early warning signs

**Impact**:
- May generate D7/D6 signals for risky stocks
- Profit factor could suffer from undetected risks

#### 2. Helper Agent Prompts Are Generic 📊

**Comparative Agent** (Current):
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

**Issues**:
- Doesn't emphasize relative surprise (company beats consensus, but peers beat more)
- Doesn't distinguish sector-wide tailwinds vs company-specific strength
- Impact Score (0-10) lacks calibration guidance

#### 3. Historical Earnings Agent Lacks Context 📈

**Historical Earnings Agent** (Current):
```
You are a historical guidance validation analyst.

Your role:
- Compare current quarter results against management's prior guidance and projections
- Track whether the company consistently beats, meets, or misses its own guidance
- Identify patterns in management's forecasting accuracy and credibility
- Assess whether current guidance should be trusted based on historical track record

Output requirements:
- Reference specific prior quarter guidance and compare to actual results
- Note any pattern of conservative or aggressive guidance
- Conclude with an Impact Score (0-10) indicating historical analysis's effect on 30-day outlook
```

**Issues**:
- Doesn't explicitly check for guidance sandbagging patterns
- Doesn't weight recent quarters more than distant history
- Doesn't identify trend changes (was credible, now suspicious)

---

## Request to ChatGPT Pro (Round 7)

Please provide specific improvements in these areas:

### 1. Enhanced Veto System 🎯

**Questions**:
1. What additional hard vetoes should we add?
   - Candidates: Severe margin compression (>500 bps), Major product failure, Regulatory issues, CEO departure with uncertainty
2. Should soft vetoes have variable weights?
   - Example: DemandSoftness (0.85x) vs VisibilityWorsening (0.92x)
3. How to detect "Hidden guidance cuts"?
   - Pattern: Strong results + cautious tone + vague forward guidance
4. Should we add a "Neutral" veto category?
   - For signals that don't block but add uncertainty

**Desired Output**:
- Revised veto categories (Hard/Soft/Neutral)
- Specific detection criteria for each veto
- Variable penalty weights for soft vetoes
- Examples of what triggers each veto

### 2. Improved Comparative Agent Prompt 📊

**Questions**:
1. How to better assess "relative surprise"?
   - Company beats 10%, peers beat 15% → Actually a relative miss
2. How to distinguish sector momentum vs company strength?
   - Whole sector up 20% vs company specific catalyst
3. Should Impact Score have explicit calibration?
   - Score 8-10: Significant competitive advantage
   - Score 5-7: In-line with peers
   - Score 0-4: Competitive disadvantage

**Desired Output**:
- Revised Comparative Agent System Message
- Explicit guidance on relative surprise analysis
- Calibrated Impact Score framework
- Examples of each score level

### 3. Refined Historical Earnings Agent Prompt 📈

**Questions**:
1. How to detect "Sandbagging patterns"?
   - Consistently lowball guidance then beat by 5-10%
2. Should recent quarters be weighted more?
   - Last 2 quarters 3x weight vs 2 years ago
3. How to identify credibility trend changes?
   - Previously credible, now becoming optimistic/cautious

**Desired Output**:
- Revised Historical Earnings Agent System Message
- Guidance on temporal weighting
- Sandbagging detection criteria
- Credibility trend assessment framework

### 4. Integration Strategy 🔗

**Questions**:
1. Should vetoes override high Direction Scores?
   - Example: D8 signal but 2 soft vetoes → Reduce to D6?
2. How should helper agent Impact Scores affect final Direction Score?
   - Average? Weighted? Multiplicative?
3. Should there be cross-validation between agents?
   - Comparative shows weakness but Historical shows strength → Flag inconsistency?

**Desired Output**:
- Integration rules for veto + Direction Score
- Helper agent Impact Score weighting scheme
- Cross-validation logic

---

## Constraints & Context

### Must Maintain
- Win Rate: 70-75%
- Max Drawdown: <-25%
- No lookahead bias
- Backward compatible with existing code structure

### Available Data
- Neo4j historical earnings facts
- PostgreSQL price/fundamentals
- Market anchors (eps_surprise, earnings_day_return, pre_earnings_5d_return)

### Models Available
- GPT-5.2 (current main model)
- GPT-4o-mini (current helper model)
- Claude Opus 4.5 (alternative for reasoning)

---

## Expected Outcomes

### Primary Goals
1. **Better risk detection** → Reduce false positives (D7/D6 signals that fail)
2. **More nuanced analysis** → Helper agents provide better context
3. **Improved veto accuracy** → Catch hidden risks, avoid over-vetoing

### Target Metrics (Combined with Round 6)
- CAGR: **28-32%** (vs current 20.05%, target 35%)
- Sharpe: **1.7-1.9** (vs current 1.53, target 2.0)
- Win Rate: **70-75%** (maintain)
- D7/D6 Ratio: **>55%** (vs Iter1 45.8%)

### Trade-offs to Consider
- More vetoes → Fewer trades (good if they're low-quality)
- Stricter helper agents → May filter some winners
- Complex integration → Implementation effort

---

## Success Criteria

### Minimum Requirements
- ✅ Clearer veto detection criteria
- ✅ At least 2 new hard vetoes identified
- ✅ Variable soft veto weights defined
- ✅ Helper agent prompts improved with calibration

### Ideal Outcomes
- 🎯 Comprehensive veto framework (Hard/Soft/Neutral)
- 🎯 Helper agents with explicit Impact Score calibration
- 🎯 Integration rules for veto override logic
- 🎯 Cross-validation mechanisms between agents

---

## Timeline

- **Round 7 Analysis**: 1-2 minutes (ChatGPT Pro)
- **Implementation**: 15-20 minutes
- **Testing**: Via final backtest (after Round 10)

---

## References

- Round 6 Output: [round6_output.md](round6_output.md)
- Round 6 Implementation: [round6_implementation.md](round6_implementation.md)
- Current Prompts: `EarningsCallAgenticRag/agents/prompts/prompts.py`
- Veto Logic: `agentic_rag_bridge.py` (lines with veto detection)

---

**Please provide specific, actionable recommendations with exact prompt text and veto criteria.**
