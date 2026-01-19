# Round 9 Implementation Plan (Deferred to Final Backtest)

**狀態**: 已記錄，實施延遲
**原因**: 快速迭代模式 - 累積所有變更，一次實施

---

## 需實施的變更

### 1. 交叉驗證機制 (orchestrator_parallel_facts.py)

#### Sanity Check - 衝突檢測

```python
def sanity_check(agent_results: Dict[str, Dict]) -> int:
    """
    檢測代理輸出間的矛盾並返回懲罰值。

    Added: 2026-01-19 (Round 9)

    Returns:
        Direction Score penalty (negative integer)
    """
    penalties = []

    comparative = agent_results.get("comparative", {})
    historical_earnings = agent_results.get("historical_earnings", {})
    historical_performance = agent_results.get("historical_performance", {})

    # Conflict Type A: Strong Comparative vs Weak Historical
    comp_score = comparative.get("impact_score", 5)
    hist_score = historical_earnings.get("impact_score", 0)

    if comp_score > 7 and hist_score < -1:
        logger.warning(
            f"Conflict detected: Strong comparative ({comp_score}) "
            f"vs weak historical ({hist_score})"
        )
        penalties.append(-2)

    # Conflict Type B: Positive vs Declining
    if comparative.get("relative_surprise") == "positive":
        if historical_earnings.get("credibility_trend") == "declining":
            logger.warning(
                "Conflict: Positive surprise but declining credibility"
            )
            penalties.append(-1)

    # Conflict Type C: Performance contradiction
    if hist_score > 1:  # Strong historical earnings
        perf_pattern = historical_performance.get("historical_pattern", "")
        if "weak" in perf_pattern or "declining" in perf_pattern:
            logger.warning(
                "Conflict: Strong earnings history but weak performance pattern"
            )
            penalties.append(-1)

    return sum(penalties)
```

#### 順序代理審查（可選）

```python
def run_agents_with_context(
    facts: List[Fact],
    market_anchors: Dict
) -> Dict[str, Dict]:
    """
    依序執行代理，後續代理可參考先前結果。

    Added: 2026-01-19 (Round 9) - OPTIONAL ENHANCEMENT
    """
    # Stage 1: Comparative Agent
    comparative_result = ComparativeAgent.run(facts, market_anchors)

    # Stage 2: Historical Earnings with Comparative context
    historical_context = {
        "comparative_impact": comparative_result["impact_score"],
        "relative_surprise": comparative_result.get("relative_surprise")
    }

    historical_result = HistoricalEarningsAgent.run(
        facts,
        market_anchors,
        context=historical_context  # NEW: Pass context
    )

    # Stage 3: Historical Performance
    performance_result = HistoricalPerformanceAgent.run(
        facts,
        market_anchors
    )

    return {
        "comparative": comparative_result,
        "historical_earnings": historical_result,
        "historical_performance": performance_result
    }
```

---

### 2. 事實委派優化 (orchestrator_parallel_facts.py)

#### 智能事實路由

```python
# Fact routing configuration
FACT_ROUTING = {
    "Surprise": ["comparative", "historical_earnings"],
    "Guidance": ["comparative", "historical_earnings"],
    "Tone": ["historical_earnings"],
    "Market Reaction": ["comparative", "historical_performance"],
    "Warning Sign": ["historical_earnings", "comparative"],
    "Risk Disclosure": ["comparative"],
    "Performance": ["historical_performance"]
}

def route_facts_intelligently(facts: List[Fact]) -> Dict[str, List[Fact]]:
    """
    根據事實類型智能路由到相應代理。

    Updated: 2026-01-19 (Round 9)
    """
    delegation = {
        "comparative": [],
        "historical_earnings": [],
        "historical_performance": []
    }

    for fact in facts:
        category = fact.category

        # Direct category match
        if category in FACT_ROUTING:
            target_agents = FACT_ROUTING[category]
            for agent in target_agents:
                delegation[agent].append(fact)
        else:
            # Fuzzy match (fallback)
            matched = False
            for key in FACT_ROUTING:
                if key.lower() in category.lower():
                    target_agents = FACT_ROUTING[key]
                    for agent in target_agents:
                        delegation[agent].append(fact)
                    matched = True
                    break

            if not matched:
                # Send to all agents as fallback
                logger.warning(
                    f"Unknown fact category: {category}, "
                    f"sending to all agents"
                )
                for agent in delegation.keys():
                    delegation[agent].append(fact)

    return delegation
```

