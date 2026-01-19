# Round 9 Input - Cross-Validation & Fact Delegation Optimization

**Date**: 2026-01-19
**Round**: 9 of 10 (Fast Iteration Mode)
**Accumulated Changes**: Rounds 6-8 (prompts + veto logic + tier gates)

---

## Context

After Rounds 6-8 optimizations (prompts, veto logic, tier gates), we're now focusing on cross-validation mechanisms and fact delegation logic to improve signal reliability and reduce false positives.

**Current Performance (Iteration 1)**:
- CAGR: 20.05%
- Sharpe: 1.53
- Win Rate: 72.26%

**Rounds 6-8 Expected Impact**:
- CAGR: 32-36% (projected)
- Sharpe: 1.8-2.1 (projected)
- D7/D6 Ratio: >60%

**Ultimate Target**:
- CAGR: >35%
- Sharpe: >2.0

---

## Current Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MainAgent                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 1. extract(): Extract facts from transcript                 │   │
│  │ 2. delegate(): Send facts to specialist agents              │   │
│  │ 3. summarise(): Aggregate agent results → Direction Score   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐
│ Comparative │ │ Historical  │ │ Historical          │
│ Agent       │ │ Earnings    │ │ Performance         │
│             │ │ Agent       │ │ Agent               │
│ 同業比較    │ │ 歷史財報    │ │ 歷史股價表現        │
└─────────────┘ └─────────────┘ └─────────────────────┘
```

### Current Fact Delegation Logic

```python
# orchestrator_parallel_facts.py

def _delegate_facts(facts: List[Fact]) -> Dict[str, List[Fact]]:
    """
    Route facts to appropriate specialist agents.
    """
    delegation = {
        "comparative": [],
        "historical_earnings": [],
        "historical_performance": []
    }

    for fact in facts:
        category = fact.category.lower()

        # Simple keyword-based routing
        if "guidance" in category or "forward" in category:
            delegation["comparative"].append(fact)
            delegation["historical_earnings"].append(fact)

        if "surprise" in category or "beat" in category:
            delegation["comparative"].append(fact)

        if "performance" in category or "return" in category:
            delegation["historical_performance"].append(fact)

    return delegation
```

**Problems**:
1. **No cross-validation**: Agents work in isolation, no consistency checking
2. **Simplistic routing**: Keyword-based delegation may miss nuanced facts
3. **No conflict detection**: Contradictory agent conclusions not flagged
4. **Equal weighting**: All agent outputs treated equally regardless of reliability

---

## Current Agent Outputs

### Comparative Agent
```python
{
    "impact_score": 7,  # 0-10 scale
    "analysis": "Company outperforms peers by 15%...",
    "relative_surprise": "positive"
}
```

### Historical Earnings Agent
```python
{
    "impact_score": 6,  # -2 to +2 scale (different from comparative!)
    "credibility_trend": "improving",
    "sandbagging_detected": false
}
```

### Historical Performance Agent
```python
{
    "historical_pattern": "strong_post_earnings",
    "confidence": "high"
}
```

**Problems**:
1. **Inconsistent scales**: Impact scores on different scales (0-10 vs -2 to +2)
2. **No uncertainty quantification**: No confidence intervals or ranges
3. **Limited cross-referencing**: Agents don't see each other's conclusions
4. **No conflict resolution**: What if Comparative says "positive" but Historical says "declining"?

---

## Cross-Validation Issues

### Issue 1: Contradictory Signals

**Scenario**: Comparative Agent says "relative outperformance" (Impact Score 8) but Historical Earnings Agent detects "decreasing credibility" (Impact Score -1)

**Current Behavior**: MainAgent averages the scores → misleading signal

**Better Approach**: Flag the contradiction, reduce confidence, or apply conflict resolution logic

### Issue 2: Confirmation Bias

**Scenario**: All agents receive the same facts → may all confirm the same bias

**Current Behavior**: No mechanism to challenge consensus

**Better Approach**: Devil's advocate agent or explicit counter-evidence search

### Issue 3: Missing Context

**Scenario**: Comparative Agent sees "15% revenue beat" but doesn't know company had guidance cut last quarter

**Current Behavior**: Comparative Agent may over-weight the beat

**Better Approach**: Cross-agent context sharing (Historical Earnings informs Comparative)

---

## Fact Delegation Problems

### Problem 1: Over-Delegation

**Current**: Some facts sent to all agents (e.g., "guidance cut" → Comparative + Historical Earnings)

**Issue**: Redundant processing, increased cost, potential double-counting

**Better**: Smarter routing based on fact type and relevance

### Problem 2: Under-Delegation

**Current**: Some important facts not sent to any agent

**Issue**: Information loss, incomplete analysis

**Better**: Ensure all extracted facts delegated to at least one agent

### Problem 3: No Prioritization

**Current**: All facts treated equally

**Issue**: Minor facts dilute signal from major facts

**Better**: Weight facts by importance (e.g., "guidance cut" > "inventory up 2%")

---

## Round 9 Optimization Request

**Focus Areas**:
1. **Cross-Validation Logic**: How to detect and resolve contradictions between agents?
2. **Fact Delegation Strategy**: How to route facts more intelligently?
3. **Agent Output Normalization**: How to make scores comparable across agents?
4. **Conflict Resolution**: How to handle disagreements between agents?
5. **Confidence Quantification**: How to express uncertainty in agent outputs?

---

### Specific Questions

#### 1. Cross-Validation Mechanisms

**Q1.1**: Should we implement a "sanity check" step after all agents return?

```python
# Example: Detect contradictions
if comparative_impact_score > 7 and historical_impact_score < -1:
    logger.warning("Conflict: Strong comparative signal but weak historical credibility")
    confidence_penalty = -2  # Reduce final Direction Score
