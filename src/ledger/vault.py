import hashlib
import json
import time
import os
from typing import Dict, Any

LEDGER_PATH = os.getenv("CETI_LEDGER_PATH", "./ledger.jsonl")

def record_verdict(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    timestamp = int(time.time())
    record = {"hash": digest, "timestamp": timestamp, "payload": payload}

    try:
        with open(LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        raise RuntimeError(f"Failed to write verdict to ledger: {e}")

    return f"{digest}:{timestamp}"

def push_to_supabase(payload: Dict[str, Any]) -> bool:
    return False