#### 事實優先級

```python
# Priority definitions
HIGH_PRIORITY_FACTS = [
    "GuidanceCut",
    "SevereMarginCompression",
    "RegulatoryRisk",
    "ExecutiveTurnover",
    "Surprise"
]

MEDIUM_PRIORITY_FACTS = [
    "Guidance",
    "Tone",
    "Market Reaction",
    "Warning Sign"
]

LOW_PRIORITY_FACTS = [
    "MinorInventoryChange",
    "RoutineCompliance"
]

def prioritize_facts(facts: List[Fact]) -> List[Fact]:
    """
    為事實分配優先級權重。

    Added: 2026-01-19 (Round 9)
    """
    for fact in facts:
        if fact.category in HIGH_PRIORITY_FACTS:
            fact.priority = 1.0
        elif fact.category in MEDIUM_PRIORITY_FACTS:
            fact.priority = 0.6
        elif fact.category in LOW_PRIORITY_FACTS:
            fact.priority = 0.3
        else:
            fact.priority = 0.5  # Default

    # Sort by priority (highest first)
    return sorted(facts, key=lambda x: x.priority, reverse=True)
```

#### 事實去重

```python
def deduplicate_facts(facts: List[Fact]) -> List[Fact]:
    """
    移除重複或高度相似的事實。

    Added: 2026-01-19 (Round 9)
    """
    from difflib import SequenceMatcher

    def similar(a: str, b: str) -> float:
        """計算字符串相似度"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    seen_facts = {}
    unique_facts = []

    for fact in facts:
        fact_key = fact.content.lower().strip()

        # Check for duplicates
        is_duplicate = False
        for existing_key in seen_facts:
            if similar(fact_key, existing_key) > 0.85:  # 85% similarity threshold
                is_duplicate = True
                logger.debug(
                    f"Duplicate fact removed: {fact.content[:50]}... "
                    f"(similar to: {seen_facts[existing_key].content[:50]}...)"
                )
                break

        if not is_duplicate:
            seen_facts[fact_key] = fact
            unique_facts.append(fact)

    logger.info(f"Deduplication: {len(facts)} → {len(unique_facts)} facts")
    return unique_facts
```

---

### 3. 代理輸出標準化 (orchestrator_parallel_facts.py)

#### 標準化函數

```python
def normalize_impact_score(
    score: float,
    scale_range: Tuple[float, float],
    target_range: Tuple[float, float] = (0, 10)
) -> float:
    """
    將不同量表的分數標準化到統一量表。

    Added: 2026-01-19 (Round 9)

    Args:
        score: 原始分數
        scale_range: 原始量表範圍 (min, max)
        target_range: 目標量表範圍 (default: 0-10)

    Returns:
        標準化後的分數
    """
    min_score, max_score = scale_range
    target_min, target_max = target_range

    # Handle edge case
    if max_score == min_score:
        return target_min

    # Normalize to 0-1
    normalized = (score - min_score) / (max_score - min_score)

    # Scale to target range
    scaled = target_min + normalized * (target_max - target_min)

    # Clamp to target range
    scaled = max(target_min, min(target_max, scaled))

    return scaled
```

#### 標準化代理輸出

