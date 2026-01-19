#!/usr/bin/env python3
"""
Pro Iteration Script
====================
A Claude + ChatGPT Pro iterative refinement workflow.

This script:
1. Takes an initial task/analysis from Claude
2. Sends it to ChatGPT Pro for recommendations
3. Applies Pro's feedback and continues
4. Repeats for N iterations
5. Logs all inputs/outputs in detail

Usage:
    python pro_iteration.py --task "分析 OOS 驗證結果並給出改進建議"
    python pro_iteration.py --task "優化策略參數" --iterations 5
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests

# Configuration
CHATGPT_PRO_API = "https://chatgpt-pro.gpu5090.whaleforce.dev"
DEFAULT_ITERATIONS = 3
POLL_INTERVAL = 5  # seconds
MAX_WAIT_TIME = 600  # seconds (increased from 300 to handle complex prompts)


class ProIterationLogger:
    """Logger for Pro Iteration workflow."""

    def __init__(self, output_dir: str = None):
        self.start_time = datetime.now()
        self.output_dir = Path(output_dir) if output_dir else Path("pro_iteration_logs")
        self.output_dir.mkdir(exist_ok=True)

        # Create session log file
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file = self.output_dir / f"pro_iteration_{timestamp}.md"
        self.iterations: List[Dict] = []

    def log(self, message: str):
        """Print and log message."""
        print(message)
        with open(self.log_file, "a") as f:
            f.write(message + "\n")

    def log_iteration_start(self, iteration: int, total: int):
        """Log iteration start."""
        self.log(f"\n{'='*70}")
        self.log(f"## ITERATION {iteration}/{total}")
        self.log(f"{'='*70}")
        self.log(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def log_input_to_pro(self, prompt: str):
        """Log input sent to ChatGPT Pro."""
        self.log(f"\n### INPUT TO CHATGPT PRO\n")
        self.log("```")
        self.log(prompt)
        self.log("```")

    def log_output_from_pro(self, response: str, task_id: str, wait_time: float):
        """Log output received from ChatGPT Pro."""
        self.log(f"\n### OUTPUT FROM CHATGPT PRO")
        self.log(f"Task ID: {task_id}")
        self.log(f"Wait Time: {wait_time:.1f}s\n")
        self.log("```")
        self.log(response)
        self.log("```")

    def log_claude_action(self, action: str):
        """Log Claude's action based on Pro's feedback."""
        self.log(f"\n### CLAUDE'S ACTION\n")
        self.log(action)

    def save_summary(self, iterations_data: List[Dict]):
        """Save final summary."""
        summary_file = self.log_file.with_suffix(".json")
        with open(summary_file, "w") as f:
            json.dump({
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_iterations": len(iterations_data),
                "iterations": iterations_data
            }, f, indent=2, ensure_ascii=False)
        self.log(f"\n\n{'='*70}")
        self.log(f"Session saved to: {self.log_file}")
        self.log(f"JSON summary: {summary_file}")


def submit_to_pro(prompt: str, project: str = "pro-iteration") -> Optional[str]:
    """Submit a task to ChatGPT Pro API."""
    try:
        response = requests.post(
            f"{CHATGPT_PRO_API}/chat",
            json={"prompt": prompt, "project": project},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            return data.get("task_id")
        else:
            print(f"Error submitting task: {data}")
            return None
    except Exception as e:
        print(f"Error submitting to Pro API: {e}")
        return None


def wait_for_result(task_id: str, max_idle: int = MAX_WAIT_TIME) -> Dict[str, Any]:
    """Wait for ChatGPT Pro task to complete.

    Args:
        task_id: The task ID to poll
        max_idle: Maximum time to wait when NOT receiving "processing" status.
                  If Pro is actively processing, we wait indefinitely.
    """
    start_time = time.time()
    last_processing_time = time.time()  # Track when we last saw "processing" status
    consecutive_errors = 0
    max_consecutive_errors = 5

    while True:
        try:
            response = requests.get(
                f"{CHATGPT_PRO_API}/task/{task_id}",
                params={"wait": 60},
                timeout=65
            )
            data = response.json()
            consecutive_errors = 0  # Reset error counter on success

            status = data.get("status")

            if status == "completed":
                return {
                    "success": True,
                    "answer": data.get("answer", ""),
                    "wait_time": time.time() - start_time,
                    "chat_url": data.get("chat_url")
                }
            elif status in ["failed", "error", "timeout", "cancelled"]:
                return {
                    "success": False,
                    "error": data.get("error", f"Task {status}"),
                    "wait_time": time.time() - start_time
                }
            elif status in ["processing", "sent", "queued"]:
                # Pro is actively working - reset idle timer and keep waiting
                last_processing_time = time.time()
                progress = data.get("progress", "Processing...")
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] {progress}                    ", end="\r")
            else:
                # Unknown status - check if we've been idle too long
                elapsed_since_processing = time.time() - last_processing_time
                if elapsed_since_processing > max_idle:
                    return {
                        "success": False,
                        "error": f"Timeout: unknown status '{status}' for {max_idle}s",
                        "wait_time": time.time() - start_time
                    }
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] Status: {status}                    ", end="\r")

        except requests.exceptions.Timeout:
            # Network timeout is OK, just retry
            elapsed = int(time.time() - start_time)
            print(f"  [{elapsed}s] Network timeout, retrying...          ", end="\r")
            time.sleep(POLL_INTERVAL)

        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                return {
                    "success": False,
                    "error": f"Too many consecutive errors: {e}",
                    "wait_time": time.time() - start_time
                }
            elapsed = int(time.time() - start_time)
            print(f"  [{elapsed}s] Error: {e}, retrying...               ", end="\r")
            time.sleep(POLL_INTERVAL)


def run_pro_iteration(
    initial_task: str,
    iterations: int = DEFAULT_ITERATIONS,
    context_builder: callable = None
) -> List[Dict]:
    """
    Run the Pro Iteration workflow.

    Args:
        initial_task: The initial task/analysis to iterate on
        iterations: Number of iterations
        context_builder: Optional function to build context for each iteration

    Returns:
        List of iteration results
    """
    logger = ProIterationLogger()

    logger.log(f"# Pro Iteration Session")
    logger.log(f"Start Time: {logger.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.log(f"Initial Task: {initial_task}")
    logger.log(f"Total Iterations: {iterations}")

    results = []
    current_context = initial_task
    accumulated_insights = []

    for i in range(1, iterations + 1):
        logger.log_iteration_start(i, iterations)

        # Build prompt for this iteration
        if i == 1:
            prompt = f"""你是一個專業的策略分析師。請分析以下內容並給出具體可行的建議：

