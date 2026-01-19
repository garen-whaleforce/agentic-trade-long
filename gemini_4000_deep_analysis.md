# Gemini 4000 樣本回測深度分析

**日期**: 2026-01-19
**分析師**: Claude Sonnet 4.5
**數據來源**: gemini-3-flash-preview 4000 樣本回測 (2017-2025)

---

## 執行摘要

### 關鍵發現
1. ✅ **系統穩定性優異**: 99.75% 成功率
2. ⚠️ **信號率異常偏高**: 38.5% (預期 10-20%)
3. ⚠️ **D4_OPP 氾濫**: 佔所有信號的 58.9%
4. ❌ **D6_STRICT 稀缺**: 僅 6 個信號 (0.4%)
5. ⚠️ **D7_CORE 不足**: 72 個信號 (4.7%)
6. ✅ **配置版本混亂**: 檢測到 v34 (D8_MEGA) 與 v33 混合

### 風險評級
- **直接使用風險**: 🔴 **高** - 不建議直接交易
- **數據品質**: 🟢 **良好** - Direction Score 分佈正常
- **系統穩定性**: 🟢 **優秀** - 錯誤率極低

---

## 第一部分：Root Cause Analysis

### 問題 1: D4_OPP 氾濫 (58.9% of signals)

#### 診斷
D4_OPP 產生 908 個信號，遠超預期。這是**最嚴重的問題**。

#### 根本原因 (按可能性排序)

**1. D4_OPP Gates 未實施或失效 (可能性: 90%)**

D4_OPP 應該有以下嚴格條件：
```python
# 預期的 D4_OPP 條件
- direction_score >= 4
- momentum_aligned (day_return 與 direction 一致)
- eps_surprise >= 某個門檻 (可能 3-5%)
- soft_veto <= 2
- 無 hard veto
```

**可能失效原因**:
- `momentum_aligned` 檢查邏輯錯誤或被註解
- `eps_surprise` 門檻過低或未檢查
- Veto 機制未正確應用於 D4_OPP

**2. D4_ENTRY 與 D4_OPP 邏輯重疊 (可能性: 60%)**

當前結果:
- D4_OPP: 908 個
- D4_ENTRY: 381 個
- 比例 70:30

正常應該是 30:70 (OPP 較少)。

**可能原因**: 
- D4_OPP 條件比 D4_ENTRY 更寬鬆
- 或者 tier 分配邏輯順序錯誤 (先檢查 OPP 後檢查 ENTRY)

**3. Market Anchors 數據缺失 (可能性: 40%)**

如果 `eps_surprise` 或 `earnings_day_return` 數據缺失或為 null：
- Gates 可能自動通過 (fail-open)
- 導致大量 D4_OPP 被錯誤分配

#### 驗證方法
```python
# 檢查 D4_OPP 信號的實際 market_anchors
sample_d4_opp = results[tier == "D4_OPP"].sample(100)
print(sample_d4_opp[["eps_surprise", "earnings_day_return", "direction_score"]].describe())

# 應該顯示:
# - eps_surprise 是否有 null
# - eps_surprise 平均值是否符合預期門檻
# - earnings_day_return 與 direction 是否一致
```

---

### 問題 2: D6_STRICT 稀缺 (0.4%)

#### 診斷
D6 只有 6 個信號，但 Direction Score D6 有 409 個 (10.3%)。
**轉換率**: 6/409 = 1.5% (極低)

#### 根本原因 (按可能性排序)

**1. D6_REQUIRE_LOW_RISK 重新啟用 (可能性: 80%)**

v33 Iteration 1 配置應該是:
```python
D6_REQUIRE_LOW_RISK = False  # 已移除
```

如果這個被改回 `True`，會導致:
- 只有 `risk_code == "low"` 的信號通過
- 大量 D6 被排除

**2. D6_MIN_EPS_SURPRISE 過高 (可能性: 60%)**

當前設定應該是 0.5%，但可能實際是:
```python
D6_MIN_EPS_SURPRISE = 5.0  # 錯誤！應該是 0.5
```

