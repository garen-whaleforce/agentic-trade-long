#!/bin/bash
# LiteLLM 成本查詢腳本

API_KEY=$(grep "LITELLM_API_KEY" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")

echo "💰 LiteLLM 當前花費查詢"
echo "時間: $(date)"
echo "================================================================================"

response=$(curl -s -H "Authorization: Bearer $API_KEY" "https://litellm.whaleforce.dev/user/info")

spend=$(echo "$response" | jq -r '.user_info.spend')
max_budget=$(echo "$response" | jq -r '.user_info.max_budget')
reset_at=$(echo "$response" | jq -r '.user_info.budget_reset_at')

echo "當前花費: \$$spend"
echo "預算上限: \$$max_budget"
echo "剩餘預算: \$$(echo "$max_budget - $spend" | bc)"
echo "使用比例: $(echo "scale=1; $spend / $max_budget * 100" | bc)%"
echo "預算重置: $reset_at"
echo ""
echo "Key 詳細資訊:"
echo "$response" | jq -r '.keys[] | "  \(.key_alias): \$\(.spend)"'