```

**Q1.2**: Should we have agents review each other's conclusions?

```python
# Example: Sequential agent calls
comparative_result = ComparativeAgent.run(facts)
historical_result = HistoricalEarningsAgent.run(facts, context=comparative_result)
# Historical agent can challenge Comparative's conclusions
```

**Q1.3**: What conflict resolution strategy is best?

- Option A: Average with conflict penalty
- Option B: Trust the more reliable agent (e.g., Historical over Comparative)
- Option C: Require agreement threshold (e.g., all agents within 2 points)

#### 2. Fact Delegation Optimization

**Q2.1**: How to route facts more intelligently?

```python
# Current: Simple keywords
# Better: Fact type-specific routing?

FACT_ROUTING = {
    "Surprise": ["comparative", "historical_earnings"],
    "Guidance": ["comparative", "historical_earnings"],
    "Tone": ["historical_earnings"],  # Only historical earnings?
    "Market Reaction": ["historical_performance"],
    "Warning Sign": ["historical_earnings", "comparative"],
    "Risk Disclosure": ["comparative"]  # Sector comparison?
}
```

**Q2.2**: Should we prioritize facts by importance?

```python
# High-priority facts
HIGH_PRIORITY = ["GuidanceCut", "SevereMarginCompression", "RegulatoryRisk"]

# Low-priority facts
LOW_PRIORITY = ["MinorInventoryChange", "RoutineCompliance"]

# Weight agent output by fact priority?
```

**Q2.3**: Should we implement fact deduplication?

```python
# Example: Multiple facts about "guidance cut"
facts = [
    Fact(category="Guidance", content="Q1 guidance lowered 10%"),
    Fact(category="Guidance", content="Full-year guidance revised down"),
    Fact(category="Warning Sign", content="Weak outlook for next quarter")
]

# These might be referring to the same underlying issue
# Should we deduplicate or merge them?
```

#### 3. Agent Output Normalization

**Q3.1**: Should all agents use the same Impact Score scale?

```python
# Current: Inconsistent
# - Comparative: 0-10
# - Historical Earnings: -2 to +2
# - Historical Performance: No numeric score

# Better: All use 0-10 or all use -5 to +5?
```

**Q3.2**: How to combine agent scores into final Direction Score?

```python
# Option A: Simple average
direction_score = (comparative_score + historical_earnings_score + historical_performance_score) / 3

# Option B: Weighted average (prioritize certain agents)
direction_score = (
    0.4 * comparative_score +
    0.4 * historical_earnings_score +
    0.2 * historical_performance_score
)

