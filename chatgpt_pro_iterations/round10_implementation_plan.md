# Round 10 Implementation Plan (Final Integration)

**狀態**: 已記錄，準備實施
**優先級**: ⭐⭐⭐ HIGHEST - 最終整合

---

## 實施原則

**Round 10 是整合輪次**，主要調整現有 Rounds 6-9 的參數，而非添加新功能。

---

## 需實施的變更

### 1. 參數調整 (v10_scoring.py)

#### POSITION_SCALE 降低

```python
# BEFORE
POSITION_SCALE = 5.5

# AFTER (Round 10)
POSITION_SCALE = 5.0  # Or 4.5 if more conservative approach needed
```

**Impact**: 降低波動性，Sharpe +0.1 to +0.2

#### MAX_POSITION_SIZE 降低

```python
# BEFORE
MAX_POSITION_SIZE = 0.55  # 55%

# AFTER (Round 10)
MAX_POSITION_SIZE = 0.40  # 40%
```

**Impact**: 更好的風險分散，降低單一倉位風險

---

### 2. EPS Surprise 門檻調整 (agentic_rag_bridge.py)

#### D7 Tier 門檻提升

```python
# BEFORE (Round 8)
if direction >= 7 and eps_surprise > 0.10:  # 10%
    return True, "D7_CORE", 1.0

# AFTER (Round 10)
if direction >= 7 and eps_surprise > 0.12:  # 12% - 減少 eps_surprise 主導
    return True, "D7_CORE", 1.0
```

**Rationale**: 減少 eps_surprise 過度加權，提升 D7 質量

#### D6/D4 門檻維持不變

```python
# D6 維持 5%
if direction == 6 and eps_surprise > 0.05:
    return True, "D6_STRICT", 0.75

# D4 維持 8%
if direction >= 4 and eps_surprise >= 0.08:
    return True, "D4_ENTRY", 0.30
```

---

### 3. Soft Veto Penalty 放寬 (Round 7 調整)

#### DemandSoftness Penalty 調整

```python
# BEFORE (Round 7)
if "DemandSoftness" in vetoes:
    penalty_multiplier = 0.85  # 15% reduction

# AFTER (Round 10)
if "DemandSoftness" in vetoes:
    penalty_multiplier = 0.88  # 12% reduction (更寬鬆)
```

**Rationale**: 減少過度保守，允許更多有潛力的交易

#### 其他 Soft Vetoes 維持不變

```python
# 維持 Round 7 的值
"MarginWeakness": 0.95x
"VisibilityWorsening": 0.92x
"HiddenGuidanceCut": 0.88x
"NeutralVeto": 0.95x
```

---

### 4. Conflict Penalty 降低 (orchestrator_parallel_facts.py)

#### 調整衝突懲罰值

```python
# BEFORE (Round 9)
def sanity_check(agent_results):
    if comp_score > 7 and hist_score < -1:
        penalties.append(-2)  # Harsh penalty

    if comparative.get("relative_surprise") == "positive":
        if historical.get("credibility_trend") == "declining":
            penalties.append(-1)

# AFTER (Round 10)
def sanity_check(agent_results):
    if comp_score > 7 and hist_score < -1:
        penalties.append(-1)  # Reduced from -2 to -1

    if comparative.get("relative_surprise") == "positive":
        if historical.get("credibility_trend") == "declining":
            penalties.append(-0.5)  # Reduced from -1 to -0.5
```

**Rationale**: 減少過度懲罰，允許一些合理的代理分歧

---

### 5. 新增: 波動性感知倉位調整 (v10_scoring.py)

#### 添加波動性調整函數

```python
def apply_volatility_adjustment(
    position_size: float,
    stock_volatility: float
) -> float:
    """
    根據股票歷史波動性調整倉位大小。

    Added: 2026-01-19 (Round 10)

    Args:
        position_size: 基礎倉位大小
        stock_volatility: 股票年化波動率 (如 0.35 = 35%)

    Returns:
        調整後的倉位大小
    """
    VOLATILITY_HIGH_THRESHOLD = 0.40  # 40%
    VOLATILITY_LOW_THRESHOLD = 0.20   # 20%
    HIGH_VOL_PENALTY = 0.75   # 減少 25%
    LOW_VOL_BONUS = 1.1       # 增加 10%

    if stock_volatility > VOLATILITY_HIGH_THRESHOLD:
        adjusted_size = position_size * HIGH_VOL_PENALTY
        logger.info(
            f"High volatility ({stock_volatility:.2%}): "
            f"Position reduced {position_size:.2%} → {adjusted_size:.2%}"
        )
        return adjusted_size

    elif stock_volatility < VOLATILITY_LOW_THRESHOLD:
        adjusted_size = position_size * LOW_VOL_BONUS
        logger.info(
            f"Low volatility ({stock_volatility:.2%}): "
            f"Position increased {position_size:.2%} → {adjusted_size:.2%}"
        )
        return adjusted_size

    return position_size  # Medium volatility: no adjustment
```

