import hashlib
import json
import time
from typing import Dict, Any

def record_verdict(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    timestamp = int(time.time())
    return f"{digest}:{timestamp}"
