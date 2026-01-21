# GitHub Actions CI/CD

本目錄包含自動化驗證流程，確保所有回測結果符合 Gate-2 和 Gate-3 標準。

---

## 📋 Workflows 總覽

### 1. `backtest-validation.yml` (主要驗證流程)

**觸發條件**:
- Push 到 `main` 或 `develop` 分支
- Pull Request 包含 `.json` 或 `backtest_*.py` 或 `gate*.py` 檔案

**執行內容**:
1. ✅ Gate-2 Data Contract Validation
   - Lookahead Safety (≥90% safe, <5% violations)
   - EPS Surprise Coverage (>95% valid)
   - Cross-Quarter Drift (≥90% ≤3d, 100% ≤7d)
   - NULL Field Threshold (transcript 0%, earnings <5%)

2. ✅ Gate-3 Execution Contract Validation
   - Trade Ledger Complete (所有必要欄位)
   - Holding Period T+30 (28-45 days, <60 hard limit)
   - Price Semantics Documented
   - Signal Mapping 1:1

3. ✅ UAL Sentinel Regression Test
   - Entry: 2019-01-17
   - Exit: 2019-02-15 ~ 2019-02-22 (T+30 valid range)
   - ❌ Forbidden: 2020-10-29 (portfolio rebalance, 452 days)

**產出**:
- Validation Report (artifact)
- PR Comment（自動評論驗證結果）
- Exit code 1 如果驗證失敗

---

### 2. `gate2-qa.yml` (Gate-2 專用)

**觸發條件**:
- Push/PR 修改以下檔案:
  - `pg_client.py`
  - `agentic_rag_bridge.py`
  - `run_full_backtest_gpt5mini.py`
  - `tests/test_gate2_data_contract.py`

**執行內容**:
- 執行 pytest Gate-2 測試
- 執行 standalone Gate-2 測試
- 生成 QA 報告

---

### 3. `gate3-validation.yml` (Gate-3 專用)

**觸發條件**:
- Push/PR 修改以下檔案:
  - `backtest_stop_loss_tradeable.py`
  - `generate_*_tradeable.py`
  - `gate3_execution_contract.py`
  - `tradeable_*.json`
  - 回測結果檔案

**執行內容**:
- 驗證所有 `tradeable_*.json` 檔案
- UAL Sentinel Test
- 生成失敗報告

---

### 4. `pre-commit.yml` (程式碼品質檢查)

**觸發條件**:
- 所有 Push 和 Pull Request

**執行內容**:
- Black (code formatting)
- Flake8 (linting)
- isort (import sorting)
- Debug statements 檢查
- Hardcoded credentials 檢查
- Large files 檢查
- Gate-3 contract integrity 驗證
- CLAUDE.md 完整性檢查

---

## 🚦 驗證狀態

### ✅ AUDITABLE (可審計)

滿足條件:
- Gate-2: PASSED
- Gate-3: PASSED
- UAL Sentinel: PASSED

**結果**: 可以用於策略決策

### ❌ NON-ACTIONABLE (不可用)

觸發條件:
- Gate-2: FAILED (資料不一致)
- Gate-3: FAILED (執行模型錯誤)
- UAL Sentinel: FAILED (portfolio rebalance 檢測)

**結果**: 不得用於策略決策，必須修正後重新驗證

---

## 📊 本地測試

在提交前，可以在本地執行驗證：

### Gate-2 驗證

```bash
# 使用 pytest
pytest tests/test_gate2_data_contract.py -v

# Standalone 測試
python tests/test_gate2_data_contract.py
```

### Gate-3 驗證

```bash
# 驗證單一檔案
python gate3_execution_contract.py tradeable_NO_D4_OPP_stop_none.json NO_D4_OPP

# 驗證所有檔案
for file in tradeable_*.json; do
    portfolio=$(basename "$file" .json | sed 's/tradeable_//')
    python gate3_execution_contract.py "$file" "$portfolio"
done
```

### Pre-commit 檢查

```bash
# 安裝依賴
pip install black flake8 isort

# 執行格式化
black .

# 執行 linting
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# 排序 imports
isort .
```

---

## 🔧 設置說明

### 首次設置

1. **確保 GitHub Actions 已啟用**:
   - 前往 Repository Settings → Actions → General
   - 確認 "Allow all actions and reusable workflows" 已選擇

2. **設置必要的 Secrets** (如果需要):
   - Repository Settings → Secrets and variables → Actions
   - 添加 secrets (例如: API keys, database credentials)

3. **配置分支保護**:
   - Repository Settings → Branches
   - 添加 branch protection rule for `main`:
     - ✅ Require status checks to pass before merging
     - 選擇: `validate-backtest-results`

### 本地 Pre-commit Hook (可選)

創建 `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running pre-commit checks..."

# Check for debug statements
if grep -r "import pdb" --include="*.py" . ; then
    echo "❌ Found 'import pdb'. Please remove before committing."
    exit 1
fi

# Check for credentials.json
if git diff --cached --name-only | grep -q "credentials.json"; then
    echo "❌ credentials.json should not be committed!"
    exit 1
fi

echo "✅ Pre-commit checks passed"
```

然後執行:
```bash
chmod +x .git/hooks/pre-commit
```

---

## 📖 參考文件

- **CLAUDE.md Rule #0**: Gate-2 和 Gate-3 詳細要求
- **P1_RECALC_PORTFOLIO_METRICS.md**: P1 驗證計畫
- **gate3_execution_contract.py**: Gate-3 實作
- **tests/test_gate2_data_contract.py**: Gate-2 測試實作

---

## 🐛 故障排除

### Workflow 失敗處理

1. **查看失敗原因**:
   - GitHub Actions tab → 點擊失敗的 workflow
   - 展開失敗的 step 查看詳細錯誤

2. **常見失敗原因**:

   **Gate-2 失敗**:
   - `earnings_date_used` 為 NULL
   - EPS surprise coverage < 95%
   - Cross-quarter drift > 7 days
   - Lookahead violations > 5%

   **Gate-3 失敗**:
   - Holding period > 60 days (portfolio rebalance)
   - Missing required trade fields
   - UAL exit date = 2020-10-29 (wrong execution model)

3. **修正後重新驗證**:
   ```bash
   # 本地驗證
   python gate3_execution_contract.py tradeable_FILE.json PORTFOLIO

   # Push 觸發 CI
   git add .
   git commit -m "fix: Gate-3 violations"
   git push
   ```

---

## 📞 聯絡

如有問題，請參考:
- CLAUDE.md Rule #0
- P1_RECALC_PORTFOLIO_METRICS.md
- 建立 GitHub Issue

---

**最後更新**: 2026-01-21
**維護者**: Claude Code
