# Round 8 Implementation Plan (Deferred to Final Backtest)

**Status**: Documented, implementation deferred
**Reason**: Fast iteration mode - accumulate all changes, implement once

---

## Changes to Implement

### 1. Tier Gate Logic (agentic_rag_bridge.py)

#### D4 Tier - Add EPS Surprise Requirement
```python
# BEFORE
if direction >= 4:
    if earnings_day_return >= 0.03 and pre_earnings_5d_return >= 0.05:
        return True, "D4_ENTRY", 0.30

# AFTER
if direction >= 4:
    if (earnings_day_return >= 0.03 and
        pre_earnings_5d_return >= 0.05 and
        eps_surprise >= 0.08):  # NEW: 8% earnings surprise required
        return True, "D4_ENTRY", 0.30
```

#### D7 Tier - Add EPS Surprise Requirement + Soft Veto Relaxation
```python
# BEFORE
if direction >= 7 and len(soft_vetoes) <= 1:
    return True, "D7_CORE", 1.0

# AFTER
if direction >= 7:
    # Standard gate: D7 with <=1 soft veto and eps_surprise > 10%
    if len(soft_vetoes) <= 1 and eps_surprise > 0.10:
        return True, "D7_CORE", 1.0

    # Relaxed gate: D7 with <=2 soft vetoes if exceptional surprise
    if len(soft_vetoes) <= 2 and eps_surprise > 0.15:
        return True, "D7_CORE", 1.0
```

#### D6 Tier - Add EPS Surprise Requirement
```python
# BEFORE
if direction == 6 and len(soft_vetoes) <= 1:
    return True, "D6_STRICT", 0.75

# AFTER
if direction == 6:
    if len(soft_vetoes) <= 1 and eps_surprise > 0.05:  # NEW: 5% surprise required
        return True, "D6_STRICT", 0.75
```

#### D8 MEGA Tier (NEW)
```python
# NEW TIER: Exceptional earnings surprises
if direction >= 7 and eps_surprise > 0.20:  # 20% earnings beat
    return True, "D8_MEGA", 1.2  # Higher confidence multiplier
```

**Note**: D8_MEGA should be checked BEFORE D7 to catch exceptional cases first

#### Complete Updated Tier Logic Order
```python
def _compute_trade_long(
    direction: int,
    confidence: int,
    hard_vetoes: List[str],
    soft_vetoes: List[str],
    sector: str,
    eps_surprise: float,  # NEW PARAMETER
    earnings_day_return: float,
    pre_earnings_5d_return: float,
) -> Tuple[bool, Optional[str], float]:
    """
    Compute trade long signal with enhanced EPS surprise integration.

    Updated: 2026-01-19 (Round 8)
    """

    # Hard veto blocks all trades
    if hard_vetoes:
        return False, None, 0.0

    # NEW TIER 0: D8_MEGA (Exceptional surprises - check first)
    if direction >= 7 and eps_surprise > 0.20:
        # Allow even in blocked sectors for exceptional surprises
        return True, "D8_MEGA", 1.2

    # TIER 1: D7_CORE (Highest conviction)
    if direction >= 7:
        # Standard gate
        if len(soft_vetoes) <= 1 and eps_surprise > 0.10:
            # Check sector blocks (can be overridden by strong surprise)
            if sector in D7_BLOCKED_SECTORS and eps_surprise <= 0.15:
                return False, None, 0.0
            return True, "D7_CORE", 1.0

        # Relaxed gate for strong surprises
        if len(soft_vetoes) <= 2 and eps_surprise > 0.15:
            return True, "D7_CORE", 1.0

    # TIER 2: D6_STRICT
    if direction == 6:
        if len(soft_vetoes) <= 1 and eps_surprise > 0.05:
            # Check sector blocks (can be overridden by strong surprise)
            if sector in D6_BLOCKED_SECTORS and eps_surprise <= 0.15:
                return False, None, 0.0
            return True, "D6_STRICT", 0.75

    # TIER 3: D5_GATED (Momentum required)
    if direction >= 5:
        if earnings_day_return >= 0.02 or pre_earnings_5d_return >= 0.03:
            return True, "D5_GATED", 0.50

    # TIER 4: D4_ENTRY (Confirmation + EPS surprise required)
    if direction >= 4:
        if (earnings_day_return >= 0.03 and
            pre_earnings_5d_return >= 0.05 and
            eps_surprise >= 0.08):
            return True, "D4_ENTRY", 0.30

    # No tier matched
    return False, None, 0.0
```