```python
def standardize_agent_outputs(agent_results: Dict) -> Dict:
    """
    標準化所有代理輸出到相同量表 (0-10)。

    Added: 2026-01-19 (Round 9)
    """
    standardized = {}

    # Comparative Agent: Already 0-10
    if "comparative" in agent_results:
        standardized["comparative"] = {
            **agent_results["comparative"],
            "impact_score": agent_results["comparative"]["impact_score"]
        }

    # Historical Earnings Agent: -2 to +2 → 0 to 10
    if "historical_earnings" in agent_results:
        original_score = agent_results["historical_earnings"]["impact_score"]
        normalized_score = normalize_impact_score(original_score, (-2, 2))
        standardized["historical_earnings"] = {
            **agent_results["historical_earnings"],
            "impact_score": normalized_score,
            "original_impact_score": original_score  # Keep for debugging
        }

    # Historical Performance Agent: Convert to numeric if needed
    if "historical_performance" in agent_results:
        perf_result = agent_results["historical_performance"]

        # If no numeric score, derive from pattern + confidence
        if "impact_score" not in perf_result:
            pattern = perf_result.get("historical_pattern", "neutral")
            confidence = perf_result.get("confidence", "medium")

            # Map pattern to score
            pattern_scores = {
                "strong_post_earnings": 8,
                "moderate_post_earnings": 6,
                "neutral": 5,
                "weak_post_earnings": 3,
                "declining": 2
            }

            confidence_multipliers = {
                "high": 1.0,
                "medium": 0.8,
                "low": 0.6
            }

            base_score = pattern_scores.get(pattern, 5)
            multiplier = confidence_multipliers.get(confidence, 0.8)
            derived_score = base_score * multiplier

        else:
            derived_score = perf_result["impact_score"]

        standardized["historical_performance"] = {
            **perf_result,
            "impact_score": derived_score
        }

    return standardized
```

---

### 4. 組合代理分數 (orchestrator_parallel_facts.py)

#### 加權平均組合

```python
def combine_agent_scores(
    agent_results: Dict,
    weights: Optional[Dict[str, float]] = None,
    use_confidence: bool = True
) -> float:
    """
    組合代理分數，使用加權平均或信心加權。

    Updated: 2026-01-19 (Round 9)

    Args:
        agent_results: 標準化後的代理輸出
        weights: 可選的手動權重
        use_confidence: 是否使用信心分數進行加權

    Returns:
        Combined direction score (0-10)
    """
    if weights is None:
        # Default weights
        weights = {
            "comparative": 0.4,
            "historical_earnings": 0.4,
            "historical_performance": 0.2
        }

    if use_confidence:
        # Confidence-weighted combination
        total_confidence = sum(
            agent_results[agent].get("confidence", 0.5)
            for agent in agent_results
            if agent in weights
        )

        if total_confidence > 0:
            weighted_score = sum(
                agent_results[agent]["impact_score"] *
                agent_results[agent].get("confidence", 0.5)
                for agent in agent_results
                if agent in weights
            )
            direction_score = weighted_score / total_confidence
        else:
            # Fallback to manual weights
            direction_score = sum(
                agent_results[agent]["impact_score"] * weights[agent]
                for agent in agent_results
                if agent in weights
            )
    else:
        # Manual weighted average
        direction_score = sum(
            agent_results[agent]["impact_score"] * weights[agent]
            for agent in agent_results
            if agent in weights
        )

    return direction_score
```

---

### 5. 完整整合函數 (orchestrator_parallel_facts.py)

#### 主要 orchestrator 更新

```python
def orchestrate_earnings_analysis_v2(
    transcript: str,
    symbol: str,
    year: int,
    quarter: int,
    market_anchors: Dict
) -> Dict:
    """
    Round 9 enhanced orchestration with cross-validation.

    Updated: 2026-01-19 (Round 9)
    """
    # Step 1: Extract facts (unchanged)
    facts = MainAgent.extract_facts(transcript)

    # Step 2: Prioritize and deduplicate facts (NEW)
    facts = prioritize_facts(facts)
    facts = deduplicate_facts(facts)

    logger.info(f"Extracted {len(facts)} unique facts")

    # Step 3: Intelligent fact delegation (UPDATED)
    delegation = route_facts_intelligently(facts)

    # Step 4: Run agents in parallel (or with context)
    agent_results = run_agents_parallel(delegation, market_anchors)

    # Step 5: Standardize outputs (NEW)
    agent_results = standardize_agent_outputs(agent_results)

    # Step 6: Sanity check for conflicts (NEW)
    conflict_penalty = sanity_check(agent_results)

    # Step 7: Combine scores (UPDATED)
    base_direction_score = combine_agent_scores(
        agent_results,
        use_confidence=True
    )

    # Step 8: Apply conflict penalty (NEW)
    final_direction_score = base_direction_score + conflict_penalty

    # Clamp to valid range
    final_direction_score = max(0, min(10, final_direction_score))

    logger.info(
        f"Direction Score: {base_direction_score:.1f} "
        f"(conflict penalty: {conflict_penalty}) "
        f"→ {final_direction_score:.1f}"
    )

    return {
        "direction_score": final_direction_score,
        "base_score": base_direction_score,
        "conflict_penalty": conflict_penalty,
        "agent_results": agent_results,
        "facts_count": len(facts)
    }
```

