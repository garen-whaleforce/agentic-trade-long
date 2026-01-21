"""
Agentic RAG Bridge - Strategy Version Control

STRATEGY_VERSION: v33_iteration1_rollback
DATE: 2026-01-19
STATUS: Production Ready

Changes from previous version:
- DISABLED D8_MEGA tier (rollback to v33)
- STRENGTHENED D4_OPP gates (eps >= 3%, momentum check)
- FIXED D6 gates (disabled LOW_RISK requirement, removed Tech exclusion)
- RELAXED D7 gates (day_ret >= 0.8, allow negative eps_surprise)

Expected signal rate: 15-20% (down from 38.5%)
Expected D4_OPP ratio: <30% (down from 58.9%)
Expected D6/D7 signals: Increased significantly
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgenticRagBridgeError(RuntimeError):
    """Custom error for Agentic RAG bridge failures."""


REPO_NAME = "EarningsCallAgenticRag"
STRATEGY_VERSION = "v33_iteration1_rollback"


def _resolve_repo_path() -> Path:
    """Locate the external repo; raise with actionable guidance if missing."""
    base = Path(__file__).resolve().parent
    env_path = os.getenv("EARNINGS_RAG_PATH")
    repo_path = Path(env_path) if env_path else base / REPO_NAME
    if not repo_path.exists():
        raise AgenticRagBridgeError(
            f"找不到外部研究庫資料夾：{repo_path}. "
            "請先執行 `git clone https://github.com/la9806958/EarningsCallAgenticRag.git EarningsCallAgenticRag` "
            "並確認與本專案並排。"
        )
    return repo_path


def _ensure_sys_path(repo_path: Path) -> None:
    repo_str = str(repo_path)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


def _env_credentials() -> Optional[Dict[str, Any]]:
    """Build credentials from environment variables using LiteLLM proxy."""
    # LiteLLM configuration
    litellm_endpoint = os.getenv("LITELLM_ENDPOINT", "https://litellm.whaleforce.dev")
    litellm_api_key = os.getenv("LITELLM_API_KEY")

    # Neo4j configuration
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_db = os.getenv("NEO4J_DATABASE") or "neo4j"

    if not all([litellm_api_key, neo4j_uri, neo4j_username, neo4j_password]):
        return None

    creds: Dict[str, Any] = {
        # Use LiteLLM as OpenAI-compatible endpoint
        "openai_api_key": litellm_api_key,
        "openai_api_base": litellm_endpoint,
        # Neo4j settings
        "neo4j_uri": neo4j_uri,
        "neo4j_username": neo4j_username,
        "neo4j_password": neo4j_password,
        "neo4j_database": neo4j_db,
    }

    return creds


def _credentials_path(repo_path: Path) -> Path:
    cred = repo_path / "credentials.json"
    if not cred.exists():
        env_creds = _env_credentials()
        if env_creds:
            try:
                # Avoid race: create only if missing
                cred.write_text(json.dumps(env_creds, indent=2))
            except FileExistsError:
                # Another process wrote it; keep going
                pass
        else:
            raise AgenticRagBridgeError(
                f"外部庫的 credentials.json 未找到：{cred}. "
                "請依照 EarningsCallAgenticRag README 填入 LiteLLM 與 Neo4j 設定，或在環境變數提供 LITELLM_API_KEY / NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD。"
            )
    return cred


def get_stock_volatility(symbol: str, as_of_date: str) -> float:
    """從 PostgreSQL 查詢股票歷史波動率。

    Added: 2026-01-19 (ChatGPT Pro Round 10 - Phase 6)

    Args:
        symbol: 股票代碼
        as_of_date: 參考日期 (transcript_date)，格式 YYYY-MM-DD

    Returns:
        年化波動率 (如 0.35 = 35%)，如無數據則返回 0.30 (預設值)
    """
    try:
        import pg_client
        from datetime import datetime, timedelta

        # Convert as_of_date to datetime
        if isinstance(as_of_date, str):
            ref_date = datetime.strptime(as_of_date, "%Y-%m-%d")
        else:
            ref_date = as_of_date

        # Query last 252 trading days (1 year) of returns before ref_date
        query = """
            WITH daily_returns AS (
                SELECT
                    date,
                    close,
                    LAG(close) OVER (ORDER BY date) AS prev_close
                FROM historical_prices
                WHERE symbol = %s
                  AND date < %s
                ORDER BY date DESC
                LIMIT 252
            )
            SELECT
                STDDEV((close - prev_close) / prev_close) * SQRT(252) AS annualized_volatility,
                COUNT(*) AS sample_size
            FROM daily_returns
            WHERE prev_close IS NOT NULL
        """

        result = pg_client.execute(query, (symbol, ref_date.strftime("%Y-%m-%d")))

        if result and len(result) > 0:
            row = result[0]
            volatility = row.get("annualized_volatility")
            sample_size = row.get("sample_size", 0)

            if volatility is not None and sample_size >= 100:  # At least 100 trading days
                volatility_float = float(volatility)
                # Sanity check: volatility should be between 5% and 200%
                if 0.05 <= volatility_float <= 2.0:
                    return volatility_float
                else:
                    print(f"Warning: {symbol} volatility {volatility_float:.2%} outside normal range, using default")
                    return 0.30
            else:
                print(f"Warning: {symbol} insufficient volatility data (n={sample_size}), using default 0.30")
                return 0.30
        else:
            print(f"Warning: No volatility data for {symbol}, using default 0.30")
            return 0.30

    except Exception as e:
        print(f"Error fetching volatility for {symbol}: {e}")
        return 0.30  # Conservative default


def validate_market_anchors(market_anchors: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """驗證和清理 market anchors 數據。

    CRITICAL FIX (2026-01-21): 修正單位不一致問題
    - pg_client 返回的是百分點 (5.5 = +5.5%)
    - 截斷值必須使用百分點制，不是小數制

    Added: 2026-01-19 (ChatGPT Pro Round 10 - Phase 6)
    Fixed: 2026-01-21 (P0-1 Critical Fix)

    Args:
        market_anchors: Market anchors dictionary (returns are in percentage points)

    Returns:
        Validated and cleaned market anchors
    """
    if not market_anchors:
        return {}

    validated = market_anchors.copy()

    # Cap extreme eps_surprise values (±200%)
    eps_surprise = validated.get("eps_surprise")
    if eps_surprise is not None:
        if eps_surprise > 2.0:  # +200%
            print(f"Warning: Capping extreme positive eps_surprise {eps_surprise:.1%} → 200%")
            validated["eps_surprise"] = 2.0
        elif eps_surprise < -0.50:  # -50%
            print(f"Warning: Capping extreme negative eps_surprise {eps_surprise:.1%} → -50%")
            validated["eps_surprise"] = -0.50

    # Validate earnings_day_return (百分點制: -50.0 ~ +100.0)
    # CRITICAL: pg_client 返回百分點 (6.0 = +6%, not 0.06)
    earnings_day_return = validated.get("earnings_day_return")
    if earnings_day_return is not None:
        if earnings_day_return > 100.0:  # +100%
            print(f"Warning: Capping extreme earnings_day_return {earnings_day_return:.2f}% → +100%")
            validated["earnings_day_return"] = 100.0
        elif earnings_day_return < -50.0:  # -50%
            print(f"Warning: Capping extreme earnings_day_return {earnings_day_return:.2f}% → -50%")
            validated["earnings_day_return"] = -50.0

    # Validate pre_earnings_5d_return (百分點制: -30.0 ~ +50.0)
    # CRITICAL: pg_client 返回百分點 (12.0 = +12%, not 0.12)
    pre_earnings_5d_return = validated.get("pre_earnings_5d_return")
    if pre_earnings_5d_return is not None:
        if pre_earnings_5d_return > 50.0:  # +50%
            print(f"Warning: Capping extreme pre_earnings_5d_return {pre_earnings_5d_return:.2f}% → +50%")
            validated["pre_earnings_5d_return"] = 50.0
        elif pre_earnings_5d_return < -30.0:  # -30%
            print(f"Warning: Capping extreme pre_earnings_5d_return {pre_earnings_5d_return:.2f}% → -30%")
            validated["pre_earnings_5d_return"] = -30.0

    return validated


def _load_sector_map(repo_path: Path) -> Dict[str, str]:
    """Best-effort load and merge all GICS sector maps (NYSE + NASDAQ + MAEC)."""
    candidates = [
        repo_path / "gics_sector_map_nyse.csv",
        repo_path / "gics_sector_map_nasdaq.csv",
        repo_path / "gics_sector_map_maec.csv",
    ]
    import pandas as pd  # Lazy import; included in requirements

    merged: Dict[str, str] = {}
    for csv_path in candidates:
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                cols = {c.lower(): c for c in df.columns}
                ticker_col = cols.get("ticker") or cols.get("symbol")
                sector_col = cols.get("sector") or cols.get("gics_sector")
                if ticker_col and sector_col:
                    for t, s in zip(df[ticker_col], df[sector_col]):
                        if pd.notna(t) and pd.notna(s):
                            merged[str(t).upper()] = str(s)
            except Exception:
                continue
    return merged


def _summarize_financials(financials: Optional[Dict[str, Any]]) -> str:
    """Create a compact string for the main agent prompt."""
    if not financials:
        return "No structured financials supplied."

    parts: List[str] = []
    income = financials.get("income") or []
    balance = financials.get("balance") or []
    cash = financials.get("cashFlow") or []

    def _line(label: str, rows: List[dict], keys: List[str]) -> Optional[str]:
        if not rows:
            return None
        latest = rows[0] if isinstance(rows[0], dict) else {}
        date = (
            latest.get("date")
            or latest.get("calendarYear")
            or latest.get("fillingDate")
            or latest.get("period")
        )
        metrics = []
        for k in keys:
            if k in latest and latest[k] not in (None, ""):
                metrics.append(f"{k}={latest[k]}")
        if not metrics:
            metrics.append("no key metrics detected")
        return f"{label} [{date or 'n/a'}]: " + ", ".join(metrics)

    income_line = _line("Income", income, ["revenue", "netIncome", "eps", "grossProfit"])
    balance_line = _line("Balance", balance, ["totalAssets", "totalLiabilities", "cashAndCashEquivalents"])
    cash_line = _line("CashFlow", cash, ["operatingCashFlow", "freeCashFlow"])

    for ln in (income_line, balance_line, cash_line):
        if ln:
            parts.append(ln)

    return "\n".join(parts) if parts else "Financial statements present but could not summarize."


@contextmanager
def _push_dir(path: Path):
    cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def _resolve_models(main_model: Optional[str], helper_model: Optional[str]) -> Dict[str, Any]:
    """Return sanitized models and matching temperatures for main/helper agents.

    Uses LiteLLM proxy which supports various models. Default to gpt-4o-mini.
    """
    # Default temperature for all models via LiteLLM
    default_temp = 0.7

    # Use environment variable defaults or fall back to gpt-5-mini
    default_main = os.getenv("MAIN_MODEL", "gpt-5-mini")
    default_helper = os.getenv("HELPER_MODEL", "gpt-5-mini")

    chosen_main = main_model if main_model else default_main
    chosen_helper = helper_model if helper_model else default_helper

    return {
        "main_model": chosen_main,
        "main_temperature": default_temp,
        "helper_model": chosen_helper,
        "helper_temperature": default_temp,
    }


def run_single_call_from_context(
    context: Dict[str, Any],
    main_model: Optional[str] = None,
    helper_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the real Agentic RAG pipeline from the external repo for a single earnings call.

    Returns a result dict with at least: prediction, confidence, summary, reasons, raw.
    """
    repo_path = _resolve_repo_path()
    _ensure_sys_path(repo_path)
    cred_path = _credentials_path(repo_path)

    try:
        from agents.mainAgent import MainAgent
        from agents.agent_factory import (
            get_historical_performance_agent,
            get_historical_earnings_agent,
            get_comparative_agent,
        )
    except Exception as exc:  # noqa: BLE001
        raise AgenticRagBridgeError(f"匯入 Agentic RAG 模組失敗：{exc}") from exc

    symbol = (context.get("symbol") or context.get("ticker") or "").upper()
    year = context.get("year")
    quarter = context.get("quarter")
    transcript_text = context.get("transcript_text") or ""
    transcript_date = context.get("transcript_date") or ""

    if not symbol or not year or not quarter:
        raise AgenticRagBridgeError("context 缺少必填欄位：symbol、year、quarter。")

    # LOOKAHEAD PROTECTION: In backtest/live-safe mode, transcript_date is REQUIRED
    # Without it, we can't properly filter historical data and may leak future info
    import os
    lookahead_assertions = os.environ.get("LOOKAHEAD_ASSERTIONS", "").lower() in ("1", "true", "yes", "on")
    if lookahead_assertions and not transcript_date:
        raise AgenticRagBridgeError(
            f"LOOKAHEAD PROTECTION: transcript_date is REQUIRED when LOOKAHEAD_ASSERTIONS=true. "
            f"Symbol={symbol}, Year={year}, Quarter={quarter}. "
            f"Cannot proceed without transcript_date as it would allow data leakage from future periods."
        )

    # ------------------------------------------------------------------
    # Fetch market anchors (eps surprise, earnings day return, pre-earnings momentum)
    # ------------------------------------------------------------------
    market_anchors: Dict[str, Any] = {}
    try:
        import pg_client

        # P0' GATE-2: Get earnings day return FIRST to establish canonical event_date
        # This uses price_analysis table (transcript_id join), which is immune to fiscal year issues
        day_ret = pg_client.get_earnings_day_return(symbol, year, quarter)
        canonical_event_date = None  # Will be used as anchor for EPS surprise

        if day_ret and day_ret.get("pct_change_t") is not None:
            market_anchors["earnings_day_return"] = day_ret.get("pct_change_t")

            # Extract canonical earnings_date from day_ret
            canonical_event_date = day_ret.get("earnings_date")

            # Diagnostic info for P0 verification
            market_anchors["_earnings_day_return_source"] = day_ret.get("source")
            market_anchors["_earnings_date"] = canonical_event_date
            market_anchors["_earnings_day_start"] = day_ret.get("price_start_date")
            market_anchors["_earnings_day_end"] = day_ret.get("price_end_date")

        # P0' GATE-2: Get EPS surprise using canonical event_date as anchor
        # This ensures eps_surprise uses the SAME earnings_date as earnings_day_return
        eps_data = pg_client.get_earnings_surprise(symbol, year, quarter, event_date=canonical_event_date)
        if eps_data:
            market_anchors["eps_surprise"] = eps_data.get("eps_surprise")
            market_anchors["eps_actual"] = eps_data.get("eps_actual")
            market_anchors["eps_estimated"] = eps_data.get("eps_estimated")

            # P0' GATE-2: Add diagnostic fields
            market_anchors["_eps_surprise_date"] = eps_data.get("earnings_date")
            market_anchors["_eps_surprise_diff_days"] = eps_data.get("diff_days")
            market_anchors["_eps_surprise_source"] = eps_data.get("eps_surprise_source")

        # Get pre-earnings momentum (5-day)
        # FIX: Normalize transcript_date to YYYY-MM-DD (FMP may return "YYYY-MM-DD HH:MM:SS")
        if transcript_date:
            normalized_date = transcript_date[:10] if len(transcript_date) >= 10 else transcript_date
            momentum = pg_client.get_pre_earnings_momentum(symbol, normalized_date, days=5)
            if momentum:
                market_anchors["pre_earnings_5d_return"] = momentum.get("return_pct")

        # Get market timing (BMO/AMC)
        timing = pg_client.get_market_timing(symbol, year, quarter)
        if timing:
            market_anchors["market_timing"] = timing
    except Exception:
        pass  # Silently continue if market anchors unavailable

    quarter_label = f"{year}-Q{quarter}"
    sector_map = _load_sector_map(repo_path)
    sector = context.get("sector")

    # FMP API fallback: If symbol not in sector_map CSV, query FMP for sector
    if symbol not in sector_map:
        try:
            from fmp_client import get_company_profile
            profile = get_company_profile(symbol)
            if profile and profile.get("sector"):
                sector_map[symbol] = profile["sector"]
                sector = sector or profile["sector"]
        except Exception:
            pass  # Silently fall back to full DB scan if FMP fails

    model_cfg = _resolve_models(main_model, helper_model)

    with _push_dir(repo_path):
        # Use agent factory to get the appropriate agent implementations
        comparative_agent = get_comparative_agent(
            credentials_file=str(cred_path),
            model=model_cfg["helper_model"],
            temperature=model_cfg["helper_temperature"],
            sector_map=sector_map or None,
        )
        financials_agent = get_historical_performance_agent(
            credentials_file=str(cred_path),
            model=model_cfg["helper_model"],
            temperature=model_cfg["helper_temperature"],
        )
        past_calls_agent = get_historical_earnings_agent(
            credentials_file=str(cred_path),
            model=model_cfg["helper_model"],
            temperature=model_cfg["helper_temperature"],
        )
        main_agent = MainAgent(
            credentials_file=str(cred_path),
            model=model_cfg["main_model"],
            temperature=model_cfg["main_temperature"],
            comparative_agent=comparative_agent,
            financials_agent=financials_agent,
            past_calls_agent=past_calls_agent,
        )

        # Extract and annotate facts from transcript
        facts = main_agent.extract(transcript_text)
        for f in facts:
            f.setdefault("ticker", symbol)
            f.setdefault("quarter", quarter_label)

        row = {
            "ticker": symbol,
            "q": quarter_label,
            "transcript": transcript_text,
            "sector": sector,
            "as_of_date": transcript_date[:10] if transcript_date and len(transcript_date) >= 10 else None,
        }
        financials_text = _summarize_financials(context.get("financials"))

        agent_output = main_agent.run(
            facts,
            row,
            mem_txt=None,
            original_transcript=transcript_text,
            financial_statements_facts=financials_text,
            market_anchors=market_anchors if market_anchors else None,
        )

    if not isinstance(agent_output, dict):
        agent_output = {"raw_output": agent_output}

    def _infer_direction(summary: Optional[str]) -> tuple[str, Optional[float]]:
        if not summary:
            return "UNKNOWN", None
        import re

        match = re.search(r"Direction\s*:\s*(\d+)", summary, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            # Updated mapping (prompt_v2 - no NEUTRAL allowed):
            # - Direction >= 6 視為 UP
            # - Direction <= 5 視為 DOWN (Direction 5 now maps to DOWN, not NEUTRAL)
            # This aligns with the prompt instruction to never use Direction 5
            # and lean DOWN when uncertain
            if score >= 6:
                return "UP", score / 10
            # Direction 5 or below maps to DOWN (lean bearish when uncertain)
            return "DOWN", score / 10

        lowered = summary.lower()
        if any(k in lowered for k in ["up", "increase", "growth", "record", "beat"]):
            return "UP", 0.6
        if any(k in lowered for k in ["down", "decline", "miss", "pressure", "headwind"]):
            return "DOWN", 0.4
        return "UNKNOWN", None

    def _extract_long_eligible_json(summary: Optional[str]) -> Optional[Dict[str, Any]]:
        """Extract the LongEligible JSON block from the main agent output."""
        if not summary:
            return None
        import re

        # Try to find JSON block in markdown code fence
        json_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", summary)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON block at the end
        json_match = re.search(r'\{\s*"DirectionScore"[\s\S]*?"PricedInRisk"[^}]*\}', summary)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    # =========================================================================
    # Long-only Strategy v3.0 - TWO-TIER ARCHITECTURE
    # =========================================================================
    # Tier 1 (D7 CORE): D7+ with relaxed positives, strict market-confirmation
    # Tier 2 (D6 STRICT): D6 exception layer with very strict filters
    # =========================================================================

    # PricedInRisk thresholds (env-tunable)
    RISK_EPS_MISS_THRESHOLD = float(os.getenv("RISK_EPS_MISS_THRESHOLD", "0"))
    RISK_EARNINGS_DAY_LOW = float(os.getenv("RISK_EARNINGS_DAY_LOW", "-3"))
    RISK_PRE_RUNUP_HIGH = float(os.getenv("RISK_PRE_RUNUP_HIGH", "15"))
    RISK_PRE_RUNUP_LOW = float(os.getenv("RISK_PRE_RUNUP_LOW", "5"))

    # -------------------------------------------------------------------------
    # TIER 1: D7 CORE (主幹層 - Direction >= 7)
    # v33 Iteration 1 Settings (2026-01-19 rollback - relaxed)
    # -------------------------------------------------------------------------
    LONG_D7_ENABLED = os.getenv("LONG_D7_ENABLED", "1") == "1"
    LONG_D7_MIN_POSITIVES = int(os.getenv("LONG_D7_MIN_POSITIVES", "0"))  # 不卡 positives
    LONG_D7_MIN_DAY_RET = float(os.getenv("LONG_D7_MIN_DAY_RET", "0.8"))  # RELAXED from 1.0 to 0.8
    LONG_D7_REQUIRE_EPS_POS = os.getenv("LONG_D7_REQUIRE_EPS_POS", "0") == "1"  # DISABLED (allow sandbagging)

    # -------------------------------------------------------------------------
    # TIER 2: D6 STRICT EXCEPTION (補 coverage 層 - Direction == 6)
    # v33 Iteration 1 Settings (2026-01-19 rollback)
    # -------------------------------------------------------------------------
    LONG_D6_ENABLED = os.getenv("LONG_D6_ENABLED", "1") == "1"
    LONG_D6_MIN_EPS_SURPRISE = float(os.getenv("LONG_D6_MIN_EPS_SURPRISE", "0.02"))  # eps >= 2%
    LONG_D6_MIN_POSITIVES = int(os.getenv("LONG_D6_MIN_POSITIVES", "0"))  # positives >= 0 (P1-A fix, aligned with D7)
    LONG_D6_MIN_DAY_RET = float(os.getenv("LONG_D6_MIN_DAY_RET", "0.5"))  # earnings_day >= 0.5%
    LONG_D6_REQUIRE_LOW_RISK = os.getenv("LONG_D6_REQUIRE_LOW_RISK", "0") == "1"  # DISABLED (v33 Iter 1)
    LONG_D6_ALLOW_MEDIUM_WITH_DAY = os.getenv("LONG_D6_ALLOW_MEDIUM_WITH_DAY", "0") == "1"  # allow medium if day>=0
    LONG_D6_EXCLUDE_SECTORS = os.getenv("LONG_D6_EXCLUDE_SECTORS", "").split(",") if os.getenv("LONG_D6_EXCLUDE_SECTORS") else []  # NO EXCLUSIONS (v33 Iter 1)

    # -------------------------------------------------------------------------
    # TIER 5: D3 WIDE (Direction >= 3, relaxed tier)
    # P1-C (2026-01-20): DISABLED to reduce signal rate
    # -------------------------------------------------------------------------
    LONG_D3_ENABLED = os.getenv("LONG_D3_ENABLED", "0") == "1"  # P1-C: disabled (signal quality insufficient)

    # -------------------------------------------------------------------------
    # Sector-specific rules (apply to both tiers)
    # -------------------------------------------------------------------------
    LONG_SECTOR_TIGHTEN_ENERGY = os.getenv("LONG_SECTOR_TIGHTEN_ENERGY", "1") == "1"
    LONG_ENERGY_MIN_EPS = float(os.getenv("LONG_ENERGY_MIN_EPS", "0.05"))
    LONG_ENERGY_MIN_DAY_RET = float(os.getenv("LONG_ENERGY_MIN_DAY_RET", "2.0"))

    LONG_SECTOR_TIGHTEN_BASIC_MATERIALS = os.getenv("LONG_SECTOR_TIGHTEN_BASIC_MATERIALS", "1") == "1"
    LONG_BASIC_MATERIALS_MIN_DAY_RET = float(os.getenv("LONG_BASIC_MATERIALS_MIN_DAY_RET", "2.0"))
    LONG_EXCLUDE_BASIC_MATERIALS = os.getenv("LONG_EXCLUDE_BASIC_MATERIALS", "0") == "1"

    def _compute_risk_from_anchors(anchors: Optional[Dict[str, Any]]) -> str:
        """Compute PricedInRisk from market anchors (code-based, not LLM)."""
        if not anchors:
            return "medium"  # Default if no anchors

        eps_surprise = anchors.get("eps_surprise")
        earnings_day_return = anchors.get("earnings_day_return")
        pre_earnings_5d_return = anchors.get("pre_earnings_5d_return")

        # High risk conditions (any one triggers)
        if eps_surprise is not None and eps_surprise <= RISK_EPS_MISS_THRESHOLD:
            return "high"
        if earnings_day_return is not None and earnings_day_return < RISK_EARNINGS_DAY_LOW:
            return "high"
        if pre_earnings_5d_return is not None and pre_earnings_5d_return > RISK_PRE_RUNUP_HIGH:
            return "high"

        # Low risk conditions (all must be true)
        eps_ok = eps_surprise is None or eps_surprise > 0
        day_ok = earnings_day_return is None or earnings_day_return > 0
        runup_ok = pre_earnings_5d_return is None or pre_earnings_5d_return < RISK_PRE_RUNUP_LOW

        if eps_ok and day_ok and runup_ok:
            return "low"

        return "medium"

    # =========================================================================
    # Phase 2: Round 7 New Veto Detection Functions
    # Added: 2026-01-19
    # =========================================================================

    def detect_severe_margin_compression(
        long_json: Optional[Dict[str, Any]],
        agent_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Detect severe margin compression (>500bps YoY decline).

        Added: ChatGPT Pro Round 7 (Phase 2)

        Args:
            long_json: LongEligible JSON with MarginWeakness flag
            agent_results: Agent results with margin analysis

        Returns:
            True if severe margin compression detected (hard veto)
        """
        if not long_json:
            return False

        # Check if MarginWeakness flag is set
        margin_weak = str(long_json.get("MarginWeakness", "NO")).upper() == "YES"
        if not margin_weak:
            return False

        # If available, check agent results for magnitude
        # TODO: Parse agent results for margin compression magnitude
        # For now, conservatively require explicit detection in facts
        if agent_results:
            main_result = agent_results.get("main", {})
            facts = main_result.get("facts", [])

            # Look for margin compression facts with magnitude > 500bps
            for fact in facts:
                if isinstance(fact, dict):
                    category = fact.get("category", "").lower()
                    text = fact.get("text", "").lower()

                    if "margin" in category or "margin" in text:
                        # Check for severe compression indicators
                        if any(keyword in text for keyword in ["severe", "collapse", "compression", ">500", ">5%"]):
                            return True

        return False

    def detect_regulatory_risk(
        agent_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Detect regulatory investigations or compliance violations.

        Added: ChatGPT Pro Round 7 (Phase 2)

        Args:
            agent_results: Agent results with regulatory analysis

        Returns:
            True if regulatory risk detected (hard veto)
        """
        if not agent_results:
            return False

        # Check main agent facts for regulatory keywords
        main_result = agent_results.get("main", {})
        facts = main_result.get("facts", [])

        regulatory_keywords = [
            "investigation", "sec investigation", "doj investigation",
            "regulatory", "compliance violation", "lawsuit", "litigation",
            "fine", "penalty", "settlement", "probe", "inquiry"
        ]

        for fact in facts:
            if isinstance(fact, dict):
                text = fact.get("text", "").lower()
                category = fact.get("category", "").lower()

                if any(keyword in text or keyword in category for keyword in regulatory_keywords):
                    return True

        return False

    def detect_executive_turnover(
        agent_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Detect CEO departure or key executive turnover.

        Added: ChatGPT Pro Round 7 (Phase 2)

        Args:
            agent_results: Agent results with management analysis

        Returns:
            True if critical executive turnover detected (hard veto)
        """
        if not agent_results:
            return False

        # Check main agent facts for executive turnover keywords
        main_result = agent_results.get("main", {})
        facts = main_result.get("facts", [])

        turnover_keywords = [
            "ceo departure", "ceo resign", "ceo stepped down", "ceo left",
            "cfo departure", "cfo resign", "cfo left",
            "executive departure", "management turnover", "leadership change"
        ]

        for fact in facts:
            if isinstance(fact, dict):
                text = fact.get("text", "").lower()
                category = fact.get("category", "").lower()

                if any(keyword in text or keyword in category for keyword in turnover_keywords):
                    return True

        return False

    def detect_hidden_guidance_cut(
        agent_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Detect subtle/hidden guidance reduction without explicit cut.

        Added: ChatGPT Pro Round 7 (Phase 2)

        Args:
            agent_results: Agent results with guidance analysis

        Returns:
            True if hidden guidance cut detected (soft veto, 0.88x)
        """
        if not agent_results:
            return False

        # Check main agent and historical earnings agent for hidden guidance signals
        main_result = agent_results.get("main", {})
        hist_result = agent_results.get("historical_earnings", {})

        facts = main_result.get("facts", []) + hist_result.get("facts", [])

        hidden_cut_keywords = [
            "cautious outlook", "tempered expectation", "lowered visibility",
            "reduced visibility", "uncertain outlook", "challenging environment",
            "headwinds", "macro uncertainty", "softer guidance", "below consensus"
        ]

        for fact in facts:
            if isinstance(fact, dict):
                text = fact.get("text", "").lower()
                category = fact.get("category", "").lower()

                if "guidance" in text or "outlook" in text or "forecast" in text:
                    if any(keyword in text for keyword in hidden_cut_keywords):
                        return True

        return False

    def detect_neutral_veto(
        long_json: Optional[Dict[str, Any]] = None,
        agent_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Detect neutral/uncertain signals that warrant caution.

        Added: ChatGPT Pro Round 7 (Phase 2)

        Args:
            long_json: LongEligible JSON
            agent_results: Agent results

        Returns:
            True if neutral veto detected (soft veto, 0.95x)
        """
        if not agent_results:
            return False

        # Check for low confidence or neutral tone
        main_result = agent_results.get("main", {})
        confidence = main_result.get("confidence", 1.0)

        # Low confidence (<0.4) suggests uncertainty
        if confidence < 0.4:
            return True

        # Check for neutral/uncertain language in facts
        facts = main_result.get("facts", [])
        neutral_keywords = [
            "uncertain", "unclear", "mixed signal", "conflicting",
            "neutral", "in-line", "as expected", "no surprise"
        ]

        neutral_count = 0
        for fact in facts:
            if isinstance(fact, dict):
                text = fact.get("text", "").lower()
                if any(keyword in text for keyword in neutral_keywords):
                    neutral_count += 1

        # If >30% of facts are neutral, apply neutral veto
        if len(facts) > 0 and neutral_count / len(facts) > 0.3:
            return True

        return False

    def _compute_counts_from_booleans(
        long_json: Optional[Dict[str, Any]],
        agent_results: Optional[Dict[str, Any]] = None
    ) -> tuple[int, int, int]:
        """Compute HardPositivesCount, HardVetoCount, SoftVetoCount from boolean fields.

        Updated: ChatGPT Pro Round 7 (Phase 2) - Added new hard vetoes
        - Hard vetoes (always block): GuidanceCut, SevereMarginCompression, RegulatoryRisk, ExecutiveTurnover
        - Soft vetoes (reduce size): DemandSoftness, MarginWeakness, VisibilityWorsening, CashBurn, HiddenGuidanceCut, NeutralVeto

        Returns: (positives, hard_vetoes, soft_vetoes)
        """
        if not long_json:
            return 0, 2, 3  # No positives, max hard vetoes, max soft vetoes

        positive_fields = ["GuidanceRaised", "DemandAcceleration", "MarginExpansion", "FCFImprovement", "VisibilityImproving"]

        # Hard vetoes: structural risk, always block
        # Round 7: Added SevereMarginCompression, RegulatoryRisk, ExecutiveTurnover
        hard_veto_fields = ["GuidanceCut"]

        # Soft vetoes: reduce position size but don't block
        soft_veto_fields = ["DemandSoftness", "MarginWeakness", "VisibilityWorsening", "CashBurn"]

        positives = sum(1 for f in positive_fields if str(long_json.get(f, "NO")).upper() == "YES")
        hard_vetoes = sum(1 for f in hard_veto_fields if str(long_json.get(f, "NO")).upper() == "YES")
        soft_vetoes = sum(1 for f in soft_veto_fields if str(long_json.get(f, "NO")).upper() == "YES")

        # Round 7: Check new hard vetoes from agent results
        if agent_results:
            if detect_severe_margin_compression(long_json, agent_results):
                hard_vetoes += 1
            if detect_regulatory_risk(agent_results):
                hard_vetoes += 1
            if detect_executive_turnover(agent_results):
                hard_vetoes += 1

            # Round 7: Check new soft vetoes
            if detect_hidden_guidance_cut(agent_results):
                soft_vetoes += 1
            if detect_neutral_veto(long_json, agent_results):
                soft_vetoes += 1

        return positives, hard_vetoes, soft_vetoes

    def _compute_detailed_vetoes(
        long_json: Optional[Dict[str, Any]],
        agent_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compute detailed veto information with veto-specific penalties.

        Added: ChatGPT Pro Round 7 (Phase 2)

        Returns:
            {
                "hard_vetoes": List[str],  # List of hard veto names
                "soft_vetoes": Dict[str, float],  # {veto_name: penalty_multiplier}
                "total_soft_veto_multiplier": float  # Combined multiplier
            }
        """
        if not long_json:
            return {
                "hard_vetoes": [],
                "soft_vetoes": {},
                "total_soft_veto_multiplier": 1.0
            }

        hard_vetoes = []
        soft_vetoes = {}

        # Hard vetoes
        if str(long_json.get("GuidanceCut", "NO")).upper() == "YES":
            hard_vetoes.append("GuidanceCut")

        if agent_results:
            if detect_severe_margin_compression(long_json, agent_results):
                hard_vetoes.append("SevereMarginCompression")
            if detect_regulatory_risk(agent_results):
                hard_vetoes.append("RegulatoryRisk")
            if detect_executive_turnover(agent_results):
                hard_vetoes.append("ExecutiveTurnover")

        # Soft vetoes with Round 7/10 updated penalties
        if str(long_json.get("DemandSoftness", "NO")).upper() == "YES":
            soft_vetoes["DemandSoftness"] = 0.88  # Round 10: 0.85 → 0.88

        if str(long_json.get("MarginWeakness", "NO")).upper() == "YES":
            # Variable penalty based on magnitude (TODO: parse from agent results)
            # For now, use conservative 0.90x
            soft_vetoes["MarginWeakness"] = 0.90  # Could be 0.95x if <300bps

        if str(long_json.get("VisibilityWorsening", "NO")).upper() == "YES":
            soft_vetoes["VisibilityWorsening"] = 0.92  # Round 7: new penalty

        if str(long_json.get("CashBurn", "NO")).upper() == "YES":
            soft_vetoes["CashBurn"] = 0.90  # Keep existing

        if agent_results:
            if detect_hidden_guidance_cut(agent_results):
                soft_vetoes["HiddenGuidanceCut"] = 0.88  # Round 7: new veto

            if detect_neutral_veto(long_json, agent_results):
                soft_vetoes["NeutralVeto"] = 0.95  # Round 7: new veto

        # Compute total multiplier
        total_multiplier = 1.0
        for penalty in soft_vetoes.values():
            total_multiplier *= penalty

        return {
            "hard_vetoes": hard_vetoes,
            "soft_vetoes": soft_vetoes,
            "total_soft_veto_multiplier": total_multiplier
        }

    def _compute_trade_long(
        long_json: Optional[Dict[str, Any]],
        sector: Optional[str] = None,
        market_anchors: Optional[Dict[str, Any]] = None,
        agent_results: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str, str, str, int]:
        """Compute trade_long based on THREE-TIER LongEligible criteria (v3.1 ChatGPT Pro Round 1).

        Updated: ChatGPT Pro Round 7 (Phase 2) - Added agent_results for new veto detection

        Returns: (trade_long: bool, risk_code: str, block_reason: str, tier: str, soft_veto_count: int)

        THREE-TIER ARCHITECTURE (ChatGPT Pro Round 1):
        - Tier 1 (D7_CORE): Direction>=7, hard_veto=0, soft_veto<=1, 100% size
        - Tier 2 (D6_STRICT): Direction==6, hard_veto=0, soft_veto<=2, 75% size, non-Tech
        - Tier 3 (D5_GATED): Direction>=5, hard_veto=0, soft_veto<=1, 50% size (NEW)

        Hard vetoes (always block): GuidanceCut, CashBurn
        Soft vetoes (reduce size 0.85x each): DemandSoftness, MarginWeakness, VisibilityWorsening
        """
        if not long_json:
            return False, "unknown", "NO_JSON", "", 0

        try:
            direction_score = int(long_json.get("DirectionScore", 0))

            # Compute counts from booleans (Round 7: pass agent_results for new veto detection)
            hard_positives_count, hard_veto_count, soft_veto_count = _compute_counts_from_booleans(long_json, agent_results)

            # Compute risk from market anchors (not trusting LLM PricedInRisk)
            computed_risk = _compute_risk_from_anchors(market_anchors)

            # Extract market anchor values
            eps_surprise = market_anchors.get("eps_surprise") if market_anchors else None
            earnings_day_ret = market_anchors.get("earnings_day_return") if market_anchors else None

            # Normalize sector for comparison
            sector_lower = (sector or "").lower()
            is_energy = "energy" in sector_lower
            is_basic_materials = "basic materials" in sector_lower or "materials" in sector_lower

            # Check if sector is in D6 exclude list
            sector_in_d6_exclude = any(
                excl.strip().lower() in sector_lower
                for excl in LONG_D6_EXCLUDE_SECTORS if excl.strip()
            )

            # =================================================================
            # GLOBAL GATING (applies to all tiers)
            # =================================================================
            if computed_risk == "high":
                return False, computed_risk, "HIGH_RISK", "", soft_veto_count

            # Hard vetoes always block (GuidanceCut, CashBurn)
            if hard_veto_count > 0:
                return False, computed_risk, "HARD_VETOES", "", soft_veto_count

            # =================================================================
            # SECTOR-SPECIFIC TIGHTENING (applies before tier logic)
            # =================================================================
            # Energy sector: require EPS >= 0.05, earnings_day >= 2%
            if is_energy and LONG_SECTOR_TIGHTEN_ENERGY:
                if eps_surprise is None or eps_surprise < LONG_ENERGY_MIN_EPS:
                    return False, computed_risk, "ENERGY_EPS_LOW", "", soft_veto_count
                if earnings_day_ret is None or earnings_day_ret < LONG_ENERGY_MIN_DAY_RET:
                    return False, computed_risk, "ENERGY_DAY_RET_LOW", "", soft_veto_count

            # Basic Materials: exclude entirely OR require earnings_day >= 2%
            if is_basic_materials:
                if LONG_EXCLUDE_BASIC_MATERIALS:
                    return False, computed_risk, "BASIC_MATERIALS_EXCLUDED", "", soft_veto_count
                if LONG_SECTOR_TIGHTEN_BASIC_MATERIALS:
                    if earnings_day_ret is None or earnings_day_ret < LONG_BASIC_MATERIALS_MIN_DAY_RET:
                        return False, computed_risk, "BASIC_MATERIALS_DAY_RET_LOW", "", soft_veto_count

            # =================================================================
            # TIER 0: D8_MEGA (Exceptional surprises) - ChatGPT Pro Round 8
            # Added: 2026-01-19 (Phase 3)
            # DISABLED 2026-01-19: Rolled back to v33 Iteration 1
            # =================================================================
            # if direction_score >= 7 and LONG_D7_ENABLED:
            #     # D8_MEGA: Exceptional earnings surprise (>20%)
            #     # Overrides sector blocks and relaxes veto requirements
            #     if eps_surprise is not None and eps_surprise > 0.20:
            #         # Allow even with sector blocks
            #         # Allow up to 2 soft vetoes (exceptional case)
            #         if soft_veto_count <= 2:
            #             # Minimal positives check
            #             if hard_positives_count >= LONG_D7_MIN_POSITIVES:
            #                 # earnings_day >= threshold
            #                 if earnings_day_ret is not None and earnings_day_ret >= LONG_D7_MIN_DAY_RET:
            #                     return True, computed_risk, "", "D8_MEGA", soft_veto_count

            # =================================================================
            # TIER 1: D7 CORE (Direction >= 7, soft_veto <= 1, eps > 12%)
            # Updated: ChatGPT Pro Round 8 + Round 10 (Phase 3)
            # =================================================================
            if direction_score >= 7 and LONG_D7_ENABLED:
                # Round 10: EPS surprise requirement increased from 10% to 12%
                eps_surprise_threshold = 0.12  # Round 10 adjustment

                # Standard gate: D7 with ≤1 soft veto and eps_surprise > 12%
                if soft_veto_count <= 1:
                    # D7 不卡 positives (or minimal)
                    if hard_positives_count < LONG_D7_MIN_POSITIVES:
                        return False, computed_risk, "D7_POSITIVES_LOW", "", soft_veto_count

                    # Round 8: EPS surprise > 12% required (Round 10 adjustment)
                    if eps_surprise is None:
                        return False, computed_risk, "D7_EPS_MISSING", "", soft_veto_count
                    if eps_surprise <= eps_surprise_threshold:
                        return False, computed_risk, "D7_EPS_NOT_SUFFICIENT", "", soft_veto_count

                    # earnings_day >= threshold
                    if earnings_day_ret is None or earnings_day_ret < LONG_D7_MIN_DAY_RET:
                        return False, computed_risk, "D7_DAY_RET_LOW", "", soft_veto_count

                    # Round 8: Conditional sector block override (strong surprise >15% overrides)
                    # Check sector blocks, but allow if eps_surprise > 15%
                    # (D7_BLOCKED_SECTORS defined elsewhere, typically ["Real Estate"])
                    # Note: This is implicit - if we reached here, no block applied

                    # D7 CORE passed!
                    return True, computed_risk, "", "D7_CORE", soft_veto_count

                # Round 8: Relaxed gate for strong surprises (≤2 soft vetoes if eps > 15%)
                if soft_veto_count <= 2:
                    if eps_surprise is not None and eps_surprise > 0.15:
                        # Relaxed positives check
                        if hard_positives_count >= LONG_D7_MIN_POSITIVES:
                            # earnings_day >= threshold
                            if earnings_day_ret is not None and earnings_day_ret >= LONG_D7_MIN_DAY_RET:
                                # D7 CORE passed with relaxed gate!
                                return True, computed_risk, "", "D7_CORE", soft_veto_count

            # =================================================================
            # TIER 2: D6 STRICT EXCEPTION (Direction == 6, soft_veto <= 1, eps > 5%)
            # Updated: ChatGPT Pro Round 8 (Phase 3)
            # =================================================================
            if direction_score == 6 and LONG_D6_ENABLED:
                # D6: allow at most 1 soft veto (Round 8: tightened from 2 to 1)
                if soft_veto_count > 1:
                    return False, computed_risk, "D6_TOO_MANY_SOFT_VETOES", "", soft_veto_count

                # Round 8: Conditional sector exclusion (override if eps > 15%)
                if sector_in_d6_exclude:
                    # Allow override if strong eps surprise
                    if eps_surprise is None or eps_surprise <= 0.15:
                        return False, computed_risk, "D6_SECTOR_EXCLUDED", "", soft_veto_count
                    # Otherwise, continue (sector block overridden)

                # Risk check: require low (or allow medium with day>=0)
                if LONG_D6_REQUIRE_LOW_RISK:
                    if computed_risk != "low":
                        if LONG_D6_ALLOW_MEDIUM_WITH_DAY and computed_risk == "medium":
                            if earnings_day_ret is None or earnings_day_ret < 0:
                                return False, computed_risk, "D6_MEDIUM_DAY_NEG", "", soft_veto_count
                        else:
                            return False, computed_risk, "D6_RISK_NOT_LOW", "", soft_veto_count

                # Round 8: EPS surprise >= 5% required
                eps_surprise_threshold = 0.05
                if eps_surprise is None:
                    return False, computed_risk, "D6_EPS_MISSING", "", soft_veto_count
                if eps_surprise < eps_surprise_threshold:
                    return False, computed_risk, "D6_EPS_TOO_SMALL", "", soft_veto_count

                # Positives >= 2 (stricter than D7)
                if hard_positives_count < LONG_D6_MIN_POSITIVES:
                    return False, computed_risk, "D6_POSITIVES_LOW", "", soft_veto_count

                # earnings_day >= threshold
                if earnings_day_ret is None or earnings_day_ret < LONG_D6_MIN_DAY_RET:
                    return False, computed_risk, "D6_DAY_RET_LOW", "", soft_veto_count

                # D6 STRICT passed!
                return True, computed_risk, "", "D6_STRICT", soft_veto_count

            # =================================================================
            # TIER 3: D5 GATED (Direction >= 5, soft_veto <= 2)
            # ChatGPT Pro Round 2: Loosened from soft<=1 to soft<=2 so it can fire
            # =================================================================
            if direction_score >= 5:
                # D5: allow at most 2 soft vetoes (ChatGPT Pro Round 2)
                if soft_veto_count > 2:
                    return False, computed_risk, "D5_TOO_MANY_SOFT_VETOES", "", soft_veto_count

                # D5 requires at least 1 positive
                if hard_positives_count < 1:
                    return False, computed_risk, "D5_POSITIVES_LOW", "", soft_veto_count

                # D5 requires low or medium risk (not high)
                if computed_risk == "high":
                    return False, computed_risk, "D5_HIGH_RISK", "", soft_veto_count

                # D5 requires positive EPS surprise
                if eps_surprise is None or eps_surprise <= 0:
                    return False, computed_risk, "D5_EPS_NOT_POS", "", soft_veto_count

                # D5 GATED passed!
                return True, computed_risk, "", "D5_GATED", soft_veto_count

            # =================================================================
            # TIER 4: D4 ENTRY (Direction == 4, strict gates)
            # Updated: ChatGPT Pro Round 8 (Phase 3)
            # - soft <= 1
            # - positives >= 2 OR EPS >= 8% (Round 8: increased from 2%)
            # =================================================================
            if direction_score >= 4:
                # D4_ENTRY: Allow at most 1 soft veto
                d4_entry_soft_ok = soft_veto_count <= 1

                # Round 8: D4_ENTRY requires confirmation with higher EPS threshold
                has_positives = hard_positives_count >= 2
                has_strong_eps = eps_surprise is not None and eps_surprise >= 0.08  # Round 8: 2% → 8%
                d4_entry_confirm_ok = has_positives or has_strong_eps

                # D4_ENTRY requires low or medium risk
                d4_entry_risk_ok = computed_risk != "high"

                if d4_entry_soft_ok and d4_entry_confirm_ok and d4_entry_risk_ok:
                    # D4 ENTRY passed!
                    return True, computed_risk, "", "D4_ENTRY", soft_veto_count

                # =================================================================
                # TIER 4b: D4_OPP (Direction >= 4, Opportunity tier)
                # P1-D (2026-01-20): TIGHTENED EPS threshold to reduce signal rate
                # v33 Iteration 1 (2026-01-19 rollback - STRENGTHENED)
                # Requirements:
                # - soft <= 2 (more permissive)
                # - EPS >= 5% (P1-D: RAISED from 3%)
                # - Momentum aligned (NEW: day_return must align with direction)
                # - Not high risk
                # =================================================================
                d4_opp_soft_ok = soft_veto_count <= 2

                # P1-D: TIGHTENED EPS surprise must be >= 5% (was 3%)
                d4_opp_eps_ok = eps_surprise is not None and eps_surprise >= 0.05

                # NEW: Momentum alignment check
                d4_opp_momentum_ok = True
                if direction_score >= 5:
                    # For D5+, day return should be positive
                    if earnings_day_ret is not None and earnings_day_ret < 0:
                        d4_opp_momentum_ok = False
                elif direction_score == 4:
                    # For D4, day return should not be very negative
                    if earnings_day_ret is not None and earnings_day_ret < -1.0:
                        d4_opp_momentum_ok = False

                d4_opp_risk_ok = computed_risk != "high"

                if d4_opp_soft_ok and d4_opp_eps_ok and d4_opp_momentum_ok and d4_opp_risk_ok:
                    # D4_OPP passed!
                    return True, computed_risk, "", "D4_OPP", soft_veto_count

                # Return most specific block reason
                if not d4_entry_soft_ok and not d4_opp_soft_ok:
                    return False, computed_risk, "D4_TOO_MANY_SOFT_VETOES", "", soft_veto_count
                if not d4_entry_risk_ok:
                    return False, computed_risk, "D4_HIGH_RISK", "", soft_veto_count
                return False, computed_risk, "D4_NO_CONFIRMATION", "", soft_veto_count

            # =================================================================
            # TIER 5: D3 WIDE (Direction >= 3, relaxed confirmations)
            # P1-C (2026-01-20): DISABLED - signal quality insufficient
            # ChatGPT Pro Round 5: Relaxed gates from 3/3% to 2/2%
            # - Requires: soft=0, (positives>=2 OR EPS>=2%), no HIGH_RISK
            # =================================================================
            if direction_score >= 3 and LONG_D3_ENABLED:  # P1-C: check if D3 enabled
                # D3: NO soft vetoes allowed (strictest confirmation)
                if soft_veto_count > 0:
                    return False, computed_risk, "D3_HAS_SOFT_VETOES", "", soft_veto_count

                # D3 requires no high risk
                if computed_risk == "high":
                    return False, computed_risk, "D3_HIGH_RISK", "", soft_veto_count

                # D3 requires confirmation: 2+ positives OR EPS>=2% (Round 5: relaxed from 3/3%)
                has_strong_positives = hard_positives_count >= 2
                has_strong_eps = eps_surprise is not None and eps_surprise >= 0.02
                if not (has_strong_positives or has_strong_eps):
                    return False, computed_risk, "D3_NO_CONFIRMATION", "", soft_veto_count

                # D3 WIDE passed!
                return True, computed_risk, "", "D3_WIDE", soft_veto_count

            # =================================================================
            # Direction too low (< 3) - ChatGPT Pro Round 4: lowered from 4 to 3
            # =================================================================
            if direction_score < 3:
                return False, computed_risk, "DIR_TOO_LOW", "", soft_veto_count

            return False, computed_risk, "TIER_NOT_MATCHED", "", soft_veto_count

        except (ValueError, TypeError):
            return False, "unknown", "EXCEPTION", "", 0

    notes = agent_output.get("notes") or {}

    def _keep(val: Optional[str]) -> Optional[str]:
        if not val:
            return None
        normalized = str(val).strip()
        if normalized.lower() in {"n/a", "na", "none"}:
            return None
        return normalized

    reasons = [
        f"financials: {notes.get('financials')}" if _keep(notes.get("financials")) else None,
        f"past calls: {notes.get('past')}" if _keep(notes.get("past")) else None,
        f"peers: {notes.get('peers')}" if _keep(notes.get("peers")) else None,
    ]
    reasons = [r for r in reasons if r]

    if not reasons:
        # Fallback：取前 3 條提取的事實做理由摘要
        top_facts = facts[:3]
        for f in top_facts:
            metric = f.get("metric") or "metric"
            val = f.get("value") or ""
            ctx = f.get("context") or f.get("reason") or ""
            reasons.append(f"{metric}: {val} {ctx}".strip())

    prediction, confidence = _infer_direction(agent_output.get("summary"))

    # Extract LongEligible JSON and compute trade_long (returns 5-tuple with tier and soft_veto_count)
    # Round 7: Pass agent_output for new veto detection
    long_eligible_json = _extract_long_eligible_json(agent_output.get("summary"))
    trade_long, risk_code, long_block_reason, trade_long_tier, soft_veto_count = _compute_trade_long(
        long_eligible_json, sector, market_anchors, agent_output
    )

    # Compute counts for CSV output (code-based, not LLM)
    # Round 7: Pass agent_output for new veto detection
    computed_positives, computed_hard_vetoes, computed_soft_vetoes = _compute_counts_from_booleans(
        long_eligible_json, agent_output
    )

    # Round 7: Compute detailed veto information for veto-specific penalties
    detailed_vetoes = _compute_detailed_vetoes(long_eligible_json, agent_output)

    meta = agent_output.setdefault("metadata", {})
    meta.setdefault(
        "models",
        {
            "main": model_cfg["main_model"],
            "helpers": model_cfg["helper_model"],
            "main_temperature": model_cfg["main_temperature"],
            "helper_temperature": model_cfg["helper_temperature"],
        },
    )

    return {
        "prediction": prediction,
        "confidence": confidence,
        "summary": agent_output.get("summary"),
        "reasons": reasons,
        "raw": agent_output,
        "trade_long": trade_long,
        "long_eligible_json": long_eligible_json,
        # New fields for CSV output and offline grid search
        "risk_code": risk_code,
        "long_block_reason": long_block_reason,  # Why trade was blocked (empty if not blocked)
        "trade_long_tier": trade_long_tier,  # D7_CORE, D6_STRICT, or D5_GATED (empty if not traded)
        "market_anchors": market_anchors,
        "computed_positives": computed_positives,
        "computed_hard_vetoes": computed_hard_vetoes,  # Hard vetoes: GuidanceCut + Round 7 new vetoes
        "computed_soft_vetoes": computed_soft_vetoes,  # Soft vetoes: DemandSoftness, MarginWeakness, VisibilityWorsening + Round 7
        "soft_veto_count": soft_veto_count,  # For position sizing (backwards compat)
        "detailed_vetoes": detailed_vetoes,  # Round 7: Veto-specific penalties
    }


def verify_agentic_repo() -> bool:
    """
    Quick healthcheck: ensure external repo & credentials.json exist and are readable.
    """
    repo_path = _resolve_repo_path()
    _ensure_sys_path(repo_path)
    _credentials_path(repo_path)
    return True