---

### 2. Industry Block Conditional Removal (agentic_rag_bridge.py)

```python
# Updated sector block logic (integrated above)
# Strong surprise (>15%) overrides sector blocks

D6_BLOCKED_SECTORS = ["Technology", "Healthcare"]  # Keep definitions
D7_BLOCKED_SECTORS = ["Real Estate"]

# But apply conditionally:
if sector in D6_BLOCKED_SECTORS and eps_surprise <= 0.15:
    return False, None, 0.0  # Block only if surprise not strong

if sector in D7_BLOCKED_SECTORS and eps_surprise <= 0.15:
    return False, None, 0.0  # Block only if surprise not strong
```

---

### 3. Position Sizing Enhancement (v10_scoring.py)

#### Update compute_v10_position_size Function

```python
def compute_v10_position_size(
    tier: str,
    direction_score: int,
    confidence: int,
    reliability_score: float,
    evidence_score: float,
    contradiction_score: float,
    n_soft_vetoes: int,
    reaction_term: float = 0.0,
    eps_surprise: float = 0.0,  # NEW PARAMETER
    earnings_day_return: float = 0.0,  # NEW PARAMETER
) -> float:
    """
    Compute position size with enhanced market reaction integration.

    Updated: 2026-01-19 (Round 8)
    """

    # Tier-specific base sizes
    if tier == "D8_MEGA":
        kelly_multiplier = 1.2  # NEW TIER
    elif tier == "D7_CORE":
        kelly_multiplier = 1.0
    elif tier == "D6_STRICT":
        kelly_multiplier = 0.75
    elif tier == "D5_GATED":
        kelly_multiplier = 0.50
    elif tier == "D4_ENTRY":
        kelly_multiplier = 0.30
    else:
        kelly_multiplier = 0.1  # Fallback

    # Enhanced reaction term (Option C - Combined approach)
    if eps_surprise != 0.0 or earnings_day_return != 0.0:
        reaction_term = (earnings_day_return / 0.10) + (eps_surprise * 0.5)
        reaction_term = max(0, reaction_term)  # Ensure non-negative

    # Utility score (same as before)
    utility = (
        0.3 * reliability_score +
        0.2 * evidence_score +
        0.1 * (10 - contradiction_score) / 10 +
        0.1 * reaction_term  # Now properly populated
    )

    # Soft veto penalty
    soft_veto_penalty = 0.90 ** n_soft_vetoes

    # Base position size
    position_size = utility * kelly_multiplier * soft_veto_penalty * POSITION_SCALE

    # NEW: EPS surprise boost (for significant surprises)
    if eps_surprise > 0.10:
        eps_boost = 1.0 + max(0, eps_surprise * 2)  # 10% surprise = 1.2x
        position_size *= eps_boost

    # Cap at max position size
    position_size = min(position_size, MAX_POSITION_SIZE)

    return position_size

# Constants
POSITION_SCALE = 5.5  # Unchanged
MAX_POSITION_SIZE = 0.55  # 55% max position (new safety cap)
```

---

### 4. Data Flow Updates (agentic_rag_bridge.py)

#### Ensure eps_surprise Passed to Functions

```python
# In agentic_rag_earnings_analysis() or main analysis function

# Extract market anchors
market_anchors = get_market_anchors(symbol, year, quarter, transcript_date)
eps_surprise = market_anchors.get("eps_surprise", 0.0)
earnings_day_return = market_anchors.get("earnings_day_return", 0.0)
pre_earnings_5d_return = market_anchors.get("pre_earnings_5d_return", 0.0)

# Pass to tier logic
trade_long, tier, kelly_mult = _compute_trade_long(
    direction=direction_score,
    confidence=confidence_score,
    hard_vetoes=hard_vetoes,
    soft_vetoes=soft_vetoes,
    sector=company_sector,
    eps_surprise=eps_surprise,  # NEW
    earnings_day_return=earnings_day_return,
    pre_earnings_5d_return=pre_earnings_5d_return,
)

# Pass to position sizing
if trade_long:
    position_size = compute_v10_position_size(
        tier=tier,
        direction_score=direction_score,
        confidence=confidence_score,
        reliability_score=reliability_score,
        evidence_score=evidence_score,
        contradiction_score=contradiction_score,
        n_soft_vetoes=len(soft_vetoes),
        reaction_term=0.0,  # Will be computed inside function now
        eps_surprise=eps_surprise,  # NEW
        earnings_day_return=earnings_day_return,  # NEW
    )
```

