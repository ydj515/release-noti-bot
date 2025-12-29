# -*- coding: utf-8 -*-
import os

# 경로 설정
STATE_PATH = os.path.join("state", "last_seen.json")

# GitHub / 제품 대상 설정
TARGETS = [
    ("spring-projects/spring-boot", "Spring Boot"),
    ("spring-projects/spring-framework", "Spring Framework"),
]

# 릴리즈 노트 섹션 정규표현식 패턴
SECTION_PATTERNS = {
    "Breaking": [
        r"^#+\s*Breaking\s+Changes\b",
        r"^#+\s*Breaking\b",
        r"^#+\s*Incompatible\s+Changes\b",
        r"^#+\\s*Changes\\s+in\\s+Behavior\\b",
    ],
    "Deprecated": [
        r"^#+\s*Deprecations?\b",
        r"^#+\s*Deprecated\b",
    ],
    "Dependency": [
        r"^#+\s*:?\w*:\s*Dependency\s+Upgrades?\b",
        r"^#+\s*Dependencies\b",
        r"^#+\s*Upgrades?\b",
        r"^#+\\s*BOM\\s+Updates\\b",
    ],
    "Features": [
        r"^#+\s*:?\w*:\s*New\s+Features\b",
        r"^#+\s*Features\b",
        r"^#+\s*Enhancements?\b",
        r"^#+\s*What'?s\s+New\b",
    ],
    "BugFixes": [
        r"^#+\s*:?\w*:\s*Bug\s+Fixes\b",
        r"^#+\s*Fixes\b",
        r"^#+\s*Bugs\b",
        r"^#+\s*Bugfix(es)?\b",
    ],
    "Docs": [
        r"^#+\s*:?\w*:\s*Documentation\b",
        r"^#+\s*Docs\b",
    ],
    "Contributors": [
        r"^#+\s*:?\w*:\s*Contributors\b",
        r"^#+\s*Thanks\b",
    ],
}

MAX_BULLETS_PER_SECTION = 8

# AI 기본값
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o"
