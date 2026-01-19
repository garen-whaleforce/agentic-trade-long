#!/usr/bin/env python3
"""
增量回測腳本 - 支持 Checkpoint 機制
Incremental Backtest with Checkpoint Support

使用方式:
1. 先測試 10 筆: python3 run_incremental_backtest.py --test 10
2. 完整回測: python3 run_incremental_backtest.py --full
3. 從 checkpoint 繼續: python3 run_incremental_backtest.py --resume
"""

import sys
import time
import json
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from agentic_rag_bridge import run_single_call_from_context

# Checkpoint 設定
CHECKPOINT_DIR = Path("backtest_checkpoints")
CHECKPOINT_FILE = CHECKPOINT_DIR / "checkpoint.json"
RESULTS_FILE = CHECKPOINT_DIR / "backtest_results.json"
CHECKPOINT_INTERVAL = 100  # 每 100 筆儲存一次
DEFAULT_WORKERS = 5  # 預設並發數量

# 確保 checkpoint 目錄存在
CHECKPOINT_DIR.mkdir(exist_ok=True)

# 並發控制
results_lock = threading.Lock()
checkpoint_lock = threading.Lock()


def load_earnings_calendar() -> pd.DataFrame:
    """載入財報日曆資料。

    從 earnings_transcripts 表載入 2017-2024 的財報日曆。
    """
    try:
        import pg_client

        # 使用 get_cursor() context manager
        with pg_client.get_cursor() as cur:
            if cur is None:
                print("⚠️  資料庫連接失敗，使用測試資料")
                return create_test_data()

            query = """
                SELECT DISTINCT
                    et.symbol,
                    et.year,
                    et.quarter,
                    et.transcript_date,
                    c.sector
                FROM earnings_transcripts et
                LEFT JOIN companies c ON et.symbol = c.symbol
                WHERE et.year BETWEEN 2017 AND 2024
                  AND et.transcript_date IS NOT NULL
                ORDER BY et.transcript_date, et.symbol
            """

            cur.execute(query)
            result = cur.fetchall()

            if result:
                df = pd.DataFrame(result)
                print(f"✅ 載入 {len(df)} 筆財報記錄 (2017-2024)")
                return df
            else:
                print("⚠️  未找到財報記錄，使用測試資料")
                return create_test_data()

    except Exception as e:
        print(f"⚠️  載入財報日曆失敗: {e}")
        print("使用測試資料")
        return create_test_data()


def create_test_data() -> pd.DataFrame:
    """創建測試資料 (如果沒有實際資料)。"""
    test_data = []

    # 2024 Q1 測試資料
    symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMZN", "TSLA",
               "JPM", "JNJ", "XOM", "AMD", "NFLX", "NKE", "HD", "BA"]

    for symbol in symbols:
        test_data.append({
            "symbol": symbol,
            "year": 2024,
            "quarter": 1,
            "transcript_date": "2024-02-01",
            "sector": "Technology"
        })

    return pd.DataFrame(test_data)


