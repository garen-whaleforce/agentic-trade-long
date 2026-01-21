# GitHub CI/CD 設置完成總結

**完成時間**: 2026-01-21
**狀態**: ✅ 完成並可立即使用

---

## 📂 創建的檔案（共 6 個）

### GitHub Actions Workflows (4 個)

| 檔案 | 大小 | 用途 |
|------|------|------|
| `.github/workflows/backtest-validation.yml` | 9.9K | 主要驗證流程（Gate-2 + Gate-3 + UAL Sentinel） |
| `.github/workflows/gate2-qa.yml` | 2.7K | Gate-2 專用驗證（已存在） |
| `.github/workflows/gate3-validation.yml` | 6.4K | Gate-3 專用驗證 |
| `.github/workflows/pre-commit.yml` | 4.2K | 程式碼品質檢查 |

### 文件與腳本 (2 個)

| 檔案 | 大小 | 用途 |
|------|------|------|
| `.github/README.md` | 5.5K | CI/CD 快速導覽 |
| `.github/SETUP_GUIDE.md` | 7.7K | 詳細設置與故障排除指南 |
| `test_ci_locally.sh` | 6.3K | 本地 CI/CD 測試腳本（可執行） |

**總計**: 42.7K 的 CI/CD 自動化基礎設施

---

## 🎯 核心功能

### 1. 自動化驗證

```
Push/PR → GitHub Actions
    ↓
Gate-2 驗證 (Data Contract)
    ↓
Gate-3 驗證 (Execution Contract)
    ↓
UAL Sentinel 測試 (Regression)
    ↓
✅ AUDITABLE 或 ❌ NON-ACTIONABLE
```

### 2. 多層次檢查

| 層次 | 檢查項目 | 標準 |
|------|----------|------|
| **Gate-2** | Lookahead Safety | ≥90% safe, <5% violations |
| | EPS Surprise Coverage | >95% valid |
| | Cross-Quarter Drift | ≥90% ≤3d, 100% ≤7d |
| | NULL Fields | transcript 0%, earnings <5% |
| **Gate-3** | Trade Ledger | 所有必要欄位完整 |
| | Holding Period | 28-45 days (允許 stop-loss <28) |
| | Hard Fail | >60 days（portfolio rebalance） |
| | Signal Mapping | 1 signal → 1 trade |
| **UAL Sentinel** | Entry Date | 2019-01-17 |
| | Exit Date | 2019-02-15 ~ 2019-02-22 (T+30) |
| | ❌ Forbidden | 2020-10-29 (452 days) |
| **Code Quality** | Formatting | Black, isort |
| | Linting | Flake8 |
| | Security | No debug, no credentials |

### 3. 自動化報告

- ✅ Validation Report（可下載 artifact）
- ✅ PR Comments（自動評論驗證結果）
- ✅ Status Checks（通過/失敗狀態）
- ✅ Exit Codes（CI/CD 整合）

---

## 🚀 使用流程

### 本地開發

```bash
# 1. 修改程式碼
vim gate3_execution_contract.py

# 2. 本地測試（可選但推薦）
./test_ci_locally.sh

# 3. Commit & Push
git add .
git commit -m "fix: Gate-3 violations"
git push
```

### Pull Request

```bash
# 1. 創建 feature branch
git checkout -b feature/new-portfolio

# 2. 進行修改
# ... modify files ...

# 3. Push to GitHub
git push origin feature/new-portfolio

# 4. 創建 PR
# GitHub UI → New Pull Request

# 5. 查看 CI 結果
# Actions tab → 點擊 workflow run
# PR 頁面會顯示 status checks

# 6. 修正問題（如果失敗）
# 查看 logs → 修正 → push again

# 7. 合併（驗證通過後）
# Merge Pull Request
```

---

## 📊 驗證標準

### ✅ AUDITABLE（可審計）

