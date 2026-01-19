#!/usr/bin/env python3
"""Debug NVDA 2017Q1 error"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ['MAIN_MODEL'] = 'gemini-3-flash-preview'

from agentic_rag_bridge import run_single_call_from_context

test_case = {
    "symbol": "NVDA",
    "year": 2017,
    "quarter": 1,
    "transcript_date": None
}

print("Testing NVDA 2017Q1 with gemini-3-flash-preview...")
try:
    result = run_single_call_from_context(test_case)
    print(f"✅ Success: {result.get('direction_score', 'N/A')}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