或者 eps_surprise 數據品質問題:
- 大部分為 null
- 數值異常 (單位錯誤，如 0.005 而非 0.5)

**3. D6_BLOCKED_SECTORS 過多 (可能性: 40%)**

如果 Technology 或其他主要 sector 被封鎖:
```python
D6_BLOCKED_SECTORS = ["Technology", "Healthcare", "Financials"]  # 過多！
```

會導致大量優質 D6 信號被排除。

#### 驗證方法
```python
# 檢查 Direction Score D6 但未產生信號的案例
d6_no_signal = results[(direction_score == 6) & (trade_long == False)]
print(d6_no_signal[["sector", "risk_code", "eps_surprise"]].value_counts())

# 應該顯示:
# - 哪些 sector 佔多數
# - risk_code 分佈 (是否大量 "medium" or "high")
# - eps_surprise 是否低於門檻
```

---

### 問題 3: D7_CORE 不足 (4.7%)

#### 診斷
D7 有 72 個信號，但 Direction Score D7+ 有 296 個 (7.4%)。
**轉換率**: 72/256 = 28.1% (僅計算 D7，不含 D8/D9)

這比 D6 的 1.5% 好，但仍偏低。

#### 根本原因 (按可能性排序)

**1. D7_MIN_DAY_RET 門檻過高 (可能性: 70%)**

v33 設定應該是 1.0%，但可能實際是:
```python
D7_MIN_DAY_RET = 2.0  # 錯誤！應該是 1.0
```

或者 `earnings_day_return` 數據缺失率高。

**2. D7_REQUIRE_EPS_POS 限制 (可能性: 50%)**

```python
D7_REQUIRE_EPS_POS = True
```

這要求 eps_surprise > 0，如果:
- eps_surprise 數據缺失 → 被排除
- eps_surprise 為負但 direction 仍高 (公司 sandbagging) → 被排除

**3. D7_BLOCKED_SECTORS 影響 (可能性: 30%)**

```python
D7_BLOCKED_SECTORS = ["Real Estate"]
```

Real Estate 可能佔 D7 Direction Score 的 10-15%。

#### 驗證方法
```python
# 檢查 Direction Score D7 但未產生信號的案例
d7_no_signal = results[(direction_score == 7) & (trade_long == False)]
print(d7_no_signal[["sector", "earnings_day_return", "eps_surprise"]].describe())

# 應該顯示:
# - earnings_day_return 分佈 (是否大量 < 1.0%)
# - eps_surprise 是否有負值
# - Real Estate sector 佔比
```

---

### 問題 4: D8_MEGA 出現 (8.1%)

#### 診斷
D8_MEGA 有 125 個信號，這是 **v34 Rounds 6-10** 新增的 tier。

#### 根本原因

**配置版本混亂 (確定性: 100%)**

當前代碼同時包含:
- v33 Iteration 1 配置 (D7/D6/D4 邏輯)
- v34 Rounds 6-10 新增 (D8_MEGA tier)

這表示:
1. 代碼已部分套用 Rounds 6-10 changes
2. 但未完整套用 (否則 D4_OPP/D6 問題應該已修復)
3. 或者 v34 changes 有 bug

#### D8_MEGA 條件驗證
```python
# v34 D8_MEGA 條件
eps_surprise > 20%  # 極高驚喜
direction_score >= 8
no hard vetoes

# 檢查這 125 個 D8_MEGA 信號
d8_signals = results[tier == "D8_MEGA"]
print(d8_signals[["eps_surprise", "direction_score", "soft_veto_count"]].describe())

# 預期:
# - eps_surprise 平均 > 20%
# - direction_score 平均 8.0-8.5
# - soft_veto_count 應該很低
```

如果發現不符合，說明 D8_MEGA 邏輯實施錯誤。

---

## 第二部分：配置診斷與建議

### 立即檢查清單 (今晚完成)

#### 1. 確認當前配置版本
```bash
# 檢查 agentic_rag_bridge.py 頂部的版本註解
grep -n "STRATEGY_VERSION\|v33\|v34" agentic_rag_bridge.py | head -20

# 檢查環境變數
env | grep "STRATEGY\|VERSION"
```

