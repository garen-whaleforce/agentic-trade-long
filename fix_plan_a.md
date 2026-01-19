# 方案 A 修复计划

## 已确认的问题

### 1. D4_OPP 氾滥
**位置**: Line 1114-1128
**问题代码**:
```python
has_any_eps = eps_surprise is not None and eps_surprise >= 0.01  # 只要 1%！
d4_opp_confirm_ok = has_any_positive or has_any_eps  # OR 条件
```
**问题**: eps 门槛仅 1%，且缺少 momentum check

### 2. D6_STRICT 稀缺
**位置**: Line 528
**问题代码**:
```python
LONG_D6_REQUIRE_LOW_RISK = os.getenv("LONG_D6_REQUIRE_LOW_RISK", "1") == "1"  # 启用！
LONG_D6_EXCLUDE_SECTORS = "Technology"  # 封锁科技业
```
**问题**: 要求 low risk，排除大量信号

### 3. D7_CORE 不足
**位置**: Line 518-519
**问题代码**:
```python
LONG_D7_MIN_DAY_RET = 1.0  # 可能过高
LONG_D7_REQUIRE_EPS_POS = "1"  # 要求 eps > 0
```
**问题**: 双重限制可能过严

### 4. D8_MEGA 存在
**位置**: Line 966-980
**问题**: v34 tier，需禁用以回到 v33

## 修复方案

### 修复 1: 禁用 D8_MEGA
注释掉 D8_MEGA 相关代码 (line 966-980)

### 修复 2: 强化 D4_OPP gates
```python
# 新条件:
- eps_surprise >= 0.03 (3%)
- 增加 momentum_aligned 检查
- soft_veto_count <= 2 (保持)
```

### 修复 3: 修复 D6 配置
```python
LONG_D6_REQUIRE_LOW_RISK = "0"  # 禁用
LONG_D6_EXCLUDE_SECTORS = ""    # 移除封锁
```

### 修复 4: 放宽 D7 配置
```python
LONG_D7_MIN_DAY_RET = 0.8       # 从 1.0 降至 0.8
LONG_D7_REQUIRE_EPS_POS = "0"   # 禁用，允许负 eps_surprise
```
