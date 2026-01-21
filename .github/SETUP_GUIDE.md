# GitHub Actions 設置指南

本指南說明如何設置和使用 GitHub Actions 自動驗證回測結果。

---

## 🚀 快速開始

### 1. 確認檔案已提交

檢查所有 CI/CD 檔案是否已創建：

```bash
ls -la .github/workflows/
# 應該看到：
# - backtest-validation.yml
# - gate2-qa.yml
# - gate3-validation.yml
# - pre-commit.yml

ls -la test_ci_locally.sh
# 應該是可執行的 (-rwxr-xr-x)
```

### 2. 本地測試（可選但推薦）

在推送前，先本地測試：

```bash
# 確保 python3 可用
which python3

# 執行本地測試
./test_ci_locally.sh
```

**預期輸出**:
- ✅ UAL Sentinel tests passed
- ✅ Code quality checks passed
- ✅ Gate-3 integrity verified

### 3. 提交並推送

```bash
# Stage 所有 CI/CD 檔案
git add .github/ test_ci_locally.sh

# Commit
git commit -m "ci: add Gate-2/Gate-3 validation workflows

- Add backtest-validation.yml (Gate-2 + Gate-3)
- Add gate3-validation.yml (Gate-3 專用)
- Add pre-commit.yml (code quality)
- Add test_ci_locally.sh (local testing)
- Add CI/CD documentation
"

# Push
git push
```

### 4. 查看執行結果

前往 GitHub Repository：
- 點擊 **Actions** tab
- 查看 workflow runs
- 點擊任一 run 查看詳細日誌

---

## 📋 Workflow 詳細說明

### `backtest-validation.yml` (主要 Workflow)

**何時觸發**:
- Push 到 `main` 或 `develop` 分支
- Pull Request 包含:
  - `**.json` (任何 JSON 檔案)
  - `backtest_*.py`
  - `gate*.py`
  - `run_*.py`

**執行步驟**:
1. Setup Python 3.10
2. Install dependencies
3. **Gate-2 Validation**:
   - 執行 pytest tests
   - 檢查 lookahead safety
   - 檢查 EPS coverage
   - 檢查 cross-quarter drift
4. **Gate-3 Validation**:
   - 驗證所有 `tradeable_*.json` 檔案
   - 檢查 holding period (28-45 days)
   - 檢查 trade ledger completeness
5. **UAL Sentinel Test**:
   - 驗證 UAL (2019-01-17) 執行正確性
   - 檢測 portfolio rebalance (452 days)
6. **Generate Report**:
   - 創建 validation report
   - 上傳為 artifact
   - Comment on PR (if applicable)

**產出**:
- ✅ Exit code 0: All validations passed (AUDITABLE)
- ❌ Exit code 1: Validations failed (NON-ACTIONABLE)
- 📄 Validation Report (downloadable artifact)

---

### `gate3-validation.yml` (Gate-3 專用)

**何時觸發**:
- Push/PR 修改:
  - `backtest_stop_loss_tradeable.py`
  - `generate_*_tradeable.py`
  - `gate3_execution_contract.py`
  - `tradeable_*.json`

**用途**:
- 專注於 Gate-3 驗證
- 更快的反饋循環
- 適合開發 execution logic 時使用

---

### `gate2-qa.yml` (Gate-2 專用)

**何時觸發**:
- Push/PR 修改:
  - `pg_client.py`
  - `agentic_rag_bridge.py`
  - `run_full_backtest_gpt5mini.py`
  - `tests/test_gate2_data_contract.py`

**用途**:
- 專注於 Gate-2 驗證
- 確保 data contract 不被破壞
- 適合修改資料層時使用

---

### `pre-commit.yml` (程式碼品質)

**何時觸發**:
- 所有 Push 和 Pull Request

**檢查項目**:
- ✅ Black formatting
- ✅ Flake8 linting
- ✅ isort import sorting
- ✅ Debug statements (pdb, breakpoint)
- ✅ Hardcoded credentials
- ✅ Large files (>10MB)
- ✅ Gate-3 contract integrity
- ✅ CLAUDE.md completeness

---

## 🔧 進階設置

### 設置分支保護規則

1. 前往 Repository Settings
2. 點擊 **Branches**
3. 點擊 **Add branch protection rule**
4. Branch name pattern: `main`
5. 啟用以下選項:
   - ✅ **Require status checks to pass before merging**
   - 選擇: `validate-backtest-results` (job name)
   - ✅ **Require branches to be up to date before merging**
   - ✅ **Require conversation resolution before merging**
6. 保存設置

**效果**: 所有 PR 必須通過 Gate-2 和 Gate-3 驗證才能合併到 main 分支

---

### 設置 GitHub Secrets (如需要)