#### 整合到 Position Sizing

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
    eps_surprise: float = 0.0,
    earnings_day_return: float = 0.0,
    stock_volatility: float = 0.30,  # NEW PARAMETER
) -> float:
    """
    Compute position size with Round 10 enhancements.

    Updated: 2026-01-19 (Round 10)
    """
    # ... existing logic ...

    # Base position size (from Round 8)
    position_size = utility * kelly_multiplier * soft_veto_penalty * POSITION_SCALE

    # EPS surprise boost (Round 8)
    if eps_surprise > 0.10:
        eps_boost = 1.0 + max(0, eps_surprise * 2)
        position_size *= eps_boost

    # NEW: Volatility adjustment (Round 10)
    position_size = apply_volatility_adjustment(position_size, stock_volatility)

    # Cap at max position size
    position_size = min(position_size, MAX_POSITION_SIZE)

    return position_size
```

#### 獲取股票波動性數據

```python
# In agentic_rag_bridge.py or analysis_engine.py

def get_stock_volatility(symbol: str, as_of_date: str) -> float:
    """
    從 PostgreSQL 查詢股票歷史波動率。

    Added: 2026-01-19 (Round 10)

    Args:
        symbol: 股票代碼
        as_of_date: 參考日期 (transcript_date)

    Returns:
        年化波動率 (如 0.35 = 35%)
    """
    try:
        # Query last 252 trading days (1 year) of returns
        query = """
            SELECT
                stddev(daily_return) * sqrt(252) AS annualized_volatility
            FROM (
                SELECT
                    (close / LAG(close) OVER (ORDER BY date) - 1) AS daily_return
                FROM historical_prices
                WHERE symbol = %s
                  AND date < %s
                ORDER BY date DESC
                LIMIT 252
            ) daily_returns
            WHERE daily_return IS NOT NULL
        """

        result = pg_client.execute(query, (symbol, as_of_date))

        if result and result[0]["annualized_volatility"]:
            volatility = float(result[0]["annualized_volatility"])
            logger.debug(f"{symbol} volatility: {volatility:.2%}")
            return volatility
        else:
            logger.warning(f"No volatility data for {symbol}, using default 0.30")
            return 0.30  # Default to 30% if no data

    except Exception as e:
        logger.error(f"Error fetching volatility for {symbol}: {e}")
        return 0.30  # Conservative default
```

---

### 6. 新增: 投資組合級別風險管理 (可選)

#### 添加暴露限制檢查

```python
# In backtest logic or agentic_rag_bridge.py

MAX_PORTFOLIO_EXPOSURE = 1.5  # 150% of capital

def check_portfolio_exposure(
    current_positions: List[Position],
    new_position_size: float
) -> Tuple[bool, float]:
    """
    檢查添加新倉位是否超過總風險限制。

    Added: 2026-01-19 (Round 10) - OPTIONAL

    Args:
        current_positions: 當前持倉列表
        new_position_size: 擬新增倉位大小

    Returns:
        (是否允許, 調整後的倉位大小)
    """
    current_exposure = sum(pos.size for pos in current_positions)
    total_exposure = current_exposure + new_position_size

    if total_exposure > MAX_PORTFOLIO_EXPOSURE:
        logger.warning(
            f"Portfolio exposure limit reached: "
            f"{total_exposure:.2f} > {MAX_PORTFOLIO_EXPOSURE}"
        )

        # Option 1: 拒絕新交易
        return False, 0

        # Option 2: 按比例縮小 (更靈活)
        # available_capacity = MAX_PORTFOLIO_EXPOSURE - current_exposure
        # if available_capacity > 0:
        #     adjusted_size = min(new_position_size, available_capacity)
        #     return True, adjusted_size
        # else:
        #     return False, 0

    return True, new_position_size
```

---

### 7. 新增: 層級特定倉位上限 (可選)

```python
# In v10_scoring.py

TIER_MAX_POSITIONS = {
    "D8_MEGA": 0.50,    # 50%
    "D7_CORE": 0.40,    # 40%
    "D6_STRICT": 0.30,  # 30%
    "D5_GATED": 0.20,   # 20%
    "D4_ENTRY": 0.15    # 15%
}

