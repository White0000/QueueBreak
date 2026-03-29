from __future__ import annotations
import json
from typing import Any, Optional

def try_parse_json(text: str) -> Optional[Any]:
    if text is None:
        return None
    s = text.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        pass
    dec = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch not in "{[":
            continue
        try:
            obj, _end = dec.raw_decode(s[i:])
            return obj
        except Exception:
            continue
    return None
