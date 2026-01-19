# Round 9 Output - Cross-Validation & Fact Delegation

**日期**: 2026-01-19
**ChatGPT Pro Task ID**: e705
**Chat URL**: https://chatgpt.com/g/g-p-696d81d704a88191a62063db63b3060f-automation/c/696db9ac-3184-8324-a46f-117865249f98
**狀態**: ✅ Complete

---

## 概要

Round 9 專注於優化多代理系統的交叉驗證、事實委派、輸出標準化、衝突解決和信心量化。

**主要建議**:
1. 實施代理輸出矛盾檢測機制（sanity check）
2. 智能事實路由（基於事實類型）
3. 標準化代理輸出量表（統一為 0-10 scale）
4. 衝突解決邏輯（懲罰 + 加權）
5. 信心量化（confidence scores）

**預期影響**:
- 減少 15-20% 假陽性（更好的衝突檢測）
- 提升 Direction Score 準確性
- 更好的事實利用（智能委派）
- CAGR: 20.05% → **34-38%** (累計 Rounds 6-9)
- Sharpe: 1.53 → **1.9-2.2** (累計 Rounds 6-9)

---

## 1. 交叉驗證策略 (Cross-Validation)

### Q1.1 Sanity Check - 矛盾檢測

**建議**: ✅ 實施 sanity check 檢測代理輸出矛盾

**實施方式**:
```python
def sanity_check(agent_results):
    """
    檢測代理之間的矛盾信號。

    Added: 2026-01-19 (Round 9)
    """
    penalties = []

    comparative = agent_results.get("comparative", {})
    historical_earnings = agent_results.get("historical_earnings", {})

    # Conflict Type A: Strong Comparative vs Weak Historical
    if comparative.get("impact_score", 0) > 7:
        if historical_earnings.get("impact_score", 0) < -1:
            logger.warning("Conflict: Strong comparative signal but weak historical credibility")
            penalties.append(-2)  # Direction Score penalty

    # Conflict Type B: Positive vs Negative
    if comparative.get("relative_surprise") == "positive":
        if historical_earnings.get("credibility_trend") == "declining":
            logger.warning("Conflict: Positive surprise but declining credibility")
            penalties.append(-1)

    # Return cumulative penalty
    return sum(penalties) if penalties else 0
```

**使用方式**:
```python
# In orchestrator
sanity_check_penalty = sanity_check(agent_results)
direction_score += sanity_check_penalty  # Apply penalty
```

### Q1.2 Sequential Agent Review - 順序審查

**建議**: ✅ 實施代理間的上下文傳遞

**實施方式**:
```python
# Sequential agent execution with context
def run_agents_with_context(facts):
    """
    依序執行代理，後續代理可參考先前結果。

    Added: 2026-01-19 (Round 9)
    """
    # Stage 1: Comparative Agent (first pass)
    comparative_result = ComparativeAgent.run(facts)

    # Stage 2: Historical Earnings with Comparative context
    historical_result = HistoricalEarningsAgent.run(
        facts,
        context=comparative_result  # Pass Comparative conclusions
    )

    # Cross-reference results
    if (comparative_result["relative_surprise"] == "positive" and
        historical_result["credibility_trend"] == "declining"):
        logger.warning("Comparative signal contradicts Historical Earnings credibility")
        # Flag for conflict resolution

    # Stage 3: Historical Performance
    performance_result = HistoricalPerformanceAgent.run(facts)

    return {
        "comparative": comparative_result,
        "historical_earnings": historical_result,
        "historical_performance": performance_result
    }
```

### Q1.3 Conflict Resolution Strategy - 衝突解決

**推薦策略**: **Option A + Option B Hybrid** (加權平均 + 衝突懲罰)

