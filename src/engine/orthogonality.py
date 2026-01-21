import hashlib
from typing import List, Dict


def extract_assumptions(text: str) -> List[str]:
    lines = text.splitlines()
    result = []

    for line in lines:
        s = line.strip().lower()
        if s.startswith(("assume ", "assumption ", "premise ")):
            result.append(s)

    return result


def assumptions_fingerprint(assumptions: List[str]) -> str:
    normalized = sorted(set(a.strip() for a in assumptions))
    data = "\n".join(normalized).encode()
    return hashlib.sha256(data).hexdigest()


def orthogonality_check(justifications: List[str]) -> Dict[str, object]:
    fingerprints = []
    records = []

    for text in justifications:
        assumptions = extract_assumptions(text)
        fp = assumptions_fingerprint(assumptions)
        fingerprints.append(fp)
        records.append({
            "fingerprint": fp,
            "assumptions": assumptions
        })

    unique = set(fingerprints)

    return {
        "passed": len(unique) == len(fingerprints),
        "fingerprints": list(unique),
        "records": records
    }