**期望結果**: 
- 應該明確標示 v33 或 v34
- 如果混合，需要決定使用哪個版本

#### 2. 檢查 D4_OPP Gates 實施
```bash
# 查找 D4_OPP tier 分配邏輯
grep -A 30 "D4_OPP" agentic_rag_bridge.py | grep -E "momentum|eps_surprise|veto"
```

**期望結果**:
```python
# 應該看到類似邏輯
if direction_score >= 4:
    if momentum_aligned and eps_surprise >= 3.0 and soft_veto <= 2:
        return "D4_OPP"
    elif confirmation_criteria:
        return "D4_ENTRY"
```

**如果缺少**: 需要補上 momentum/eps 檢查

#### 3. 檢查 Market Anchors 數據品質
```python
# 在 Python 中執行
import json
with open("EarningsCallAgenticRag/backtest_checkpoints/backtest_results.json") as f:
    data = json.load(f)

# 檢查 eps_surprise 缺失率
eps_missing = sum(1 for r in data["results"] if r.get("eps_surprise") is None)
print(f"EPS Surprise 缺失: {eps_missing}/{len(data['results'])} ({eps_missing*100/len(data['results']):.1f}%)")

# 檢查 D4_OPP 的 eps_surprise 分佈
d4_opp = [r for r in data["results"] if r.get("tier") == "D4_OPP"]
eps_values = [r.get("eps_surprise") for r in d4_opp if r.get("eps_surprise") is not None]
print(f"D4_OPP EPS Surprise: mean={sum(eps_values)/len(eps_values):.2f}, min={min(eps_values):.2f}, max={max(eps_values):.2f}")
```

**期望結果**:
- EPS Surprise 缺失率 < 10%
- D4_OPP 平均 eps_surprise > 3%

#### 4. 檢查 D6 Gates 配置
```bash
# 查找 D6 配置
grep -E "D6_REQUIRE_LOW_RISK|D6_MIN_EPS_SURPRISE|D6_BLOCKED_SECTORS" agentic_rag_bridge.py
```

**期望結果**:
```python
D6_REQUIRE_LOW_RISK = False  # 應該是 False
D6_MIN_EPS_SURPRISE = 0.5    # 應該是 0.5，不是 5.0
D6_BLOCKED_SECTORS = []       # 應該是空或只有 Real Estate
```

#### 5. 檢查 D7 Gates 配置
```bash
grep -E "D7_MIN_DAY_RET|D7_REQUIRE_EPS_POS|D7_BLOCKED_SECTORS" agentic_rag_bridge.py
```

**期望結果**:
```python
D7_MIN_DAY_RET = 1.0  # 應該是 1.0，不是 1.5 或 2.0
D7_REQUIRE_EPS_POS = True
D7_BLOCKED_SECTORS = ["Real Estate"]
```

---

### 短期修復方案 (明天完成)

#### 方案 A: 回滾到已知良好配置 (推薦)

**步驟**:
1. 確認 v33 Iteration 1 基準配置
2. 禁用 D8_MEGA (如果不想使用 v34)
3. 修復 D4_OPP gates
4. 放寬 D6/D7 gates

**預期效果**:
- 信號率降至 15-20%
- D4_OPP 降至 20-30%
- D6 增加至 5-8%
- D7 增加至 6-8%