**實施方式**:
```python
def resolve_agent_conflict(agent_results):
    """
    解決代理衝突，使用加權平均 + 懲罰機制。

    Added: 2026-01-19 (Round 9)
    """
    comparative_score = agent_results["comparative"]["impact_score"]
    historical_score = agent_results["historical_earnings"]["impact_score"]
    performance_score = agent_results["historical_performance"].get("impact_score", 5)

    # Check for significant disagreement
    if abs(comparative_score - historical_score) > 3:
        logger.warning(f"Significant disagreement: Comparative={comparative_score}, Historical={historical_score}")

        # Option A: Average with conflict penalty
        penalty = -1
        direction_score = (comparative_score + historical_score + performance_score) / 3 + penalty

    else:
        # Option B: Weighted average (no conflict)
        direction_score = (
            0.4 * comparative_score +
            0.4 * historical_score +
            0.2 * performance_score
        )

    return direction_score
```

---

## 2. 事實委派優化 (Fact Delegation)

### Q2.1 Intelligent Routing - 智能路由

**當前問題**: 關鍵字匹配不夠精確，可能漏掉或重複委派

**建議**: ✅ 使用明確的事實類型映射

**實施方式**:
```python
# 明確的事實路由規則
FACT_ROUTING = {
    "Surprise": ["comparative", "historical_earnings"],
    "Guidance": ["comparative", "historical_earnings"],
    "Tone": ["historical_earnings"],  # Only historical earnings
    "Market Reaction": ["comparative", "historical_performance"],
    "Warning Sign": ["historical_earnings", "comparative"],
    "Risk Disclosure": ["comparative"]  # Sector comparison
}

def route_facts_intelligently(facts):
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

        # Match exact category
        if category in FACT_ROUTING:
            target_agents = FACT_ROUTING[category]
            for agent in target_agents:
                delegation[agent].append(fact)
        else:
            # Fallback: Send to all agents (with warning)
            logger.warning(f"Unknown fact category: {category}, sending to all agents")
            for agent in delegation.keys():
                delegation[agent].append(fact)

    return delegation
```

### Q2.2 Prioritize Facts - 事實優先級

**建議**: ✅ 根據重要性對事實分級

**實施方式**:
```python
# 事實優先級定義
HIGH_PRIORITY_FACTS = [
    "GuidanceCut",
    "SevereMarginCompression",
    "RegulatoryRisk",
    "ExecutiveTurnover"
]

LOW_PRIORITY_FACTS = [
    "MinorInventoryChange",
    "RoutineCompliance"
]

def prioritize_facts(facts):
    """
    為事實分配優先級權重。

    Added: 2026-01-19 (Round 9)
    """
    for fact in facts:
        if fact.category in HIGH_PRIORITY_FACTS:
            fact.priority = 1.0  # High priority
        elif fact.category in LOW_PRIORITY_FACTS:
            fact.priority = 0.3  # Low priority
        else:
            fact.priority = 0.6  # Neutral priority

    # Sort by priority (optional, for processing order)
    return sorted(facts, key=lambda x: x.priority, reverse=True)
```

**使用方式**:
```python
# Weight agent output by fact priority
def weight_by_fact_priority(agent_result, facts):
    """
    根據事實優先級調整代理輸出權重。
    """
    total_priority = sum(f.priority for f in facts)
    if total_priority == 0:
        return agent_result["impact_score"]

    # Scale impact score by average fact priority
    avg_priority = total_priority / len(facts)
    weighted_score = agent_result["impact_score"] * avg_priority

    return weighted_score
```

### Q2.3 Fact Deduplication - 事實去重

**建議**: ✅ 實施事實去重以避免雙重計算