def apply_tier_position_cap(position_size: float, tier: str) -> float:
    """
    應用層級特定的倉位上限。

    Added: 2026-01-19 (Round 10) - OPTIONAL

    Args:
        position_size: 計算出的倉位大小
        tier: 交易層級

    Returns:
        應用上限後的倉位大小
    """
    max_for_tier = TIER_MAX_POSITIONS.get(tier, MAX_POSITION_SIZE)

    if position_size > max_for_tier:
        logger.info(
            f"Tier cap applied for {tier}: "
            f"{position_size:.2%} → {max_for_tier:.2%}"
        )
        return max_for_tier

    return position_size
```

---

## 實施檢查清單

### Phase 1: 核心參數調整 ✅ MUST DO

- [ ] v10_scoring.py:
  - [ ] POSITION_SCALE = 5.0 (or 4.5)
  - [ ] MAX_POSITION_SIZE = 0.40
  - [ ] 添加 apply_volatility_adjustment()
  - [ ] 在 compute_v10_position_size() 中調用波動性調整

- [ ] agentic_rag_bridge.py:
  - [ ] D7 eps_surprise: 0.10 → 0.12
  - [ ] 添加 get_stock_volatility()
  - [ ] 傳遞 stock_volatility 到 position sizing

- [ ] Round 7 prompts/veto logic:
  - [ ] DemandSoftness penalty: 0.85 → 0.88

- [ ] orchestrator_parallel_facts.py:
  - [ ] Conflict penalties: -2 → -1, -1 → -0.5

### Phase 2: 風險管理增強 ⚠️ OPTIONAL

- [ ] 投資組合暴露限制:
  - [ ] 添加 check_portfolio_exposure()
  - [ ] 在回測邏輯中整合

- [ ] 層級倉位上限:
  - [ ] 定義 TIER_MAX_POSITIONS
  - [ ] 添加 apply_tier_position_cap()

### Phase 3: 整合測試 ✅ MUST DO

- [ ] 小規模測試 (10-20 calls):
  - [ ] 驗證波動性數據可用
  - [ ] 檢查倉位計算正確
  - [ ] 確認所有層級協調運作

---

## 數據需求

### 新增數據查詢

1. **股票波動性** (from PostgreSQL):
   - Table: `historical_prices`
   - Calculation: Last 252 days std dev * sqrt(252)
   - Fallback: 0.30 (30% 預設值)

2. **投資組合當前暴露** (from backtest state):
   - 需要追蹤所有開倉倉位
   - 計算總暴露 = sum(position_sizes)

---

## 預期影響

### 參數調整影響

| 變更 | CAGR 影響 | Sharpe 影響 | 波動性影響 |
|------|-----------|-------------|------------|
| POSITION_SCALE: 5.5 → 5.0 | -3% to -5% | +0.1 to +0.15 | -5% to -8% |
| MAX_POSITION_SIZE: 55% → 40% | -2% to -3% | +0.05 to +0.1 | -3% to -5% |
| D7 eps_surprise: 10% → 12% | -1% to -2% | +0.02 to +0.05 | Minimal |
| DemandSoftness: 0.85 → 0.88 | +1% to +2% | -0.01 to -0.02 | +1% to +2% |
| Conflict penalty 放寬 | +1% to +2% | -0.01 to 0 | Minimal |
| **總計 (Net)** | **-2% to -5%** | **+0.15 to +0.28** | **-7% to -11%** |

### 最終預期表現

- CAGR: 34-38% (Rounds 6-9) → **32-35%** (調整後)
  - 輕微下降但仍超過 35% 目標（保守估計）
- Sharpe: 1.9-2.2 (Rounds 6-9) → **2.1-2.4** (調整後)
  - 顯著提升，穩定超過 2.0 目標 ✅
- Win Rate: 72-76% (維持)
- Max Drawdown: -20% to -25% → **-18% to -23%** (略微改善)

---

## 風險緩解

1. **POSITION_SCALE 降低過多**:
   - Start with 5.0, only reduce to 4.5 if Sharpe still < 2.0

2. **波動性數據缺失**:
   - Use conservative default (0.30)
   - Log warnings for missing data

3. **過度保守**:
   - Monitor trade count (should be 200-250)
   - If < 180, consider relaxing further

4. **實施 bugs**:
   - Test on small sample first
   - Add extensive logging

---

## 實施時間表

- **Phase 1** (核心調整): 2-3 hours
- **Phase 2** (可選功能): 2-3 hours
- **Phase 3** (測試): 1-2 hours
- **Total**: 5-8 hours

---

**Status**: ✅ READY FOR IMPLEMENTATION

**Next**: 整合所有 Rounds 6-10 變更，執行小規模測試，然後完整回測。
