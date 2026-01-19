# Round 7 Implementation Plan (Deferred to Final Backtest)

**Status**: Documented, implementation deferred
**Reason**: Fast iteration mode - accumulate all changes, implement once

---

## Changes to Implement

### 1. Veto System Enhancements (agentic_rag_bridge.py)

#### New Hard Vetoes
- [ ] SevereMarginCompression (>500bps YoY)
- [ ] RegulatoryRisk (investigations, compliance violations)
- [ ] ExecutiveTurnover (CEO departure, key executives)

#### Updated Soft Veto Weights
- [ ] DemandSoftness: 0.90x → 0.85x
- [ ] MarginWeakness: 0.90x → 0.95x (if <300bps) or 0.90x (if >300bps)
- [ ] VisibilityWorsening: 0.90x → 0.92x
- [ ] **NEW** HiddenGuidanceCut: 0.88x

#### New Neutral Veto
- [ ] NeutralVeto: 0.95x (uncertainty without clear negative)

---

### 2. Comparative Agent Prompt (prompts.py)

```python
_DEFAULT_COMPARATIVE_SYSTEM_MESSAGE = """
You are a peer comparison analyst specializing in **relative earnings surprise** analysis.

Your role:
1. **Relative Surprise Analysis**: Compare company's earnings performance against both its own expectations AND sector performance
   - **Relative Miss**: Company misses peers by 10%+ (negative signal)
   - **In-line**: Company within ±10% of sector average (neutral)
   - **Relative Advantage**: Company beats peers by 10%+ (positive signal)

2. **Sector vs Company Distinction**:
   - If sector performs well but company underperforms → assign negative relative impact
   - If sector weak but company outperforms → assign positive relative impact
   - If both move together → attribute to sector momentum, not company strength

3. **Impact Score Calibration** (0-10):
   - **8-10**: Company outperforms peers significantly (>15% relative advantage)
   - **5-7**: Performance in line with peers (±10% relative)
   - **0-4**: Company underperforms peers significantly (>15% relative disadvantage)

Output requirements:
- Quantify relative surprise explicitly
- Distinguish sector momentum from company-specific strength
- Conclude with calibrated Impact Score (0-10)
""".strip()
```

---

### 3. Historical Earnings Agent Prompt (prompts.py)

```python
_DEFAULT_HISTORICAL_EARNINGS_SYSTEM_MESSAGE = """
You are a historical guidance validation analyst with focus on **temporal weighting** and **credibility trends**.

Your role:
1. **Sandbagging Detection**: Identify if company consistently under-promises and over-delivers
   - Pattern: 3+ consecutive quarters beating guidance by 5-10%
   - If detected: Slightly increase trust in forward guidance (+0.5 Impact Score)

2. **Temporal Weighting** (assess last 3-4 quarters primarily):
   - **Last 2 quarters**: 1.5x weight (most relevant)
   - **3-5 quarters ago**: 1.0x weight (moderately relevant)
   - **6+ quarters ago**: 0.5x weight (less relevant)

3. **Credibility Trend Assessment**:
   - **High Credibility** (Impact Score +1 to +2): 4+ quarters of meeting/exceeding expectations, guidance accuracy within ±5%
   - **Decreasing Credibility** (Impact Score -1 to -2): Repeated misses, significant outlook changes, overly optimistic patterns
   - **Stable Credibility** (Impact Score 0): Mix of beats/misses with no clear trend

Output requirements:
- Reference specific prior quarters with temporal weights
- Identify sandbagging patterns if present
- Assess credibility trend (improving/stable/declining)
- Conclude with Impact Score (-2 to +2)
""".strip()
```

---

### 4. Integration Rules (agentic_rag_bridge.py)

#### Veto Override Logic
```python
# Hard Veto: Cap Direction Score at 3-4
if has_hard_veto:
    final_direction_score = min(base_direction_score, 4)

# Soft Vetoes: Cumulative reduction
soft_veto_penalty = 0
for veto in soft_vetoes:
    if veto == "DemandSoftness":
        soft_veto_penalty += 2  # Reduce by 2 points
    elif veto == "HiddenGuidanceCut":
        soft_veto_penalty += 1.5  # Reduce by 1-2 points
    elif veto == "VisibilityWorsening":
        soft_veto_penalty += 1  # Reduce by 1 point
    elif veto == "NeutralVeto":
        soft_veto_penalty += 0.5  # Minor reduction

final_direction_score = max(base_direction_score - soft_veto_penalty, 3)
```

#### Impact Score Integration
```python
# Average helper agent Impact Scores
avg_impact_score = mean([comparative_score, historical_score, ...])

# Adjust Direction Score
if avg_impact_score >= 8:
    direction_adjustment = +2
elif avg_impact_score >= 6:
    direction_adjustment = +1
elif avg_impact_score <= 4:
    direction_adjustment = -1
elif avg_impact_score <= 2:
    direction_adjustment = -2
else:
    direction_adjustment = 0

final_direction_score += direction_adjustment
```

#### Cross-Validation
```python
# Flag conflicts
if has_hard_veto and comparative_impact_score > 7:
    confidence_penalty = -1
    logger.warning("Conflict: Hard veto but strong comparative advantage")

if historical_impact_score > 7 and len(soft_vetoes) >= 2:
    confidence_penalty = -1
    logger.warning("Conflict: High historical credibility but multiple soft vetoes")
```

---

## Implementation Schedule

### During Final Backtest Preparation
1. Update `EarningsCallAgenticRag/agents/prompts/prompts.py`:
   - Comparative Agent System Message
   - Historical Earnings Agent System Message

2. Update `agentic_rag_bridge.py`:
   - Add new hard veto detection logic
   - Update soft veto weights
   - Add hidden guidance cut detection
   - Implement integration rules

3. Test on small sample (5-10 earnings calls)

4. Execute full backtest with all Rounds 6-10 changes

---

## Estimated Impact

**Round 7 Contribution**:
- Better risk filtering (fewer false D7/D6 signals)
- More accurate relative performance assessment
- Improved guidance credibility evaluation

**Combined with Round 6**:
- CAGR: 20.05% → **28-32%** (target)
- Sharpe: 1.53 → **1.7-1.9** (target)
- Win Rate: Maintain 70-75%
- D7/D6 Ratio: 45.8% → **>55%**

---

**Note**: All implementation deferred to maintain fast iteration pace. Continuing to Round 8 immediately.