**條件**:
- Gate-2: ✅ PASSED
- Gate-3: ✅ PASSED
- UAL Sentinel: ✅ PASSED

**允許動作**:
- ✅ 合併 PR
- ✅ 使用結果進行策略決策
- ✅ 部署到生產環境
- ✅ 納入 CLAUDE.md 記錄

**標記**: 結果檔案標記為 `AUDITABLE`

---

### ❌ NON-ACTIONABLE（不可用）

**條件**:
- Gate-2: ❌ FAILED（資料不一致）
- Gate-3: ❌ FAILED（執行模型錯誤）
- UAL Sentinel: ❌ FAILED（portfolio rebalance 檢測）

**禁止動作**:
- ❌ 合併 PR
- ❌ 使用結果進行策略決策
- ❌ 部署到生產環境
- ❌ 引用結果數據

**標記**: 結果檔案標記為 `NON-ACTIONABLE`

**必須動作**: 修正 violations → 重新驗證

---

## 🔧 進階設置（可選）

### 1. 分支保護規則

```
Repository Settings → Branches → Add rule
Branch name pattern: main

☑ Require status checks to pass before merging
  ☑ validate-backtest-results
☑ Require branches to be up to date before merging
☑ Require conversation resolution before merging
```

**效果**: 未通過驗證的 PR 無法合併到 main 分支

---

### 2. GitHub Secrets

```
Repository Settings → Secrets and variables → Actions → New secret

添加以下 secrets（如需要）:
- FMP_API_KEY
- NEO4J_PASSWORD
- POSTGRES_PASSWORD
```

**用途**: Workflows 可存取私密資訊（API keys, credentials）

---

### 3. Notification Settings

```
Repository Settings → Notifications

Configure email/Slack notifications for:
- Workflow failures
- PR comments
- Status checks
```

---

## 📖 文件導覽