**實施方式**:
```python
def deduplicate_facts(facts):
    """
    移除重複或高度相似的事實。

    Added: 2026-01-19 (Round 9)
    """
    seen_facts = {}
    unique_facts = []

    for fact in facts:
        # Use normalized content as key
        fact_key = fact.content.lower().strip()

        # Check similarity threshold (optional: use fuzzy matching)
        is_duplicate = False
        for existing_key in seen_facts:
            if similar(fact_key, existing_key) > 0.8:  # 80% similarity
                is_duplicate = True
                break

        if not is_duplicate:
            seen_facts[fact_key] = fact
            unique_facts.append(fact)
        else:
            logger.debug(f"Duplicate fact removed: {fact.content}")

    logger.info(f"Deduplication: {len(facts)} → {len(unique_facts)} facts")
    return unique_facts

def similar(a, b):
    """簡單的字符串相似度計算（可用 difflib.SequenceMatcher）"""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()
```

---

## 3. 代理輸出標準化 (Agent Output Normalization)

### Q3.1 Standardize Impact Score Scale - 統一量表

**當前問題**:
- Comparative Agent: 0-10 scale
- Historical Earnings Agent: -2 to +2 scale
- Historical Performance Agent: No numeric score

**建議**: ✅ 統一為 0-10 scale

**實施方式**:
```python
def normalize_impact_score(score, scale_range, target_range=(0, 10)):
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

    # Normalize to 0-1
    normalized = (score - min_score) / (max_score - min_score)

    # Scale to target range
    scaled = target_min + normalized * (target_max - target_min)

    return scaled

# Usage examples
comparative_score = 7  # Already 0-10
historical_earnings_score = -1  # -2 to +2 scale
historical_performance_score = 0.8  # 0-1 scale (假設)

# Normalize all to 0-10
normalized_comparative = comparative_score  # No change needed
normalized_historical = normalize_impact_score(historical_earnings_score, (-2, 2))  # -1 → 2.5
normalized_performance = normalize_impact_score(historical_performance_score, (0, 1))  # 0.8 → 8.0
```

### Q3.2 Combining Scores - 組合分數

**建議**: ✅ **Option B** (加權平均) 為主要策略

**實施方式**:
```python
def combine_agent_scores(agent_results, weights=None):
    """
    組合代理分數，使用加權平均。

    Added: 2026-01-19 (Round 9)
    """
    if weights is None:
        # Default weights: Comparative and Historical Earnings more important
        weights = {
            "comparative": 0.4,
            "historical_earnings": 0.4,
            "historical_performance": 0.2
        }

    # Normalize scores first
    normalized_scores = {}
    normalized_scores["comparative"] = agent_results["comparative"]["impact_score"]

    # Historical Earnings: -2 to +2 → 0 to 10
    normalized_scores["historical_earnings"] = normalize_impact_score(
        agent_results["historical_earnings"]["impact_score"],
        (-2, 2)
    )

    # Historical Performance: Assume 0-1 → 0-10
    perf_score = agent_results["historical_performance"].get("confidence", 0.5) * 10
    normalized_scores["historical_performance"] = perf_score

    # Weighted average
    direction_score = sum(
        normalized_scores[agent] * weights[agent]
        for agent in normalized_scores
    )

    return direction_score
```

---

## 4. 衝突解決邏輯 (Conflict Resolution)

### 衝突類型與解決方案

#### Conflict Type A: Strong vs Weak
```python
# Comparative: Impact Score 9 (強烈勝出)
# Historical Earnings: Impact Score 2 (弱信用)
# Resolution: 標記衝突，降低 Direction Score 2 分

if comparative_score > 7 and historical_score < 4:
    logger.warning("Conflict Type A: Strong comparative vs weak historical")
    direction_score -= 2
```

#### Conflict Type B: Positive vs Negative
```python
# Comparative: Positive relative surprise
# Historical Performance: Declining post-earnings pattern
# Resolution: 中性信號，Direction Score = 5

if comparative_result["relative_surprise"] == "positive":
    if "declining" in historical_performance_result.get("pattern", ""):
        logger.warning("Conflict Type B: Positive surprise vs declining pattern")
        direction_score = 5  # Force neutral
```

