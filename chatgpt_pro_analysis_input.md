# Gemini-3-Flash-Preview 4000 樣本回測結果分析請求

## 背景
我們使用 gemini-3-flash-preview 作為 MAIN_MODEL 執行了 4000 筆財報電話會議分析回測（2017-2025），目標是產生做多交易信號。系統使用 7-TIER 架構，每個 tier 有不同的過濾條件和倉位大小。

## 預期行為 (基於 v33 Iteration 1 配置)
- **信號率**: 10-20%
- **D7+ (高品質信號)**: 7-10%
- **主力 tiers**: D7_CORE, D6_STRICT, D4_ENTRY
- **D4_OPP**: 機會性 tier，應該有嚴格的 gates

## 實際結果 (4000 筆)

### 執行統計
- 總樣本: 4000
- 成功: 3990 (99.75%)
- 錯誤: 10 (0.25%)
- 平均速度: 9.03s/筆
- 總時間: 10.01 小時
- 成本: $11.40 ($0.00285/筆)

### Direction Score 分佈
```
D9:   1 筆   (0.0%)
D8:  39 筆   (1.0%)
D7: 256 筆   (6.4%)
D6: 409 筆  (10.3%)
D5: 372 筆   (9.3%)
D4: 2011 筆 (50.4%)
D3: 867 筆  (21.7%)
D2:  35 筆   (0.9%)
```

**品質分層**:
- D7+ (高品質): 296 筆 (7.4%) ✅ 符合預期
- D6+ (優質): 705 筆 (17.7%)
- D5+ (合格): 1077 筆 (27.0%)

### Trade Signal 分析

**總信號: 1541 筆 (38.5%)** ⚠️ **遠高於預期的 10-20%**

按 Tier 分類:
```
D4_OPP:    908 筆 (58.9%)  ⚠️ 最多 - 應該是機會性 tier
D4_ENTRY:  381 筆 (24.7%)  
D8_MEGA:   125 筆 (8.1%)   ✅ 新 tier (Rounds 6-10)
D7_CORE:    72 筆 (4.7%)   ⚠️ 偏少 - 應該是主力
D5_GATED:   49 筆 (3.2%)   
D6_STRICT:   6 筆 (0.4%)   ❌ 過少 - 應該是主力
```

## 關鍵異常

### 1. D4_OPP 氾濫 (58.9% of signals)
- D4_OPP 產生了 908/1541 = 58.9% 的信號
- 在 v33 中，D4_OPP 應該有嚴格的 gates
- 可能原因：gates 未正確實施或配置錯誤

### 2. D6_STRICT 稀少 (0.4%)
- D6 只有 6 個信號，遠低於預期
- D6 應該是主力 tier 之一
- 可能原因：eps_surprise 要求過嚴、low_risk 要求、sector blocks

### 3. D7_CORE 偏少 (4.7%)
- D7 只有 72 個信號
- 以 7.4% 的 D7+ Direction Score 來看，應該有更多 D7 信號
- 可能原因：day_return 或 eps_surprise 門檻過高

### 4. D8_MEGA 出現 (8.1%)
- D8_MEGA 是 Rounds 6-10 (v34) 新增的 tier
- 有 125 個信號
- 表示當前配置可能已部分套用 v34 changes

## 7-TIER 架構配置 (應該的行為)

```python
# From v33 Iteration 1
D7_ENABLED = True
D6_ENABLED = True
D5_ENABLED = True
D4_ENABLED = True
D3_ENABLED = False  # Disabled

# D7 CORE 參數
D7_MIN_DAY_RET = 1.0  # 1.0%
D7_REQUIRE_EPS_POS = True
D7_BLOCKED_SECTORS = ["Real Estate"]

# D6 STRICT 參數
D6_MIN_EPS_SURPRISE = 0.5  # 0.5%
D6_REQUIRE_LOW_RISK = False
D6_EXCLUDE_SECTORS = []  # Removed Technology

# 風險過濾
RISK_DAY_LOW = -5.0  # -5%
RISK_EPS_MISS = 0.0
RISK_RUNUP_HIGH = 15.0
```

## Rounds 6-10 v34 Changes (部分可能已套用)

### D8_MEGA Tier (新增)
```python
# Conditions
eps_surprise > 20%
direction_score >= 8
no hard vetoes
```

### Veto System Updates
- 3 new hard vetoes
- Variable soft veto weights
- Hidden guidance cut detection

### Position Sizing Updates
- POSITION_SCALE: 5.5 → 5.0
- MAX_POSITION_SIZE: 55% → 40%

## 問題

1. **為什麼 D4_OPP 產生了 58.9% 的信號？**
   - 是否 D4_OPP gates 未正確實施？
   - 是否應該加強 D4_OPP 的過濾條件？

2. **為什麼 D6_STRICT 只有 6 個信號？**
   - eps_surprise 數據品質如何？
   - D6 gates 是否過於嚴格？

3. **為什麼 D7_CORE 只有 72 個信號？**
   - day_return 過濾是否過嚴？
   - 應該如何平衡 D7 的品質與數量？

4. **當前配置版本是什麼？**
   - 是 v33 Iteration 1？
   - 還是已部分套用 v34 (因為有 D8_MEGA)？

5. **38.5% 的信號率是否可接受？**
   - 如果這些信號品質高，可能可接受
   - 但需要實際回測績效驗證

## 請求分析

請提供：

1. **Root Cause Analysis**: 為什麼會出現這些異常？最可能的原因是什麼？

2. **配置建議**: 
   - 應該如何調整 tier gates？
   - 是否應該禁用某些 tiers？
   - 參數應該如何調整？

3. **下一步行動計畫**:
   - 立即行動 (今晚)
   - 短期行動 (明天)
   - 中期行動 (本週)

4. **風險評估**: 如果直接使用這 1541 個信號進行交易，有什麼風險？

5. **數據驗證**: 我們應該檢查哪些數據來診斷問題？

請基於你對量化交易策略、回測方法論、以及 LLM-based 信號生成的深度理解，提供詳細分析和可執行的建議。