如果 workflows 需要存取私密資訊（API keys, database credentials）:

1. 前往 Repository Settings
2. 點擊 **Secrets and variables** → **Actions**
3. 點擊 **New repository secret**
4. 添加 secrets:
   - `FMP_API_KEY`
   - `NEO4J_PASSWORD`
   - `POSTGRES_PASSWORD`
   - 等等

在 workflow 中使用:
```yaml
env:
  FMP_API_KEY: ${{ secrets.FMP_API_KEY }}
```

---

### 設置 Caching（提升速度）

已在 `backtest-validation.yml` 中啟用 pip cache:

```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

**效果**: 第二次及以後的 runs 會更快（跳過 dependency installation）

---

## 🐛 故障排除

### 問題 1: Workflow 沒有觸發

**可能原因**:
- GitHub Actions 未啟用
- Workflow 檔案有語法錯誤
- Push 的檔案不在觸發路徑中

**解決方案**:
```bash
# 檢查 workflow 語法
cat .github/workflows/backtest-validation.yml

# 手動觸發 workflow (如果有 workflow_dispatch)
# 或推送一個包含正確路徑的檔案
git add tradeable_test.json
git commit -m "test: trigger workflow"
git push
```

---

### 問題 2: Gate-3 驗證失敗

**常見原因**:
- Holding period > 60 days (portfolio rebalance)
- UAL exit date = 2020-10-29 (wrong execution model)
- Missing required trade fields

**解決方案**:
```bash
# 本地驗證
python3 gate3_execution_contract.py tradeable_FILE.json PORTFOLIO

# 查看詳細錯誤
cat /tmp/test_output.log

# 修正後重新推送
git add FILE.json
git commit -m "fix: Gate-3 violations"
git push
```

---

### 問題 3: pytest 找不到

**原因**: 本地環境沒有安裝 pytest

**解決方案**:
```bash
# 安裝 pytest
pip install pytest

# 或安裝所有依賴
pip install -r requirements.txt

# 重新執行測試
./test_ci_locally.sh
```

---

### 問題 4: Python version 不符

**原因**: Workflow 使用 Python 3.10，但本地不同版本

**解決方案**:
```bash
# 使用 pyenv 安裝 Python 3.10
pyenv install 3.10.12
pyenv local 3.10.12

# 或修改 workflow 使用現有版本
# 編輯 .github/workflows/*.yml
python-version: '3.9'  # 改為你的版本
```

---

## 📊 驗證報告解讀

### AUDITABLE (可審計)

```
## Verdict
✅ AUDITABLE - Results can be used for strategy decisions
```

**含義**:
- Gate-2: PASSED (資料一致性正確)
- Gate-3: PASSED (執行模型正確)
- UAL Sentinel: PASSED (T+30 語意正確)

**可以進行的動作**:
- ✅ 合併 PR
- ✅ 使用結果進行策略決策
- ✅ 部署到生產環境

---

### NON-ACTIONABLE (不可用)

```
## Verdict
❌ NON-ACTIONABLE - Results cannot be used for strategy decisions

Please fix violations before merging. See CLAUDE.md Rule #0 for requirements.
```

**含義**:
- 至少一個 Gate 驗證失敗
- 結果不可信

**必須進行的動作**:
- ❌ 不得合併 PR
- ❌ 不得使用結果
- ⚠️ 修正 violations 後重新驗證

---

## 📖 相關文件

- [CLAUDE.md Rule #0](../CLAUDE.md#0-研究可審計性規範-research-auditability-) - Gate-2/Gate-3 詳細要求
- [gate3_execution_contract.py](../gate3_execution_contract.py) - Gate-3 實作
- [tests/test_gate2_data_contract.py](../tests/test_gate2_data_contract.py) - Gate-2 測試
- [P1_RECALC_PORTFOLIO_METRICS.md](../P1_RECALC_PORTFOLIO_METRICS.md) - P1 驗證計畫
- [.github/README.md](README.md) - CI/CD 總覽

---

## 💡 最佳實踐

1. **本地測試優先**:
   ```bash
   ./test_ci_locally.sh
   ```
   在推送前先本地驗證，節省 CI 時間

2. **小步提交**:
   - 每次只改一個組合
   - 確保每次提交都通過驗證
   - 避免大批量修改

3. **查看日誌**:
   - CI 失敗時，仔細查看日誌
   - 不要盲目重試
   - 修正根本原因

4. **使用 Draft PR**:
   - 實驗性修改使用 Draft PR
   - 確認通過後再 mark as ready

5. **保持 CLAUDE.md 更新**:
   - 新增 rules 同步更新文件
   - 確保 CI 檢查與文件一致

---

**最後更新**: 2026-01-21
**維護者**: Claude Code
