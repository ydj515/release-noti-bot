#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Spring Boot / Spring Framework release watcher → Slack notifier (MVP)

- Reads/writes state/last_seen.json to prevent duplicate notifications.
- Fetches GitHub releases via GitHub REST API.
- Extracts key sections from release body (heuristic).
- Sends Slack Incoming Webhook message using Block Kit.

Required env:
  SLACK_WEBHOOK_URL

Optional env:
  GITHUB_TOKEN
  INCLUDE_PRERELEASES (true/false)
  SLACK_SEND_MODE (combined/per_repo)
  GEMINI_API_KEY (optional AI summarization)
  GEMINI_MODEL (optional, default: gemini-1.5-flash)
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


STATE_PATH = os.path.join("state", "last_seen.json")

TARGETS = [
    # (repo_full_name, friendly_name)
    ("spring-projects/spring-boot", "Spring Boot"),
    ("spring-projects/spring-framework", "Spring Framework"),
]

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
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
MAX_RELEASE_BODY_FOR_AI = 6000


@dataclass(frozen=True)
class Release:
    tag_name: str
    name: str
    html_url: str
    body: str
    prerelease: bool
    published_at: Optional[str]


def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def http_get_json(url: str, token: Optional[str] = None) -> Any:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def http_post_json(url: str, payload: Any) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        _ = resp.read()


_semver_re = re.compile(
    r"^v?(?P<maj>\d+)(?:\.(?P<min>\d+))?(?:\.(?P<pat>\d+))?(?P<rest>.*)$"
)

def parse_semver(tag: str) -> Tuple[int, int, int, str]:
    m = _semver_re.match(tag.strip())
    if not m:
        return (0, 0, 0, tag)
    maj = int(m.group("maj") or 0)
    minv = int(m.group("min") or 0)
    pat = int(m.group("pat") or 0)
    rest = (m.group("rest") or "").strip()
    return (maj, minv, pat, rest)


def semver_gt(a: str, b: str) -> bool:
    pa = parse_semver(a)
    pb = parse_semver(b)
    if pa[:3] != pb[:3]:
        return pa[:3] > pb[:3]
    ra, rb = pa[3], pb[3]
    if ra == rb:
        return False
    if ra == "" and rb != "":
        return True
    if ra != "" and rb == "":
        return False
    return ra > rb


def load_state() -> Dict[str, str]:
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            return {}
    return {}


def save_state(state: Dict[str, str]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_latest_release(repo: str, token: Optional[str], include_prereleases: bool) -> Release:
    if include_prereleases:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=10"
        items = http_get_json(url, token=token)
        if not isinstance(items, list) or not items:
            raise RuntimeError(f"No releases found for {repo}")
        chosen = None
        for it in items:
            if not isinstance(it, dict):
                continue
            chosen = it
            break
        if chosen is None:
            raise RuntimeError(f"No usable releases for {repo}")
        it = chosen
    else:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        it = http_get_json(url, token=token)

    return Release(
        tag_name=str(it.get("tag_name") or ""),
        name=str(it.get("name") or ""),
        html_url=str(it.get("html_url") or ""),
        body=str(it.get("body") or ""),
        prerelease=bool(it.get("prerelease") or False),
        published_at=it.get("published_at"),
    )


def summarize_with_gemini(product: str, rel: Release, api_key: str, model: str) -> Optional[str]:
    """Use Gemini to produce a short Slack-ready summary."""
    body = (rel.body or "").strip()
    if not body:
        return None

    if len(body) > MAX_RELEASE_BODY_FOR_AI:
        body = body[:MAX_RELEASE_BODY_FOR_AI]

    prompt = (
        "역할: Slack에 보낼 릴리즈 노트 요약 작성자. 한국어로만 간결하게 작성합니다. 과장/추측/인사말 금지.\n"
        "출력 형식(그대로 사용):\n"
        "Breaking:\n"
        "• ...\n"
        "Deprecated:\n"
        "• ...\n"
        "Features:\n"
        "• ...\n"
        "BugFixes:\n"
        "• ...\n"
        "Dependency:\n"
        "• ...\n"
        "Docs:\n"
        "• ...\n"
        "Notes:\n"
        "• ... (기타 중요 메모가 있을 때만)\n"
        "- 각 섹션에서 항목이 없으면 해당 섹션 줄 자체를 생략합니다.\n"
        "- 모든 bullet은 '• '로 시작하고 120자 이내로 요약합니다.\n"
        "- Breaking/Deprecated/Dependency를 우선적으로 포함하고, 총 bullet은 최대 8개로 제한합니다.\n"
        "- 내용이 정말 없으면 '• 주요 변경점 없음' 한 줄만 반환합니다.\n\n"
        f"제품: {product}\n"
        f"버전: {rel.tag_name}\n"
        f"릴리즈 노트 원문:\n{body}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8")
        parsed = json.loads(data)

    candidates = parsed.get("candidates") or []
    for cand in candidates:
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
        summary = "\n".join(t.strip() for t in texts if isinstance(t, str) and t.strip())
        if summary:
            return summary
    raise RuntimeError("Gemini response missing summary")


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
                # normalize bullet
                collected.append(re.sub(r"^([-*+]\s+|\d+\.\s+)", "• ", t))
            elif len(t) <= 120 and (":" in t or "removed" in t.lower() or "deprecated" in t.lower()):
                collected.append(f"• {t}")

            if len(collected) >= MAX_BULLETS_PER_SECTION:
                break
        out[key] = collected

    return out


def slack_blocks_for_release(
    product: str,
    rel: Release,
    sections: Dict[str, List[str]],
    ai_summary: Optional[str] = None,
) -> List[Dict[str, Any]]:
    title = f"{product} 업데이트: {rel.tag_name}"
    subtitle_bits = []
    if rel.published_at:
        subtitle_bits.append(f"Published: {rel.published_at}")
    if rel.prerelease:
        subtitle_bits.append("Prerelease")
    subtitle = " · ".join(subtitle_bits) if subtitle_bits else ""

    def section_block(name: str, items: List[str]) -> Optional[Dict[str, Any]]:
        if not items:
            return None
        text = "*{name}*\n{body}".format(
            name=name,
            body="\n".join(items[:MAX_BULLETS_PER_SECTION]),
        )
        return {"type": "section", "text": {"type": "mrkdwn", "text": text}}

    blocks: List[Dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": title}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"<{rel.html_url}|Release notes 열기>"}},
    ]
    if subtitle:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": subtitle}]})
    if ai_summary:
        trimmed = ai_summary.strip()
        if trimmed:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*AI 요약 (Gemini)*\n{trimmed[:2700]}"},
                }
            )

    for key, label in [
        ("Breaking", "Breaking"),
        ("Deprecated", "Deprecated"),
        ("Features", "New Features"),
        ("BugFixes", "Bug Fixes"),
        ("Dependency", "Dependency Upgrades"),
        ("Docs", "Documentation"),
        ("Contributors", "Contributors"),
    ]:
        blk = section_block(label, sections.get(key, []))
        if blk:
            blocks.append(blk)

    if not any(sections.get(k) for k in sections):
        excerpt = "\n".join([l for l in rel.body.splitlines() if l.strip()][:8])
        excerpt = excerpt.strip()
        if excerpt:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*요약(원문 일부)*\n```{excerpt[:1200]}```"}})

    blocks.append({"type": "divider"})
    return blocks