---

### 6. 代理 Prompt 更新（可選）

#### 添加信心分數到 Agent 輸出

**更新 Comparative Agent prompt** (prompts.py):
```python
# Add to comparative agent system message
"""
In your analysis, also include:
- confidence: Your confidence in this analysis (0.0-1.0 scale)
  - 1.0: High confidence (large peer sample, clear pattern)
  - 0.5: Medium confidence (moderate sample, mixed signals)
  - 0.0: Low confidence (small sample, unclear pattern)
"""
```

**更新 Historical Earnings Agent prompt** (prompts.py):
```python
# Add to historical earnings agent system message
"""
In your analysis, also include:
- confidence: Your confidence in this assessment (0.0-1.0 scale)
  - 1.0: High confidence (4+ quarters of consistent history)
  - 0.5: Medium confidence (2-3 quarters of history)
  - 0.0: Low confidence (1 quarter or inconsistent data)
"""
```

---

## 實施排程

### 最終回測準備期間

1. **更新 `orchestrator_parallel_facts.py`**:
   - 添加 `sanity_check()` 函數
   - 添加 `prioritize_facts()` 函數
   - 添加 `deduplicate_facts()` 函數
   - 更新 `route_facts_intelligently()`
   - 添加 `standardize_agent_outputs()`
   - 更新 `combine_agent_scores()`
   - 整合到主 orchestrator 函數

2. **更新代理 prompts** (可選):
   - 添加信心分數輸出要求
   - 更新輸出格式說明

3. **添加配置**:
   - `FACT_ROUTING` mapping
   - 優先級定義（HIGH/MEDIUM/LOW_PRIORITY_FACTS）

4. **在小樣本上測試** (5-10 個財報):
   - 驗證事實去重運作正常
   - 檢查衝突檢測觸發情況
   - 確認分數標準化正確

5. **執行完整回測**，包含所有 Rounds 6-10 變更

---

## 預期影響

**Round 9 貢獻**:
- 假陽性減少 15-20%
- Direction Score 準確性提升
- 更好的事實利用
- 更可靠的代理輸出

**與 Rounds 6-8 累計**:
- CAGR: 20.05% → **34-38%** (目標)
- Sharpe: 1.53 → **1.9-2.2** (目標)
- Win Rate: 維持 72-76%
- D7/D6 Ratio: 45.8% → **>65%**
- Total Trades: 328 → 200-250 (更高品質)

---

## 測試清單

實施時需驗證:

- [ ] 事實去重運作（不誤刪不同事實）
- [ ] 智能路由正確委派事實
- [ ] 事實優先級正確分配
- [ ] 代理輸出標準化到 0-10 量表
- [ ] Sanity check 正確檢測衝突
- [ ] 衝突懲罰合理應用
- [ ] 加權平均計算正確
- [ ] 信心分數正確使用（如實施）
- [ ] 最終 Direction Score 在 0-10 範圍內
- [ ] 記錄所有衝突和懲罰（用於除錯）

---

## 風險緩解

1. **複雜度**: 添加詳細記錄和除錯輸出
2. **過度懲罰**: 從保守懲罰開始（-1 to -2）
3. **信心不準確**: 使用保守預設值（0.5）
4. **去重過度**: 使用高相似度閾值（85%）
5. **路由錯誤**: 保留 fallback 邏輯（發送到所有代理）

---

**注意**: 所有實施延遲以維持快速迭代節奏。立即繼續 Round 10。
