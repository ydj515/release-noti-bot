# -*- coding: utf-8 -*-
import re
from typing import Dict, List

from scripts.config import SECTION_PATTERNS, MAX_BULLETS_PER_SECTION

def extract_sections(markdown: str) -> Dict[str, List[str]]:
    lines = markdown.splitlines()
    out: Dict[str, List[str]] = {
        "Breaking": [],
        "Deprecated": [],
        "Dependency": [],
        "Features": [],
        "BugFixes": [],
        "Docs": [],
        "Contributors": [],
    }

    heading_indices: Dict[str, int] = {}
    for i, line in enumerate(lines):
        for key, pats in SECTION_PATTERNS.items():
            if any(re.match(p, line.strip(), flags=re.IGNORECASE) for p in pats):
                heading_indices[key] = i
                break

    def heading_level(s: str) -> int:
        m = re.match(r"^(#+)\s+", s.strip())
        return len(m.group(1)) if m else 0

    for key, start in heading_indices.items():
        start_level = heading_level(lines[start])
        collected: List[str] = []
        for j in range(start + 1, len(lines)):
            lvl = heading_level(lines[j])
            if lvl and lvl <= start_level:
                break
            t = lines[j].strip()
            if not t:
                continue
            if re.match(r"^[-*+]\s+", t) or re.match(r"^\d+\.\s+", t):
                # 불릿 기호 정규화
                collected.append(re.sub(r"^([-*+]\s+|\d+\.\s+)", "• ", t))
            elif len(t) <= 120 and (":" in t or "removed" in t.lower() or "deprecated" in t.lower()):
                collected.append(f"• {t}")

            if len(collected) >= MAX_BULLETS_PER_SECTION:
                break
        out[key] = collected

    return out