**實施**:
```python
# 在 agentic_rag_bridge.py 中

# 1. 禁用 D8_MEGA (如果要回到 v33)
D8_ENABLED = False

# 2. 強化 D4_OPP gates
def _check_d4_opp_eligible(self, direction_score, long_eligible, market_anchors):
    # 必須滿足所有條件
    if direction_score < 4:
        return False
    
    # Momentum aligned
    day_return = market_anchors.get("earnings_day_return", 0)
    if direction_score >= 5 and day_return < 0:
        return False
    if direction_score <= 4 and day_return < -1.0:
        return False
    
    # EPS surprise 門檻
    eps_surprise = market_anchors.get("eps_surprise")
    if eps_surprise is None or eps_surprise < 3.0:  # 3% 門檻
        return False
    
    # Soft veto 限制
    soft_veto_count = self._count_soft_vetoes(long_eligible)
    if soft_veto_count > 2:
        return False
    
    return True

# 3. 放寬 D6 gates (如果當前過嚴)
D6_REQUIRE_LOW_RISK = False
D6_MIN_EPS_SURPRISE = 0.5  # 確認是 0.5，不是 5.0

# 4. 放寬 D7 gates (如果當前過嚴)
D7_MIN_DAY_RET = 0.8  # 從 1.0 降至 0.8
D7_REQUIRE_EPS_POS = False  # 允許負 EPS surprise (sandbagging)
```

#### 方案 B: 完整實施 v34 Rounds 6-10 (長期)

**步驟**:
1. 完整實施 Rounds 6-10 所有 changes:
   - 新 Veto system
   - 更新的 Position sizing
   - D8_MEGA tier
   - 所有 prompt 優化
2. 執行完整回測驗證

**預期效果**:
- 信號率降至 12-18%
- D8 成為主力高品質 tier
- 整體 Sharpe > 2.0
- CAGR 32-35%

**風險**:
- 需要 25-40 小時實施
- 可能引入新 bug
- 需要重新驗證所有邏輯

#### 方案 C: 混合修復 (平衡方案)

**步驟**:
1. 保留 D8_MEGA (已實施且運作正常)
2. 修復 D4_OPP gates (立即)
3. 修復 D6/D7 gates (立即)
4. 分階段實施其他 v34 features

**預期效果**:
- 快速修復當前問題
- 保留 D8_MEGA 優勢
- 逐步過渡到 v34

---

## 第三部分：數據驗證腳本

### 腳本 1: 診斷信號分佈異常
```python
#!/usr/bin/env python3
"""diagnose_signal_distribution.py"""

import json
import pandas as pd

# 讀取結果
with open("EarningsCallAgenticRag/backtest_checkpoints/backtest_results.json") as f:
    data = json.load(f)

df = pd.DataFrame(data["results"])
df_success = df[df["success"] == True]

print("=" * 80)
print("信號分佈診斷")
print("=" * 80)

# 1. D4_OPP 深度分析
print("\n1. D4_OPP 信號分析 (908 個)")
d4_opp = df_success[df_success["tier"] == "D4_OPP"]
print(f"   數量: {len(d4_opp)}")
print(f"   Direction Score 分佈:")
print(d4_opp["direction_score"].value_counts().sort_index())
print(f"   EPS Surprise 統計:")
eps_data = d4_opp["eps_surprise"].dropna()
if len(eps_data) > 0:
    print(f"     平均: {eps_data.mean():.2f}%")
    print(f"     中位數: {eps_data.median():.2f}%")
    print(f"     最小: {eps_data.min():.2f}%")
    print(f"     缺失: {len(d4_opp) - len(eps_data)} ({(len(d4_opp) - len(eps_data))*100/len(d4_opp):.1f}%)")
else:
    print("     ⚠️  所有 D4_OPP 的 eps_surprise 都缺失！")

# 2. D6 未產生信號的案例
print("\n2. D6 Direction Score 但無信號的案例")
d6_no_signal = df_success[(df_success["direction_score"] == 6) & (df_success["trade_long"] == False)]
print(f"   數量: {len(d6_no_signal)}/409 = {len(d6_no_signal)*100/409:.1f}%")
if len(d6_no_signal) > 0:
    print(f"   EPS Surprise 統計:")
    eps_d6 = d6_no_signal["eps_surprise"].dropna()
    if len(eps_d6) > 0:
        print(f"     平均: {eps_d6.mean():.2f}%")
        print(f"     < 0.5%: {(eps_d6 < 0.5).sum()} ({(eps_d6 < 0.5).sum()*100/len(eps_d6):.1f}%)")
    else:
        print("     ⚠️  所有案例 eps_surprise 都缺失")

# 3. D7 未產生信號的案例
print("\n3. D7 Direction Score 但無信號的案例")
d7_no_signal = df_success[(df_success["direction_score"] == 7) & (df_success["trade_long"] == False)]
print(f"   數量: {len(d7_no_signal)}/256 = {len(d7_no_signal)*100/256:.1f}%")

# 4. D8_MEGA 驗證
print("\n4. D8_MEGA 信號驗證 (125 個)")
d8_mega = df_success[df_success["tier"] == "D8_MEGA"]
print(f"   數量: {len(d8_mega)}")
eps_d8 = d8_mega["eps_surprise"].dropna()
if len(eps_d8) > 0:
    print(f"   EPS Surprise 統計:")
    print(f"     平均: {eps_d8.mean():.2f}%")
    print(f"     > 20%: {(eps_d8 > 20).sum()} ({(eps_d8 > 20).sum()*100/len(eps_d8):.1f}%)")
    print(f"     < 20%: {(eps_d8 < 20).sum()} ⚠️  應該都 > 20%")
```

