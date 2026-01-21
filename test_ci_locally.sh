#!/bin/bash

# Local CI/CD Test Script
# 在推送到 GitHub 前，在本地測試 CI/CD workflows

set -e  # Exit on error

echo "=================================="
echo "Local CI/CD Test Suite"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0
skipped=0

# Function to run test
run_test() {
    local test_name=$1
    local test_cmd=$2

    echo "Running: $test_name"

    if eval "$test_cmd" > /tmp/test_output.log 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        ((passed++))
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo "Output:"
        cat /tmp/test_output.log
        ((failed++))
    fi
    echo ""
}

# Function to skip test
skip_test() {
    local test_name=$1
    local reason=$2
    echo -e "${YELLOW}⚠️  SKIP${NC}: $test_name ($reason)"
    ((skipped++))
    echo ""
}

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2)
echo "Python version: $python_version"
echo ""

# Test 1: Gate-2 Data Contract
echo "=================================="
echo "Test 1: Gate-2 Data Contract"
echo "=================================="

if [ -f "tests/test_gate2_data_contract.py" ]; then
    backtest_file="EarningsCallAgenticRag/backtest_checkpoints_gpt5mini/backtest_results_gpt5mini.json"

    if [ -f "$backtest_file" ]; then
        run_test "Gate-2 pytest" "SKIP_DB_CONNECTION=true pytest tests/test_gate2_data_contract.py -v"
    else
        skip_test "Gate-2 pytest" "No backtest results found"
    fi
else
    skip_test "Gate-2 pytest" "Test file not found"
fi

# Test 2: Gate-3 Execution Contract
echo "=================================="
echo "Test 2: Gate-3 Execution Contract"
echo "=================================="

tradeable_files=$(find . -maxdepth 1 -name "tradeable_*.json" -type f 2>/dev/null)

if [ -z "$tradeable_files" ]; then
    skip_test "Gate-3 validation" "No tradeable_*.json files found"
else
    echo "Found tradeable files:"
    echo "$tradeable_files"
    echo ""

    for file in $tradeable_files; do
        portfolio=$(basename "$file" .json | sed 's/tradeable_//')
        run_test "Gate-3: $file" "python gate3_execution_contract.py '$file' '$portfolio'"
    done
fi

# Test 3: UAL Sentinel Test
echo "=================================="
echo "Test 3: UAL Sentinel Regression"
echo "=================================="

sentinel_found=false

for file in tradeable_*.json; do
    if [ ! -f "$file" ]; then continue; fi

    if grep -q '"symbol".*:.*"UAL"' "$file" && \
       grep -q '"2019-01-17"' "$file"; then
        sentinel_found=true
        echo "✅ Found UAL sentinel in: $file"

        # Check exit date
        exit_date=$(python3 -c "
import json
with open('$file') as f:
    data = json.load(f)
trades = data.get('trades', [])
for t in trades:
    if t.get('symbol') == 'UAL' and t.get('entry_date') == '2019-01-17':
        print(t.get('actual_exit_date', 'UNKNOWN'))
        break
")

        echo "   Entry: 2019-01-17"
        echo "   Exit:  $exit_date"

        if [[ "$exit_date" > "2019-02-14" && "$exit_date" < "2019-02-23" ]]; then
            echo -e "   ${GREEN}✅ T+30 execution CORRECT${NC}"
            ((passed++))
        elif [[ "$exit_date" == "2020-10-29" ]]; then
            echo -e "   ${RED}❌ PORTFOLIO REBALANCE DETECTED${NC}"
            ((failed++))
        else
            echo -e "   ${YELLOW}⚠️  Exit date outside expected range${NC}"
            ((skipped++))
        fi
    fi
done

if [ "$sentinel_found" = false ]; then
    skip_test "UAL Sentinel" "UAL not found in any file"
fi
echo ""

# Test 4: Code Quality Checks
echo "=================================="
echo "Test 4: Code Quality Checks"
echo "=================================="

# Check for debug statements
echo "Checking for debug statements..."
if grep -r "import pdb" --include="*.py" . 2>/dev/null | grep -v ".git" | grep -v "test_ci"; then
    echo -e "${RED}❌ Found 'import pdb' statements${NC}"
    ((failed++))
else
    echo -e "${GREEN}✅ No 'import pdb' found${NC}"
    ((passed++))
fi

if grep -r "breakpoint()" --include="*.py" . 2>/dev/null | grep -v ".git"; then
    echo -e "${RED}❌ Found 'breakpoint()' statements${NC}"
    ((failed++))
else
    echo -e "${GREEN}✅ No 'breakpoint()' found${NC}"
    ((passed++))
fi
echo ""

# Check for credentials
echo "Checking for credentials..."
if git ls-files | grep -q "credentials.json"; then
    echo -e "${RED}❌ credentials.json is tracked by git!${NC}"
    ((failed++))
else
    echo -e "${GREEN}✅ credentials.json not tracked${NC}"
    ((passed++))
fi
echo ""

# Check Gate-3 integrity
echo "Checking Gate-3 contract integrity..."
if grep -q "MIN_HOLDING_DAYS.*=.*28" gate3_execution_contract.py 2>/dev/null && \
   grep -q "MAX_HOLDING_DAYS.*=.*45" gate3_execution_contract.py 2>/dev/null && \
   grep -q "HARD_MAX_HOLDING_DAYS.*=.*60" gate3_execution_contract.py 2>/dev/null; then
    echo -e "${GREEN}✅ Gate-3 constants verified${NC}"
    ((passed++))
else
    echo -e "${RED}❌ Gate-3 constants missing or incorrect${NC}"
    ((failed++))
fi
echo ""

# Test 5: CLAUDE.md completeness
echo "=================================="
echo "Test 5: Documentation Completeness"
echo "=================================="

echo "Checking CLAUDE.md..."
if grep -q "Gate-3: Execution Contract" CLAUDE.md 2>/dev/null; then
    echo -e "${GREEN}✅ Gate-3 documented in CLAUDE.md${NC}"
    ((passed++))
else
    echo -e "${YELLOW}⚠️  Gate-3 not documented in CLAUDE.md${NC}"
    ((skipped++))
fi

if grep -q "UAL Sentinel" CLAUDE.md 2>/dev/null; then
    echo -e "${GREEN}✅ UAL Sentinel documented${NC}"
    ((passed++))
else
    echo -e "${YELLOW}⚠️  UAL Sentinel not documented${NC}"
    ((skipped++))
fi
echo ""

# Summary
echo "=================================="
echo "Test Summary"
echo "=================================="
echo -e "${GREEN}Passed:${NC}  $passed"
echo -e "${RED}Failed:${NC}  $failed"
echo -e "${YELLOW}Skipped:${NC} $skipped"
echo "=================================="

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "You can safely push to GitHub."
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo ""
    echo "Please fix the issues before pushing to GitHub."
    echo "See output above for details."
    exit 1
fi