---

### 5. Data Validation (NEW)

#### Add EPS Surprise Data Quality Checks

```python
def validate_market_anchors(market_anchors: Dict[str, float]) -> Dict[str, float]:
    """
    Validate and sanitize market anchor data.

    Added: 2026-01-19 (Round 8)
    """
    validated = {}

    # EPS surprise validation
    eps_surprise = market_anchors.get("eps_surprise")
    if eps_surprise is None or not isinstance(eps_surprise, (int, float)):
        logger.warning("Invalid eps_surprise, defaulting to 0.0")
        validated["eps_surprise"] = 0.0
    elif abs(eps_surprise) > 2.0:  # Sanity check: >200% surprise unlikely
        logger.warning(f"Extreme eps_surprise {eps_surprise}, capping at ±2.0")
        validated["eps_surprise"] = max(-2.0, min(2.0, eps_surprise))
    else:
        validated["eps_surprise"] = eps_surprise

    # Other anchors
    validated["earnings_day_return"] = market_anchors.get("earnings_day_return", 0.0)
    validated["pre_earnings_5d_return"] = market_anchors.get("pre_earnings_5d_return", 0.0)

    return validated
```

---

## Implementation Schedule

### During Final Backtest Preparation

1. **Update `agentic_rag_bridge.py`**:
   - Add `eps_surprise` parameter to `_compute_trade_long()`
   - Implement D8_MEGA tier logic
   - Update D7/D6/D4 gates with eps_surprise requirements
   - Add conditional industry block removal
   - Add data validation function

2. **Update `v10_scoring.py`**:
   - Add `eps_surprise` and `earnings_day_return` parameters
   - Implement combined reaction_term calculation (Option C)
   - Add eps_surprise boost logic
   - Add D8_MEGA tier support

3. **Update data flow**:
   - Ensure eps_surprise passed to all relevant functions
   - Add validation before usage

4. **Test on small sample** (5-10 earnings calls):
   - Verify eps_surprise data available
   - Check tier logic produces expected distribution
   - Validate position sizing calculations

5. **Execute full backtest** with all Rounds 6-10 changes

---

## Estimated Impact

**Round 8 Contribution**:
- D4 ratio reduction (47.7% → <20%)
- D7/D6 ratio increase (45.8% → >60%)
- Better capital allocation via market reaction
- Capture exceptional opportunities (D8_MEGA)

**Cumulative with Rounds 6-7**:
- CAGR: 20.05% → **32-36%** (target)
- Sharpe: 1.53 → **1.8-2.1** (target)
- Win Rate: Maintain 70-75%
- Total Trades: 328 → 200-250 (higher quality)
- D7/D6 Ratio: 45.8% → **>60%**

---

## Testing Checklist

When implementing, verify:

- [ ] `eps_surprise` data available from PostgreSQL
- [ ] `eps_surprise` passed to `_compute_trade_long()`
- [ ] D8_MEGA tier triggers for `eps_surprise > 0.20`
- [ ] D7 requires `eps_surprise > 0.10`
- [ ] D6 requires `eps_surprise > 0.05`
- [ ] D4 requires `eps_surprise >= 0.08`
- [ ] D7 soft veto relaxation works with `eps_surprise > 0.15`
- [ ] Industry blocks overridden when `eps_surprise > 0.15`
- [ ] Position sizing boost applied for `eps_surprise > 0.10`
- [ ] Combined reaction_term calculation working
- [ ] Data validation catches invalid eps_surprise values
- [ ] No lookahead violations (eps_surprise must be available at transcript_date)

---

## Risk Mitigation

1. **Data Availability**: Add fallback to `eps_surprise = 0.0` if missing
2. **Extreme Values**: Cap eps_surprise at ±200% (validation function)
3. **D8_MEGA Rarity**: Monitor frequency; adjust threshold if needed
4. **Fewer Trades**: Acceptable if quality improves significantly
5. **Sector Block Removal**: Only with strong surprise (>15%), maintains safety

---

**Note**: All implementation deferred to maintain fast iteration pace. Continuing to Round 9 immediately.