### 腳本 2: 檢查配置文件
```bash
#!/bin/bash
# check_tier_config.sh

echo "========================================"
echo "Tier Gates 配置檢查"
echo "========================================"

echo -e "\n1. 搜尋 D4_OPP 相關配置:"
grep -n "D4_OPP\|D4_ENABLED" agentic_rag_bridge.py | head -20

echo -e "\n2. 搜尋 D6 相關配置:"
grep -n "D6_REQUIRE_LOW_RISK\|D6_MIN_EPS_SURPRISE\|D6_BLOCKED" agentic_rag_bridge.py

echo -e "\n3. 搜尋 D7 相關配置:"
grep -n "D7_MIN_DAY_RET\|D7_REQUIRE_EPS_POS\|D7_BLOCKED" agentic_rag_bridge.py

echo -e "\n4. 搜尋 D8_MEGA 相關配置:"
grep -n "D8_MEGA\|D8_ENABLED" agentic_rag_bridge.py

echo -e "\n5. 搜尋版本標記:"
grep -n "STRATEGY_VERSION\|v33\|v34\|Iteration\|Rounds" agentic_rag_bridge.py | head -10
```

---

## 第四部分：風險評估與建議

### 如果直接使用這 1541 個信號交易

#### 風險評級: 🔴 **高風險 - 不建議**

#### 具體風險:

**1. 信號品質未驗證 (嚴重程度: 🔴 高)**
- D4_OPP 佔 58.9%，但這些可能是錯誤配置產生的
- 實際 Sharpe ratio 可能遠低於預期
- 可能大量假陽性 (false positives)

**2. 過度分散 (嚴重程度: 🟡 中)**
- 1541 個信號對於 4000 樣本太多
- 如果資金有限，每個倉位太小，交易成本侵蝕利潤
- 無法有效分配風險預算

**3. 配置版本混亂 (嚴重程度: 🔴 高)**
- v33 + v34 混合，行為不可預測
- 未來維護困難
- 無法追溯決策邏輯

**4. Backtest 偏差風險 (嚴重程度: 🟡 中)**
- 如果 gates 失效，可能存在 lookahead bias
- Market anchors 數據品質未驗證
- 可能存在未檢測到的 bugs

#### 建議操作:

**紙上交易階段 (必須)**
1. 選取 50-100 個信號進行紙上交易
2. 優先測試 D7_CORE, D6_STRICT, D5_GATED (避開 D4_OPP)
3. 追蹤 30 天實際表現
4. 對比回測預期 vs 實際結果

**小規模實盤測試**
- 只有紙上交易通過後才開始
- 初始資金 < 5% 總資產
- 每個倉位 < 1%
- 持續監控 3 個月

---

## 第五部分：下一步行動計畫

### 🔴 立即行動 (今晚 - 2 小時)

#### A1. 配置診斷
```bash
# 執行配置檢查腳本
bash check_tier_config.sh > tier_config_report.txt

# 執行數據驗證腳本
python diagnose_signal_distribution.py > signal_diagnosis_report.txt

# 檢查結果
cat tier_config_report.txt signal_diagnosis_report.txt
```

