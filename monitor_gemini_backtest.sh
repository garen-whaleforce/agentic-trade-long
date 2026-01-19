#!/bin/bash

echo "📊 Gemini 4000樣本回測監控"
echo "============================================================"
echo ""

# 檢查進程
if ps aux | grep "run_incremental_backtest" | grep -v grep > /dev/null; then
    echo "✅ 回測進程運行中"
else
    echo "❌ 回測進程未運行"
    exit 1
fi

# 進度統計
echo ""
echo "📈 進度統計:"
TOTAL_LINES=$(wc -l < gemini_4000_backtest.log)
COMPLETED=$(grep -c "\✓\|\✗" gemini_4000_backtest.log || echo 0)
ERRORS=$(grep -c "✗" gemini_4000_backtest.log || echo 0)
PERCENTAGE=$(echo "scale=2; $COMPLETED * 100 / 4000" | bc)

echo "  總樣本數: 4000"
echo "  已完成: $COMPLETED ($PERCENTAGE%)"
echo "  錯誤數: $ERRORS"
echo "  日誌行數: $TOTAL_LINES"

# 最新進度
echo ""
echo "📝 最新 10 筆:"
tail -30 gemini_4000_backtest.log | grep -E "\[.*\].*✓\|\[.*\].*✗" | tail -10

# Checkpoint 狀態
echo ""
echo "💾 Checkpoint 狀態:"
if [ -f "backtest_checkpoints/checkpoint.json" ]; then
    CHECKPOINT_COUNT=$(jq -r '.processed_count' backtest_checkpoints/checkpoint.json 2>/dev/null || echo "N/A")
    echo "  Checkpoint 已處理: $CHECKPOINT_COUNT"
else
    echo "  ⚠️  Checkpoint 文件不存在"
fi

# 成本估算
echo ""
echo "💰 成本估算:"
CURRENT_SPEND=$(bash litellm_cost_check.sh 2>&1 | grep "當前花費" | awk '{print $2}')
echo "  當前花費: $CURRENT_SPEND"
BASELINE=17.18
if [ ! -z "$CURRENT_SPEND" ]; then
    INCREMENTAL=$(echo "$CURRENT_SPEND - $BASELINE" | bc)
    PER_SAMPLE=$(echo "scale=4; $INCREMENTAL / $COMPLETED" | bc 2>/dev/null || echo "N/A")
    PROJECTED=$(echo "scale=2; $PER_SAMPLE * 4000" | bc 2>/dev/null || echo "N/A")
    echo "  增量花費: \$$INCREMENTAL"
    echo "  平均/筆: \$$PER_SAMPLE"
    echo "  預估總成本: \$$PROJECTED"
fi

# 時間統計
echo ""
echo "⏱️  時間統計:"
if [ -f "backtest_checkpoints/backtest_results.json" ]; then
    AVG_TIME=$(jq -r '.statistics.performance.avg_time_seconds' backtest_checkpoints/backtest_results.json 2>/dev/null || echo "N/A")
    TOTAL_TIME=$(jq -r '.statistics.performance.total_time_hours' backtest_checkpoints/backtest_results.json 2>/dev/null || echo "N/A")
    echo "  平均時間: ${AVG_TIME}s"
    echo "  已用時間: ${TOTAL_TIME}h"
    
    if [ "$COMPLETED" -gt 0 ]; then
        REMAINING=$(echo "4000 - $COMPLETED" | bc)
        EST_REMAINING=$(echo "scale=2; $REMAINING * $AVG_TIME / 10 / 3600" | bc 2>/dev/null || echo "N/A")
        echo "  預估剩餘: ${EST_REMAINING}h"
    fi
fi

echo ""
echo "============================================================"
echo "執行時間: $(date)"