#### Conflict Type C: High vs Low Confidence
```python
# Comparative: High confidence (large peer sample)
# Historical Earnings: Low confidence (only 2 quarters history)
# Resolution: 更重視 Comparative

comparative_conf = comparative_result.get("confidence", 0.5)
historical_conf = historical_result.get("confidence", 0.5)

if comparative_conf > 0.8 and historical_conf < 0.3:
    weights = {"comparative": 0.7, "historical_earnings": 0.2, "historical_performance": 0.1}
```

### 完整衝突解決函數

```python
def resolve_conflicts_comprehensive(agent_results):
    """
    綜合衝突解決策略。

    Added: 2026-01-19 (Round 9)
    """
    penalties = []
    adjusted_weights = {
        "comparative": 0.4,
        "historical_earnings": 0.4,
        "historical_performance": 0.2
    }

    comparative = agent_results["comparative"]
    historical = agent_results["historical_earnings"]
    performance = agent_results["historical_performance"]

    # Type A: Strong vs Weak
    if comparative["impact_score"] > 7 and historical["impact_score"] < 4:
        penalties.append(-2)

    # Type B: Direction conflict
    if (comparative.get("relative_surprise") == "positive" and
        historical.get("credibility_trend") == "declining"):
        penalties.append(-1)

    # Type C: Confidence-based weighting
    comp_conf = comparative.get("confidence", 0.5)
    hist_conf = historical.get("confidence", 0.5)

    if comp_conf > hist_conf + 0.3:  # Significantly more confident
        adjusted_weights["comparative"] = 0.6
        adjusted_weights["historical_earnings"] = 0.25

    # Calculate base direction score
    direction_score = combine_agent_scores(agent_results, adjusted_weights)

    # Apply penalties
    direction_score += sum(penalties)

    # Clamp to valid range
    direction_score = max(0, min(10, direction_score))

    return direction_score, penalties, adjusted_weights
```

---

## 5. 信心量化 (Confidence Quantification)

### Q5.1 Confidence Scores - 信心分數

**建議**: ✅ 代理返回信心分數

**更新代理輸出格式**:
```python
# Example agent output (updated)
{
    "impact_score": 7,
    "confidence": 0.8,  # NEW: 0-1 scale
    "uncertainty_range": [6, 8],  # NEW: Possible range
    "evidence_quality": "high",  # NEW: high/medium/low
    "analysis": "Company outperforms peers by 15%..."
}
```

### Q5.2 Using Confidence - 使用信心分數

**實施方式**:
```python
def confidence_weighted_combination(agent_outputs):
    """
    基於信心的加權組合。

    Added: 2026-01-19 (Round 9)
    """
    total_confidence = sum(
        agent["confidence"]
        for agent in agent_outputs.values()
    )

    if total_confidence == 0:
        # Fallback to equal weighting
        return sum(agent["impact_score"] for agent in agent_outputs.values()) / len(agent_outputs)

    # Confidence-weighted average
    weighted_score = sum(
        agent["impact_score"] * agent["confidence"]
        for agent in agent_outputs.values()
    )

    direction_score = weighted_score / total_confidence

    return direction_score
```

**信心計算示例** (在代理內部):
```python
# In ComparativeAgent
def calculate_confidence(self, peer_data):
    """計算信心分數"""
    confidence = 0.5  # Base confidence

    # Factor 1: Sample size
    if len(peer_data) >= 5:
        confidence += 0.2
    elif len(peer_data) >= 3:
        confidence += 0.1

    # Factor 2: Data quality
    if all(p.get("data_quality") == "high" for p in peer_data):
        confidence += 0.2

    # Factor 3: Consensus
    if self.has_consensus(peer_data):
        confidence += 0.1

    return min(1.0, confidence)
```

---

## 6. 預期績效影響

### 短期影響 (Round 9 單獨)