def load_checkpoint() -> Dict[str, Any]:
    """載入 checkpoint。"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            checkpoint = json.load(f)
        print(f"✅ 載入 checkpoint: 已處理 {checkpoint['processed_count']} 筆")
        return checkpoint
    return {
        "processed_count": 0,
        "processed_ids": [],
        "last_update": None
    }


def save_checkpoint(checkpoint: Dict[str, Any]):
    """儲存 checkpoint。"""
    # 確保目錄存在
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    checkpoint["last_update"] = datetime.now().isoformat()
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)
    print(f"💾 Checkpoint 已儲存: {checkpoint['processed_count']} 筆")


def load_results() -> List[Dict[str, Any]]:
    """載入已有的結果。"""
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
            return data.get("results", [])
    return []


def save_results(results: List[Dict[str, Any]], checkpoint: Dict[str, Any],
                 stats: Dict[str, Any]):
    """儲存結果。"""
    # 確保目錄存在
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    output = {
        "last_update": datetime.now().isoformat(),
        "total_processed": checkpoint["processed_count"],
        "statistics": stats,
        "results": results
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"💾 結果已儲存: {len(results)} 筆記錄")


def calculate_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """計算統計資訊。"""
    if not results:
        return {}

    df = pd.DataFrame(results)

    # 過濾成功的結果
    if "error" in df.columns:
        successful = df[df["error"].isna()]
    else:
        successful = df

    if len(successful) == 0:
        return {"error": "No successful results"}

    # Direction Score 分佈
    direction_dist = successful["direction_score"].value_counts().to_dict()

    # Tier 分佈
    trade_long_df = successful[successful["trade_long"]]
    tier_dist = {}
    if len(trade_long_df) > 0:
        tier_dist = trade_long_df["tier"].value_counts().to_dict()

    # 交易信號統計
    trade_count = successful["trade_long"].sum()
    trade_rate = trade_count / len(successful) * 100 if len(successful) > 0 else 0

    # 高階 Tier 統計
    high_tier_count = sum(1 for t in trade_long_df["tier"] if t in ["D8_MEGA", "D7_CORE", "D6_STRICT"])
    high_tier_ratio = high_tier_count / len(trade_long_df) * 100 if len(trade_long_df) > 0 else 0

    # 時間統計
    avg_time = successful["time_seconds"].mean()
    total_time = successful["time_seconds"].sum()

    # EPS Surprise 統計
    eps_available = successful[successful["eps_surprise"].notna()]
    eps_stats = {}
    if len(eps_available) > 0:
        eps_stats = {
            "mean": float(eps_available["eps_surprise"].mean()),
            "median": float(eps_available["eps_surprise"].median()),
            "min": float(eps_available["eps_surprise"].min()),
            "max": float(eps_available["eps_surprise"].max()),
        }

    return {
        "total_analyzed": len(successful),
        "total_errors": len(df) - len(successful),
        "direction_distribution": direction_dist,
        "tier_distribution": tier_dist,
        "trade_signals": {
            "count": int(trade_count),
            "rate": float(trade_rate)
        },
        "high_tier_stats": {
            "count": high_tier_count,
            "ratio": float(high_tier_ratio)
        },
        "performance": {
            "avg_time_seconds": float(avg_time),
            "total_time_seconds": float(total_time),
            "total_time_hours": float(total_time / 3600)
        },
        "eps_surprise": eps_stats
    }


def print_statistics(stats: Dict[str, Any], processed_count: int):
    """打印統計資訊。"""
    print("\n" + "=" * 80)
    print(f"📊 當前統計 (已處理 {processed_count} 筆)")
    print("=" * 80)

    if not stats or "error" in stats:
        print("⚠️  暫無統計資訊")
        return

    print(f"\n✅ 成功分析: {stats['total_analyzed']} 筆")
    if stats['total_errors'] > 0:
        print(f"❌ 錯誤: {stats['total_errors']} 筆")

    # Direction Score
    print(f"\n📊 Direction Score 分佈:")
    direction_dist = stats.get("direction_distribution", {})
    for score in sorted(direction_dist.keys(), reverse=True):
        count = direction_dist[score]
        pct = count / stats['total_analyzed'] * 100
        bar = "█" * max(1, int(pct / 5))
        print(f"  D{score}: {count:4d} ({pct:5.1f}%) {bar}")

    # Tier 分佈
    tier_dist = stats.get("tier_distribution", {})
    if tier_dist:
        print(f"\n🏆 Tier 分佈:")
        for tier in ["D8_MEGA", "D7_CORE", "D6_STRICT", "D5_GATED", "D4_ENTRY", "D4_OPP", "D3_WIDE"]:
            if tier in tier_dist:
                count = tier_dist[tier]
                print(f"  {tier}: {count}")

    # 交易信號
    trade_stats = stats.get("trade_signals", {})
    print(f"\n✅ 交易信號: {trade_stats.get('count', 0)} ({trade_stats.get('rate', 0):.1f}%)")

    # 高階 Tier
    high_tier = stats.get("high_tier_stats", {})
    print(f"   高階 Tier (D6+): {high_tier.get('count', 0)} ({high_tier.get('ratio', 0):.1f}%)")

    # 性能
    perf = stats.get("performance", {})
    print(f"\n⏱️  性能統計:")
    print(f"   平均時間: {perf.get('avg_time_seconds', 0):.1f}s per call")
    print(f"   總時間: {perf.get('total_time_hours', 0):.2f} hours")

    # EPS Surprise
    eps_stats = stats.get("eps_surprise", {})
    if eps_stats:
        print(f"\n💰 EPS Surprise 統計:")
        print(f"   平均: {eps_stats.get('mean', 0):.1%}")
        print(f"   範圍: {eps_stats.get('min', 0):.1%} ~ {eps_stats.get('max', 0):.1%}")

    print("=" * 80 + "\n")


def process_single_case(row_data: Dict[str, Any]) -> Dict[str, Any]:
    """處理單筆案例的 worker 函數。

    Args:
        row_data: 包含 symbol, year, quarter, record_id 的字典

    Returns:
        處理結果字典
    """
    symbol = row_data["symbol"]
    year = row_data["year"]
    quarter = row_data["quarter"]
    record_id = row_data["record_id"]

    try:
        case_start = time.time()

        context = {
            "symbol": symbol,
            "year": year,
            "quarter": quarter,
            "transcript_date": None,
        }

        result = run_single_call_from_context(context)
        case_time = time.time() - case_start

        # 提取結果
        long_eligible = result.get("long_eligible_json", {})
        direction_score = long_eligible.get("DirectionScore", 0)
        confidence = result.get("confidence", 0)
        trade_long = result.get("trade_long", False)
        tier = result.get("trade_long_tier", "")

        market_anchors = result.get("market_anchors", {})
        eps_surprise = market_anchors.get("eps_surprise")

        return {
            "id": record_id,
            "symbol": symbol,
            "year": year,
            "quarter": quarter,
            "direction_score": direction_score,
            "confidence": confidence,
            "trade_long": trade_long,
            "tier": tier,
            "eps_surprise": eps_surprise,
            "time_seconds": case_time,
            "success": True
        }

    except Exception as e:
        error_msg = str(e)[:100]
        return {
            "id": record_id,
            "symbol": symbol,
            "year": year,
            "quarter": quarter,
            "error": error_msg,
            "time_seconds": 0,
            "success": False
        }


def run_backtest(calendar_df: pd.DataFrame, max_samples: Optional[int] = None,
                 resume: bool = False, workers: int = DEFAULT_WORKERS):
    """執行回測。

    Args:
        calendar_df: 財報日曆 DataFrame
        max_samples: 最大樣本數 (None = 全部)
        resume: 是否從 checkpoint 繼續
        workers: 並發數量（1 = 串行，>1 = 並發）
    """
    # 載入 checkpoint 和結果
    checkpoint = load_checkpoint() if resume else {
        "processed_count": 0,
        "processed_ids": [],
        "last_update": None
    }

    results = load_results() if resume else []

    # 過濾已處理的記錄
    processed_ids = set(checkpoint["processed_ids"])
    calendar_df["id"] = calendar_df.apply(
        lambda row: f"{row['symbol']}_{row['year']}Q{row['quarter']}",
        axis=1
    )

    if resume:
        calendar_df = calendar_df[~calendar_df["id"].isin(processed_ids)]
        print(f"🔄 從 checkpoint 繼續: 剩餘 {len(calendar_df)} 筆")

    # 限制樣本數
    if max_samples:
        calendar_df = calendar_df.head(max_samples)

    total_samples = len(calendar_df)
    if total_samples == 0:
        print("✅ 所有記錄已處理完成")
        return

    print("\n" + "=" * 80)
    print(f"🚀 開始回測 ({'並發' if workers > 1 else '串行'}模式)")
    print("=" * 80)
    print(f"總樣本數: {total_samples}")
    print(f"已處理: {checkpoint['processed_count']}")
    print(f"待處理: {total_samples}")
    if workers > 1:
        print(f"並發數量: {workers} workers")
    print("=" * 80 + "\n")

    start_time = time.time()
    last_checkpoint_time = start_time
    completed_count = 0

    # 準備任務數據
    tasks = []
    for i, row in enumerate(calendar_df.itertuples(), 1):
        tasks.append({
            "index": i,
            "symbol": row.symbol,
            "year": row.year,
            "quarter": row.quarter,
            "record_id": row.id
        })

    # 選擇執行模式：串行或並發
    if workers == 1:
        # 串行模式（原始邏輯）
        for task in tasks:
            i = task["index"]
            symbol = task["symbol"]
            year = task["year"]
            quarter = task["quarter"]
            record_id = task["record_id"]

            print(f"[{i}/{total_samples}] {symbol} {year}Q{quarter}...", end=" ", flush=True)

            result_data = process_single_case(task)

            if result_data["success"]:
                direction_score = result_data["direction_score"]
                tier = result_data["tier"]
                case_time = result_data["time_seconds"]
                print(f"✓ D{direction_score} {tier if tier else 'N/A'} ({case_time:.1f}s)")
            else:
                print(f"✗ 錯誤: {result_data['error']}")

            results.append(result_data)
            checkpoint["processed_ids"].append(record_id)
            checkpoint["processed_count"] += 1
            completed_count += 1

            # Checkpoint: 每 CHECKPOINT_INTERVAL 筆或最後一筆
            if completed_count % CHECKPOINT_INTERVAL == 0 or completed_count == total_samples:
                elapsed = time.time() - last_checkpoint_time

                # 計算統計
                stats = calculate_statistics(results)

                # 儲存 checkpoint 和結果
                save_checkpoint(checkpoint)
                save_results(results, checkpoint, stats)

                # 打印統計
                print_statistics(stats, checkpoint["processed_count"])

                # 估計剩餘時間
                if completed_count < total_samples:
                    avg_time_per_sample = elapsed / CHECKPOINT_INTERVAL
                    remaining_samples = total_samples - completed_count
                    estimated_remaining_time = avg_time_per_sample * remaining_samples

                    print(f"⏱️  預估剩餘時間: {estimated_remaining_time/60:.1f} 分鐘")
                    print()

                last_checkpoint_time = time.time()

    else:
        # 並發模式
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # 提交所有任務
            future_to_task = {executor.submit(process_single_case, task): task for task in tasks}

            # 處理完成的任務
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                i = task["index"]
                symbol = task["symbol"]
                year = task["year"]
                quarter = task["quarter"]
                record_id = task["record_id"]

                result_data = future.result()

                # 輸出結果
                if result_data["success"]:
                    direction_score = result_data["direction_score"]
                    tier = result_data["tier"]
                    case_time = result_data["time_seconds"]
                    print(f"[{completed_count+1}/{total_samples}] {symbol} {year}Q{quarter} ✓ D{direction_score} {tier if tier else 'N/A'} ({case_time:.1f}s)")
                else:
                    print(f"[{completed_count+1}/{total_samples}] {symbol} {year}Q{quarter} ✗ 錯誤: {result_data['error']}")

                # 線程安全的更新
                with results_lock:
                    results.append(result_data)

                with checkpoint_lock:
                    checkpoint["processed_ids"].append(record_id)
                    checkpoint["processed_count"] += 1
                    completed_count += 1

                    # Checkpoint: 每 CHECKPOINT_INTERVAL 筆或最後一筆
                    if completed_count % CHECKPOINT_INTERVAL == 0 or completed_count == total_samples:
                        elapsed = time.time() - last_checkpoint_time

                        # 計算統計
                        stats = calculate_statistics(results)

                        # 儲存 checkpoint 和結果
                        save_checkpoint(checkpoint)
                        save_results(results, checkpoint, stats)

                        # 打印統計
                        print_statistics(stats, checkpoint["processed_count"])

                        # 估計剩餘時間
                        if completed_count < total_samples:
                            avg_time_per_sample = elapsed / CHECKPOINT_INTERVAL
                            remaining_samples = total_samples - completed_count
                            estimated_remaining_time = avg_time_per_sample * remaining_samples

                            print(f"⏱️  預估剩餘時間: {estimated_remaining_time/60:.1f} 分鐘")
                            print()

                        last_checkpoint_time = time.time()

    # 最終統計
    total_time = time.time() - start_time
    final_stats = calculate_statistics(results)

    print("\n" + "=" * 80)
    print("🎉 回測完成")
    print("=" * 80)
    print(f"總時間: {total_time/3600:.2f} hours")
    print(f"總樣本: {checkpoint['processed_count']}")
    print("=" * 80 + "\n")

    print_statistics(final_stats, checkpoint["processed_count"])


def main():
    parser = argparse.ArgumentParser(description="增量回測腳本")
    parser.add_argument("--test", type=int, metavar="N",
                       help="測試模式: 只處理 N 筆")
    parser.add_argument("--full", action="store_true",
                       help="完整回測: 處理所有記錄")
    parser.add_argument("--limit", type=int, metavar="N",
                       help="限制處理數量: 最多處理 N 筆 (可與 --resume 配合)")
    parser.add_argument("--workers", type=int, metavar="N", default=DEFAULT_WORKERS,
                       help=f"並發數量 (預設: {DEFAULT_WORKERS}, 設為 1 則串行)")
    parser.add_argument("--resume", action="store_true",
                       help="從 checkpoint 繼續")
    parser.add_argument("--reset", action="store_true",
                       help="重置 checkpoint 和結果")

    args = parser.parse_args()

    # 重置
    if args.reset:
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
        if RESULTS_FILE.exists():
            RESULTS_FILE.unlink()
        print("✅ Checkpoint 和結果已重置")
        return

    # 載入財報日曆
    print("📅 載入財報日曆...")
    calendar_df = load_earnings_calendar()

    if len(calendar_df) == 0:
        print("❌ 未找到財報記錄")
        sys.exit(1)

    # 執行回測
    if args.test:
        print(f"\n🧪 測試模式: 處理 {args.test} 筆")
        run_backtest(calendar_df, max_samples=args.test, resume=False, workers=args.workers)
    elif args.limit:
        print(f"\n🎯 限制模式: 處理 {args.limit} 筆")
        run_backtest(calendar_df, max_samples=args.limit, resume=args.resume, workers=args.workers)
    elif args.full:
        print("\n🚀 完整回測模式")
        run_backtest(calendar_df, max_samples=None, resume=args.resume, workers=args.workers)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