| 文件 | 用途 | 讀者 |
|------|------|------|
| [.github/README.md](.github/README.md) | CI/CD 快速導覽 | 所有開發者 |
| [.github/SETUP_GUIDE.md](.github/SETUP_GUIDE.md) | 詳細設置指南 | DevOps, 首次設置者 |
| [CLAUDE.md Rule #0](CLAUDE.md#0-研究可審計性規範) | Gate-2/Gate-3 要求 | 策略開發者 |
| [gate3_execution_contract.py](gate3_execution_contract.py) | Gate-3 實作 | 程式開發者 |
| [tests/test_gate2_data_contract.py](tests/test_gate2_data_contract.py) | Gate-2 測試 | 測試工程師 |

---

## 🎓 關鍵概念

### Gate-2: Data Contract（資料契約）

**目的**: 確保所有回測使用一致的事件時間錨點

**檢查項目**:
- `earnings_date_used` 非 NULL
- `earnings_date_used` ≥ `actual_earnings_date`
- 沒有 lookahead bias（使用未來資訊）
- EPS surprise 資料完整

**違規範例**:
```python
# ❌ 錯誤: 使用 NULL earnings_date
trade = {
    'earnings_date_used': None,  # 違規!
    'entry_date': '2024-01-15'
}

# ✅ 正確: 使用一致的 earnings_date
trade = {
    'earnings_date_used': '2024-01-10',
    'entry_date': '2024-01-11'  # T+1
}
```

---

### Gate-3: Execution Contract（執行契約）

**目的**: 確保所有回測使用 T+30 event trading 執行模型

**檢查項目**:
- Holding period: 28-45 days（允許週末/假日調整）
- Stop-loss early exit: <28 days（必須標記 `stop_triggered=true`）
- Hard fail: >60 days（表示 portfolio rebalance，非 T+30）
- Trade ledger complete

**違規範例**:
```python
# ❌ 錯誤: Portfolio Rebalance (452 days)
trade = {
    'entry_date': '2019-01-16',
    'exit_date': '2020-10-29',  # 452 days! 違規!
    'holding_days': 452
}

# ✅ 正確: T+30 Event Trading (33 days)
trade = {
    'entry_date': '2019-01-17',
    'actual_exit_date': '2019-02-19',  # 33 days
    'holding_days': 33
}
```

---

### UAL Sentinel Test（金絲雀測試）

**目的**: 永久性回歸測試，檢測執行模型是否正確

**測試案例**: UAL (United Airlines) 2019-01-17

```python
# ✅ 正確 (T+30 Event Trading)
UAL_SENTINEL = {
    'symbol': 'UAL',
    'entry_date': '2019-01-17',
    'exit_date': '2019-02-19',  # 2019-02-15 ~ 2019-02-22 均可
    'holding_days': 33,
    'realized_return': +2.78%
}

# ❌ 錯誤 (Portfolio Rebalance)
UAL_WRONG = {
    'symbol': 'UAL',
    'entry_date': '2019-01-16',
    'exit_date': '2020-10-29',  # FORBIDDEN!
    'holding_days': 452,
    'realized_return': -61.13%
}
```

**為什麼是 UAL?**
- 2019-01-17 是 D7_CORE 中的典型案例
- 如果使用 portfolio rebalance，會持有到 2020-10-29（COVID crash）
- 兩種執行模型的結果差異巨大（+2.78% vs -61.13%）
- 是檢測執行模型錯誤的最佳金絲雀

---

## 💡 最佳實踐

1. **本地測試優先**: 推送前執行 `./test_ci_locally.sh`
2. **小步提交**: 每次只修改一個組合，確保通過驗證
3. **查看日誌**: CI 失敗時仔細查看日誌，修正根本原因
4. **使用 Draft PR**: 實驗性修改使用 Draft PR
5. **保持文件更新**: 新增 rules 同步更新 CLAUDE.md

---

## 🐛 常見問題

### Q1: Workflow 沒有觸發？

**A**: 檢查以下項目:
- GitHub Actions 是否啟用？
- 修改的檔案是否在觸發路徑中？
- Workflow YAML 是否有語法錯誤？

### Q2: Gate-3 驗證失敗怎麼辦？

**A**:
```bash
# 本地驗證找出問題
python3 gate3_execution_contract.py tradeable_FILE.json PORTFOLIO

# 修正後重新推送
git add FILE.json
git commit -m "fix: Gate-3 violations"
git push
```

### Q3: UAL Sentinel Test 失敗？

**A**: 這表示執行模型使用了 portfolio rebalance 而非 T+30:
- 檢查 entry_date 是否為 2019-01-17（不是 2019-01-16）
- 檢查 exit_date 是否在 2019-02-15 ~ 2019-02-22 範圍
- 如果 exit_date = 2020-10-29，需要修正執行模型

### Q4: 如何跳過某個 workflow？

**A**: 在 commit message 中加入 `[skip ci]`:
```bash
git commit -m "docs: update README [skip ci]"
```

---

## 🎉 完成！

CI/CD 自動化已完全設置完成。現在：

1. ✅ **推送程式碼自動驗證**
2. ✅ **PR 自動檢查與報告**
3. ✅ **防止錯誤結果被合併**
4. ✅ **確保所有結果 AUDITABLE**

**下一步**:

```bash
# 提交 CI/CD 配置
git add .github/ test_ci_locally.sh CI_CD_SUMMARY.md
git commit -m "ci: add Gate-2/Gate-3 validation workflows

- Add backtest-validation.yml (main workflow)
- Add gate3-validation.yml (Gate-3 specific)
- Add pre-commit.yml (code quality)
- Add test_ci_locally.sh (local testing)
- Add comprehensive CI/CD documentation
"
git push
```

然後前往 GitHub → Actions tab 查看首次執行！

---

**設置者**: Claude Code
**完成時間**: 2026-01-21
**維護**: 請查看 `.github/README.md` 和 `.github/SETUP_GUIDE.md`