| 指標 | 改進來源 | 預期改善 |
|------|----------|----------|
| 假陽性率 | 衝突檢測 + 交叉驗證 | -15% to -20% |
| Direction Score 準確性 | 標準化 + 加權 | +5% to +10% |
| 事實利用率 | 智能委派 + 去重 | +10% to +15% |
| 信號可靠性 | 信心量化 | +10% to +15% |

### 中期影響 (累計 Rounds 6-9)

| 指標 | Baseline (Iter 1) | Rounds 6-9 目標 | 改變 |
|------|-------------------|-----------------|------|
| CAGR | 20.05% | **34-38%** | +14-18% |
| Sharpe | 1.53 | **1.9-2.2** | +0.37-0.67 |
| Win Rate | 72.26% | **72-76%** | 持平或提升 |
| D7/D6 Ratio | 45.8% | **>65%** | +19.2% |
| Profit Factor | 2.57 | **3.8-4.5** | +1.23-1.93 |

### 貢獻分解

**Round 9 預期貢獻**:
- CAGR: +2-4%
- Sharpe: +0.1-0.2
- 假陽性減少: 15-20%
- 信號品質提升: 顯著

---

## 7. 實施優先級

### 高優先級（核心改進）
1. ✅ 實施 sanity_check() 衝突檢測
2. ✅ 標準化代理輸出量表（統一為 0-10）
3. ✅ 智能事實路由（FACT_ROUTING mapping）
4. ✅ 加權平均組合（confidence-weighted）

### 中優先級（增強功能）
5. ✅ 事實優先級系統
6. ✅ 事實去重邏輯
7. ✅ 順序代理審查（context passing）

### 低優先級（精細調整）
8. 監控衝突頻率並調整懲罰
9. 根據回測結果微調權重
10. 開發更複雜的信心計算公式

---

## 8. 與前幾輪的整合

### 累計變更 (Rounds 6-9)

**Round 6**: Prompt 優化（Direction Score 校準，強調驚喜）
**Round 7**: Veto 邏輯（新 hard vetoes，可變 soft veto 權重，helper agent 改進）
**Round 8**: Tier gates（eps_surprise 整合，倉位計算增強）
**Round 9**: 交叉驗證（衝突檢測，事實委派，輸出標準化）

### 協同效應

1. **Round 6 + Round 9**: 更好的 prompt → 更準確的事實提取 → 更有效的事實委派
2. **Round 7 + Round 9**: Veto 檢測改進 + 代理衝突檢測 = 全面的風險管理
3. **Round 8 + Round 9**: EPS surprise 整合 + 標準化輸出 = 一致的量化信號
4. **全部輪次**: 從 prompt 到最終決策的完整優化鏈

---

## 9. 風險評估

### 潛在下行風險

1. **複雜度增加**: 更多邏輯層 → 潛在 bugs
   - **緩解**: 徹底測試，記錄所有決策路徑

2. **過度懲罰**: 衝突檢測可能過於嚴格 → 錯失好交易
   - **緩解**: 從保守懲罰開始（-1 to -2），根據回測調整

3. **信心計算不準確**: 新的信心分數可能不可靠
   - **緩解**: 初期使用保守值（0.5 baseline），逐步校準

### 上行機會

1. **假陽性減少**: 更好的衝突檢測 → 更少的失敗交易
2. **信號品質提升**: 標準化輸出 → 更一致的決策
3. **資源效率**: 智能委派 → 降低 LLM API 成本
4. **可解釋性**: 記錄衝突和懲罰 → 更好的錯誤分析

---

## 10. 下一步

1. **建立實施計劃**: 建立 `round9_implementation_plan.md`
2. **繼續到 Round 10**: 最終整合和微調
3. **延遲實施**: 維持快速迭代模式 - 一起實施所有變更（Rounds 6-10）
4. **最終回測**: Round 10 後，實施所有變更並執行全面回測

---

**注意**: 所有實施延遲以維持快速迭代節奏。立即繼續 Round 10。