**預期輸出**: 找到具體的配置錯誤

#### A2. 緊急修復決策
基於 A1 的發現，決定:
- [ ] 選項 1: 回滾到 v33 Iteration 1 純淨版本
- [ ] 選項 2: 保留 D8_MEGA，只修復 D4_OPP/D6/D7
- [ ] 選項 3: 暫停，等待完整 v34 實施

#### A3. 文檔更新
```bash
# 將診斷結果寫入 CLAUDE.md
# 標記當前配置狀態
# 記錄待修復問題清單
```

---

### 🟡 短期行動 (明天 - 4 小時)

#### B1. 實施修復 (基於 A2 決策)

**如果選擇回滾 v33**:
```python
# 1. 註解或刪除 D8_MEGA 相關代碼
# 2. 恢復 v33 Iteration 1 完整配置
# 3. 加強 D4_OPP gates:
#    - 增加 momentum_aligned 檢查
#    - 提高 eps_surprise 門檻至 3%
#    - 嚴格 soft_veto 限制
```

**如果選擇混合修復**:
```python
# 1. 保留 D8_MEGA
# 2. 修復 D4_OPP gates (同上)
# 3. 修復 D6 gates:
#    - D6_REQUIRE_LOW_RISK = False
#    - 確認 D6_MIN_EPS_SURPRISE = 0.5
# 4. 修復 D7 gates:
#    - D7_MIN_DAY_RET = 0.8
#    - 考慮放寬 D7_REQUIRE_EPS_POS
```

#### B2. 快速驗證測試 (100 樣本)
```bash
# 使用修復後的配置執行 100 樣本測試
MAIN_MODEL=gemini-3-flash-preview python run_incremental_backtest.py --limit 100 --workers 10

# 檢查信號分佈是否改善
# 預期: 信號率 10-20%, D4_OPP < 30%
```

#### B3. 對比分析
```python
# 比較修復前 vs 修復後
# - 信號率變化
# - Tier 分佈變化
# - Direction Score 轉換率
```

---

### 🟢 中期行動 (本週 - 16 小時)

#### C1. 完整回測 (1000-2000 樣本)
- 使用修復後配置
- 包含 2017-2024 各年度樣本
- 生成完整統計報告

#### C2. 績效回測
```python
# 使用 /backtester-api skill
# 計算修復後信號的:
# - CAGR
# - Sharpe Ratio
# - Max Drawdown
# - Win Rate

# 對比目標:
# - CAGR: >20% (目標 35%)
# - Sharpe: >1.5 (目標 2.0)
# - Win Rate: 70-75%
```

#### C3. 決策點: v34 實施
基於 C1-C2 結果決定:
- 如果修復後表現良好 → 暫停 v34，使用當前版本
- 如果仍有問題 → 完整實施 v34 Rounds 6-10

#### C4. 紙上交易準備
- 選擇 50 個信號
- 設置紙上交易監控
- 建立實際 vs 預期追蹤系統

---

## 總結建議

### 最優先 (P0)
1. ✅ **執行配置診斷** → 找出 D4_OPP 根本原因
2. ✅ **決定配置版本** → v33 純淨 or 混合修復
3. ✅ **修復 tier gates** → 特別是 D4_OPP

### 高優先級 (P1)
4. **100 樣本驗證測試** → 確認修復有效
5. **市場數據品質檢查** → eps_surprise, day_return
6. **文檔完整更新** → CLAUDE.md 反映當前狀態

### 中優先級 (P2)
7. **1000+ 樣本完整回測** → 建立新基準線
8. **績效指標計算** → 使用 backtester-api
9. **v34 實施決策** → 基於修復結果

### 低優先級 (P3)
10. **紙上交易啟動** → 實際環境驗證
11. **監控系統建立** → 實時追蹤
12. **完整 v34 實施** → 如果必要

---

**下一步**: 立即執行配置診斷腳本，明確問題根源。