def post_to_slack(webhook: str, blocks: List[Dict[str, Any]]) -> None:
    payload = {
        "text": "Spring release update",
        "blocks": blocks,
    }
    http_post_json(webhook, payload)


def main() -> int:
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not slack_webhook:
        print("ERROR: SLACK_WEBHOOK_URL is required (set as GitHub Repo Secret).", file=sys.stderr)
        return 2

    token = os.getenv("GITHUB_TOKEN", "").strip() or None
    include_prereleases = env_bool("INCLUDE_PRERELEASES", False)
    send_mode = (os.getenv("SLACK_SEND_MODE", "combined").strip().lower() or "combined")
    if send_mode not in ("combined", "per_repo"):
        send_mode = "combined"
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip() or None
    gemini_model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL

    state = load_state()
    updated = False

    all_blocks: List[Dict[str, Any]] = []
    pending_posts: List[Tuple[str, List[Dict[str, Any]], str]] = []  # (repo, blocks, tag)
    for repo, product in TARGETS:
        rel = fetch_latest_release(repo, token=token, include_prereleases=include_prereleases)
        if not rel.tag_name:
            continue

        last = state.get(repo)
        is_new = (last is None) or semver_gt(rel.tag_name, last)
        if not is_new:
            print(f"[skip] {product}: latest={rel.tag_name} (already sent)")
            continue

        sections = extract_sections(rel.body or "")
        ai_summary = None
        if gemini_api_key:
            try:
                ai_summary = summarize_with_gemini(product, rel, gemini_api_key, gemini_model)
            except Exception as e:
                print(f"[warn] Gemini summary failed for {product} {rel.tag_name}: {e}", file=sys.stderr)

        blocks = slack_blocks_for_release(product, rel, sections, ai_summary)
        if send_mode == "per_repo":
            pending_posts.append((repo, blocks, rel.tag_name))
        else:
            all_blocks.extend(blocks)
            pending_posts.append((repo, [], rel.tag_name))  # tag tracking only

        updated = True
        print(f"[plan] {product}: {rel.tag_name} (was {last})")

    if not updated:
        print("No new releases to notify.")
        return 0

    # Slack 전송: combined(기본) 또는 per_repo
    if send_mode == "per_repo":
        sent_any = False
        for repo, blocks, tag in pending_posts:
            if not blocks:
                continue
            try:
                post_to_slack(slack_webhook, blocks)
                state[repo] = tag  # 성공적으로 전송됐을 때만 상태 갱신
                sent_any = True
                print(f"[sent] {repo}: {tag}")
            except Exception as e:
                print(f"[error] Slack post failed for {repo} {tag}: {e}", file=sys.stderr)
        if sent_any:
            save_state(state)
            print(f"State saved to {STATE_PATH}")
        else:
            print("No messages were sent.")
        return 0

    # combined 모드: 여러 repo 업데이트를 한 메시지로 묶어서 전송
    try:
        post_to_slack(slack_webhook, all_blocks)
        # 묶어서 보낼 때는 '계획된' repo들의 tag를 상태에 기록
        for repo, _, tag in pending_posts:
            state[repo] = tag
        save_state(state)
        print(f"State saved to {STATE_PATH}")
        return 0
    except Exception as e:
        print(f"[error] Slack post failed (combined): {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
