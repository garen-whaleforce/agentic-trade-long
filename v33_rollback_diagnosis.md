# v33 Rollback - Zero Trade Signals Diagnosis

**Date**: 2026-01-19
**Issue**: 100-sample validation test produced 0% trade signals
**Status**: 🔴 **DATA QUALITY ISSUE IDENTIFIED**

---

## Executive Summary

The zero trade signals are NOT caused by overly strict gates. The root cause is a **data mismatch between transcript dates and earnings surprise dates**.

## Root Cause

### Problem: Transcript Date Mismatch

The `earnings_transcripts` table has incorrect year/quarter labeling:

| Symbol | Label | Transcript Date | Expected Date | Offset |
|--------|-------|----------------|---------------|--------|
| ADSK | 2017Q1 | 2016-05-20 | ~2017-02-xx | **-9 months** |
| CRM | 2017Q1 | 2016-05-18 | ~2017-02-xx | **-9 months** |
| NVDA | 2017Q1 | 2016-05-13 | ~2017-02-xx | **-10 months** |
| BBY | 2017Q1 | 2016-05-24 | ~2017-03-xx | **-9 months** |
| SMCI | 2017Q1 | 2016-10-27 | ~2017-01-xx | **-3 months** |
| JBL | 2017Q1 | 2016-12-15 | ~2017-03-xx | **-3 months** |

### Impact

1. **eps_surprise lookup fails**: The `get_earnings_surprise()` function searches within ±7 days of transcript_date
2. **Transcript dates are in 2016**, but **earnings_surprises are in 2017**
3. **Result**: All eps_surprise values are NULL
4. **Consequence**: All tier gates fail because they require eps_surprise data

```python
# Current logic in pg_client.py (line 913):
cur.execute("""
    SELECT date, eps_actual, eps_estimated, eps_surprise
    FROM earnings_surprises
    WHERE UPPER(symbol) = %s
      AND date BETWEEN %s::date - interval '7 days' AND %s::date + interval '7 days'
    ...
""", (symbol.upper(), transcript_date, transcript_date, transcript_date))
# ❌ This fails because transcript_date is 2016-05-20 but earnings dates are in 2017
```

### Validation Results Evidence

From [backtest_results.json](EarningsCallAgenticRag/backtest_checkpoints/backtest_results.json):

```json
{
  "direction_distribution": {
    "8": 2,    // D8 direction scores exist
    "7": 2,    // D7 direction scores exist
    "6": 10,   // D6 direction scores exist
    ...
  },
  "results": [
    {
      "symbol": "BBY",
      "year": 2017,
      "quarter": 3,
      "direction_score": 8,        // ✅ Strong signal
      "eps_surprise": null,         // ❌ Missing data
      "trade_long": false           // ❌ Blocked
    },
    {
      "symbol": "JBL",
      "year": 2017,
      "quarter": 1,
      "direction_score": 8,         // ✅ Strong signal
      "eps_surprise": null,          // ❌ Missing data
      "trade_long": false            // ❌ Blocked
    }
  ]
}
```

**ALL 100 samples have `"eps_surprise": null`** → **0 trade signals**

---

## Proposed Fixes

### Option A: Widen eps_surprise Matching Window (QUICK FIX)

**Change**: Modify `get_earnings_surprise()` to use ±180 days instead of ±7 days for old data

```python
# pg_client.py line 909
def get_earnings_surprise(symbol: str, year: int, quarter: int) -> Optional[Dict]:
    # ... existing code ...

    # Widen window for pre-2019 data (known labeling issues)
    if transcript_date and transcript_date.year < 2019:
        window_days = 180  # ±6 months for old data
    else:
        window_days = 7    # ±7 days for recent data

    cur.execute("""
        SELECT date, eps_actual, eps_estimated, eps_surprise
        FROM earnings_surprises
        WHERE UPPER(symbol) = %s
          AND date BETWEEN %s::date - interval '%s days' AND %s::date + interval '%s days'
        ORDER BY ABS(date - %s::date)
        LIMIT 1
    """, (symbol.upper(), transcript_date, window_days, transcript_date, window_days, transcript_date))
```

**Pros**:
- Quick fix (single file change)
- Preserves accuracy for recent data (post-2019)
- Allows validation test to proceed

**Cons**:
- May match wrong quarter in edge cases
- Doesn't fix underlying data quality issue

---

### Option B: Match by Quarter Label Instead of Date (PROPER FIX)

**Change**: Match earnings_surprise by year/quarter label, not transcript_date

```python
# pg_client.py
def get_earnings_surprise_by_period(symbol: str, year: int, quarter: int) -> Optional[Dict]:
    """Get EPS surprise by quarter period, not transcript date."""
    with get_cursor() as cur:
        if cur is None:
            return None
        try:
            # Calculate quarter date range
            quarter_start = f"{year}-{(quarter-1)*3+1:02d}-01"
            if quarter == 4:
                quarter_end = f"{year+1}-01-01"
            else:
                quarter_end = f"{year}-{quarter*3+1:02d}-01"

            # Get earnings surprise within the quarter
            cur.execute("""
                SELECT date, eps_actual, eps_estimated, eps_surprise
                FROM earnings_surprises
                WHERE UPPER(symbol) = %s
                  AND date >= %s::date
                  AND date < %s::date
                ORDER BY date
                LIMIT 1
            """, (symbol.upper(), quarter_start, quarter_end))

            surprise_row = cur.fetchone()
            if surprise_row:
                return {
                    "date": str(surprise_row["date"]),
                    "eps_actual": float(surprise_row["eps_actual"]) if surprise_row.get("eps_actual") else None,
                    "eps_estimated": float(surprise_row["eps_estimated"]) if surprise_row.get("eps_estimated") else None,
                    "eps_surprise": float(surprise_row["eps_surprise"]) if surprise_row.get("eps_surprise") else None,
                }
        except Exception as e:
            logger.debug(f"get_earnings_surprise_by_period error: {e}")
    return None
```

**Pros**:
- More accurate for backtesting
- Aligns with how data is labeled
- Cleaner logic

**Cons**:
- Requires more extensive testing
- May not work for fiscal year companies

---

### Option C: Fix Underlying Data (LONG-TERM)

Re-ingest earnings_transcripts with correct fiscal year → calendar year mapping.

**Status**: Out of scope for immediate validation test

---

## Recommended Action

**Implement Option A immediately** to unblock the validation test:

1. Modify `pg_client.py` to widen eps_surprise window for pre-2019 data
2. Re-run 100-sample validation test
3. Expect 15-20% signal rate (vs 0% currently)
4. Proceed with full backtest if validation passes

**Follow-up with Option B** for production deployment.

---

## Data Coverage Stats

```
📊 Earnings Surprise Data Coverage:
  2017: 31,722 records, 9,278 symbols  ✅ Data exists
  2018: 33,179 records, 9,750 symbols  ✅ Data exists
  2019: 36,333 records, 11,560 symbols ✅ Data exists
  2020+: More comprehensive coverage    ✅ Data exists
```

**Conclusion**: The data EXISTS, but the lookup logic can't find it due to date mismatch.

---

## Next Steps

1. ✅ Diagnose root cause (COMPLETE)
2. ⏳ Implement Option A fix
3. ⏳ Re-run 100-sample validation
4. ⏳ Analyze corrected results
5. ⏳ Proceed with 1000-2000 sample test if successful
