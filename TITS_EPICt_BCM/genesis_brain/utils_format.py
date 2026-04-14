# -*- coding: utf-8 -*-
# genesis_brain/utils_format.py
import math

def safe_float(v, default=0.0) -> float:
    """
    Accepts:
      - float/int
      - "0.83"
      - "83%"   -> 0.83
      - None / "" / "N/A" -> default
    Returns: safe float.
    """
    try:
        if v is None:
            return default

        if isinstance(v, (int, float)):
            f = float(v)
            return default if (math.isnan(f) or math.isinf(f)) else f

        if isinstance(v, str):
            s = v.strip()
            if not s or s.lower() in ("n/a", "na", "none", "null"):
                return default
            is_percent = "%" in s
            s = s.replace("%", "").strip()
            f = float(s)
            if is_percent and f > 1.0:
                f /= 100.0
            return default if (math.isnan(f) or math.isinf(f)) else f

        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f

    except Exception:
        return default


def fmt_float(v, places=2, default=0.0) -> str:
    return f"{safe_float(v, default=default):.{places}f}"


def fmt_percent(v, default=0.0) -> str:
    f = safe_float(v, default=default)
    if f > 1.0:
        f /= 100.0
    return f"{f:.0%}"
