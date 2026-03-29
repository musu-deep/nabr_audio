from __future__ import annotations

import re
from typing import List, Tuple


ACTION_MAP = {
    "denoise": [
        r"ضوضاء", r"نظف", r"تنظيف", r"شوشرة", r"noise", r"denoise", r"background",
    ],
    "trim_silence": [
        r"سكتات", r"صمت", r"فراغات", r"احذف الوقفات", r"silence", r"pauses",
    ],
    "trim_edges": [
        r"البداية", r"النهاية", r"قص البداية", r"قص النهاية", r"trim start", r"trim end",
    ],
    "normalize": [
        r"رفع مستوى", r"موازنة", r"تطبيع", r"جهارة", r"loudness", r"normalize", r"volume",
    ],
    "clarity": [
        r"وضوح", r"أوضح", r"clarity", r"clear", r"speech",
    ],
    "podcast_preset": [
        r"بودكاست", r"podcast",
    ],
    "mobile_preset": [
        r"جوال", r"موبايل", r"phone", r"mobile",
    ],
}


DEFAULT_SEQUENCE = ["denoise", "trim_silence", "normalize", "clarity"]


FRIENDLY_NAMES = {
    "denoise": "تقليل ضوضاء الخلفية",
    "trim_silence": "حذف السكتات الطويلة",
    "trim_edges": "قص الصمت من البداية والنهاية",
    "normalize": "موازنة مستوى الصوت",
    "clarity": "تحسين وضوح الكلام",
    "podcast_preset": "تهيئة بودكاست",
    "mobile_preset": "تهيئة تسجيل جوال",
}


def parse_message(message: str) -> Tuple[List[str], str]:
    text = (message or "").strip().lower()
    found: List[str] = []

    for action, patterns in ACTION_MAP.items():
        for p in patterns:
            if re.search(p, text, flags=re.IGNORECASE):
                found.append(action)
                break

    if not found and text:
        found = DEFAULT_SEQUENCE.copy()

    # Expand presets into practical chains
    expanded: List[str] = []
    for action in found:
        if action == "podcast_preset":
            expanded.extend(["denoise", "trim_silence", "normalize", "clarity"])
        elif action == "mobile_preset":
            expanded.extend(["denoise", "normalize", "clarity"])
        else:
            expanded.append(action)

    deduped: List[str] = []
    for action in expanded:
        if action not in deduped:
            deduped.append(action)

    names = [FRIENDLY_NAMES.get(a, a) for a in deduped]
    summary = "سأطبق: " + "، ".join(names) if names else "لم أتعرف على طلب واضح، لكن يمكنني البدء بتنظيف متوازن وتحسين الوضوح."
    return deduped, summary
