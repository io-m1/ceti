import hashlib
import json
from pathlib import Path
from datetime import datetime

LEDGER_FILE = Path("ledger.jsonl")
LEDGER_FILE.touch(exist_ok=True)

def ledger_write(ceti_request: dict, ceti_response: dict) -> dict:
    """
    Write the request and response to ledger, including SHA256 transcript hash.
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    entry = {
        "timestamp": timestamp,
        "request": ceti_request,
        "response": ceti_response
    }
    serialized = json.dumps(entry, sort_keys=True)
    transcript_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    entry["transcript_hash"] = transcript_hash

    with LEDGER_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return {"ledger_entry": entry, "transcript_hash": transcript_hash}

def ledger_check(transcript_hash: str) -> dict | None:
    """
    Check if a transcript hash exists in the ledger.
    """
    with LEDGER_FILE.open("r") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("transcript_hash") == transcript_hash:
                return entry
    return None