# Option C: Consensus-based (require agreement)
if abs(comparative_score - historical_earnings_score) > 3:
    direction_score = min(comparative_score, historical_earnings_score)  # Conservative
```

#### 4. Conflict Detection Examples

**Conflict Type A: Strong vs Weak**
- Comparative: Impact Score 9 (strong outperformance)
- Historical Earnings: Impact Score 2 (weak credibility)
- **Resolution**: Flag conflict, reduce Direction Score by 2 points

**Conflict Type B: Positive vs Negative**
- Comparative: Positive relative surprise
- Historical Performance: Declining post-earnings pattern
- **Resolution**: Neutral signal, Direction Score = 5

**Conflict Type C: High Confidence vs Low Confidence**
- Comparative: High confidence (large sample of peers)
- Historical Earnings: Low confidence (only 2 quarters of history)
- **Resolution**: Weight Comparative more heavily

#### 5. Confidence Quantification

**Q5.1**: Should agents return confidence scores?

```python
# Example agent output
{
    "impact_score": 7,
    "confidence": 0.8,  # 0-1 scale
    "uncertainty_range": [6, 8],  # Possible range
    "evidence_quality": "high"  # high/medium/low
}
```

**Q5.2**: How to use confidence in final decision?

```python
# Confidence-weighted combination
direction_score = (
    comparative_score * comparative_confidence +
    historical_earnings_score * historical_earnings_confidence +
    historical_performance_score * historical_performance_confidence
) / (comparative_confidence + historical_earnings_confidence + historical_performance_confidence)
```

---

## Expected Outcomes

**Round 9 Target Contribution**:
- Reduce false positives by 15-20% (better conflict detection)
- Improve Direction Score accuracy (less noise from contradictory signals)
- Better fact utilization (smarter delegation)
- More reliable agent outputs (confidence quantification)

**Cumulative Impact (Rounds 6-9)**:
- CAGR: 20.05% → **34-38%** (closer to target)
- Sharpe: 1.53 → **1.9-2.2** (approaching/exceeding target)
- Win Rate: 72.26% → **72-76%** (maintain or improve)
- D7/D6 Ratio: 45.8% → **>65%**
- False Positive Rate: Reduced significantly

---

## Implementation Constraints

**Must Not Break**:
- Multi-agent orchestration framework
- Existing agent prompts (already optimized in Rounds 6-7)
- Veto system (Round 7)
- Tier gates (Round 8)

**Can Modify**:
- Fact delegation logic
- Agent output processing
- Cross-validation checks
- Conflict resolution strategies

---

## Request to ChatGPT Pro

Please analyze the current multi-agent architecture and provide:

1. **Cross-validation strategy**: How to detect and resolve agent contradictions?
2. **Fact delegation improvements**: How to route facts more intelligently?
3. **Agent output normalization**: Should we standardize Impact Score scales?
4. **Conflict resolution logic**: Code-level recommendations for handling disagreements
5. **Confidence quantification**: How to express and use uncertainty in agent outputs?
6. **Expected performance impact**: Quantified if possible

Focus on **actionable changes** that can be directly implemented in `orchestrator_parallel_facts.py` and agent files.

---

## Success Metrics

**This round successful if**:
- Clear cross-validation strategy provided
- Fact delegation optimization specified
- Conflict resolution logic detailed
- Expected to contribute +2-4% CAGR, +0.1-0.2 Sharpe

**Cumulative success if (Rounds 6-9)**:
- CAGR approaching 35%
- Sharpe approaching 2.0
- False positive rate reduced
- Signal reliability improved

---

## Data Context

**Available for Cross-Validation**:
- All agent outputs (Impact Scores, analysis text)
- Original facts extracted by MainAgent
- Market anchors (eps_surprise, earnings_day_return)
- Company metadata (sector, size)

**NOT Available**:
- Future performance (lookahead protection)
- Other companies' earnings (for current analysis)

---

**Note**: Final round (Round 10) will focus on integration and fine-tuning. Round 9 should establish robust cross-validation and fact delegation logic.