{current_context}

請提供：
1. 關鍵發現摘要
2. 具體改進建議（按優先順序）
3. 下一步行動項目
4. 潛在風險或注意事項"""
        else:
            prompt = f"""這是第 {i} 輪迭代分析。

## 原始任務
{initial_task}

## 上一輪的分析結果
{accumulated_insights[-1] if accumulated_insights else 'N/A'}

## 當前狀態
{current_context}

請基於之前的分析，提供：
1. 進一步的深入洞察
2. 上一輪建議的細化或修正
3. 新發現的問題或機會
4. 具體的下一步行動"""

        logger.log_input_to_pro(prompt)

        # Submit to Pro
        task_id = submit_to_pro(prompt)
        if not task_id:
            logger.log("ERROR: Failed to submit task to Pro API")
            results.append({
                "iteration": i,
                "success": False,
                "error": "Failed to submit task"
            })
            continue

        logger.log(f"\nTask submitted: {task_id}")
        logger.log("Waiting for response...")

        # Wait for result
        result = wait_for_result(task_id)

        if result["success"]:
            pro_response = result["answer"]
            logger.log_output_from_pro(pro_response, task_id, result["wait_time"])

            # Store for next iteration
            accumulated_insights.append(pro_response)

            # Simulate Claude's action based on Pro's feedback
            claude_action = f"""基於 ChatGPT Pro 的建議，將執行以下操作：

1. 記錄並整合 Pro 的分析洞察
2. 更新當前工作狀態
3. 準備下一輪迭代的輸入

Pro 的關鍵建議已被納入考量。"""

            logger.log_claude_action(claude_action)

            # Update context for next iteration
            if context_builder:
                current_context = context_builder(i, pro_response)
            else:
                current_context = f"已完成第 {i} 輪分析。Pro 的回應已整合。"

            results.append({
                "iteration": i,
                "success": True,
                "task_id": task_id,
                "wait_time": result["wait_time"],
                "chat_url": result.get("chat_url"),
                "prompt_length": len(prompt),
                "response_length": len(pro_response),
                "response_preview": pro_response[:500] + "..." if len(pro_response) > 500 else pro_response
            })
        else:
            logger.log(f"\nERROR: {result.get('error', 'Unknown error')}")
            results.append({
                "iteration": i,
                "success": False,
                "error": result.get("error"),
                "wait_time": result.get("wait_time", 0)
            })

    # Final summary
    logger.log(f"\n\n{'='*70}")
    logger.log("# FINAL SUMMARY")
    logger.log(f"{'='*70}")

    successful = sum(1 for r in results if r.get("success"))
    total_wait = sum(r.get("wait_time", 0) for r in results)

    logger.log(f"\n| Metric | Value |")
    logger.log(f"|--------|-------|")
    logger.log(f"| Total Iterations | {iterations} |")
    logger.log(f"| Successful | {successful} |")
    logger.log(f"| Failed | {iterations - successful} |")
    logger.log(f"| Total Wait Time | {total_wait:.1f}s |")
    logger.log(f"| Avg Wait Time | {total_wait/iterations:.1f}s |")

    if accumulated_insights:
        logger.log(f"\n## Accumulated Insights\n")
        for idx, insight in enumerate(accumulated_insights, 1):
            logger.log(f"### Iteration {idx} Key Points")
            # Extract first 300 chars as summary
            logger.log(insight[:500] + "..." if len(insight) > 500 else insight)
            logger.log("")

    logger.save_summary(results)

    return results


def main():
    parser = argparse.ArgumentParser(description="Pro Iteration - Claude + ChatGPT Pro iterative refinement")
    parser.add_argument("--task", "-t", required=True, help="Initial task/analysis to iterate on")
    parser.add_argument("--iterations", "-n", type=int, default=DEFAULT_ITERATIONS,
                        help=f"Number of iterations (default: {DEFAULT_ITERATIONS})")
    parser.add_argument("--context-file", "-c", help="Optional file with additional context")
    args = parser.parse_args()

    # Load additional context if provided
    initial_task = args.task
    if args.context_file:
        context_path = Path(args.context_file)
        if context_path.exists():
            with open(context_path) as f:
                initial_task = f"{args.task}\n\n## Additional Context\n{f.read()}"

    print(f"\n{'='*70}")
    print("PRO ITERATION - Claude + ChatGPT Pro Iterative Refinement")
    print(f"{'='*70}\n")

    results = run_pro_iteration(
        initial_task=initial_task,
        iterations=args.iterations
    )

    # Print final status
    successful = sum(1 for r in results if r.get("success"))
    print(f"\n\nCompleted: {successful}/{args.iterations} iterations successful")

    return 0 if successful == args.iterations else 1


if __name__ == "__main__":
    sys.exit(main())
