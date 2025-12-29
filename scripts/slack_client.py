# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from scripts.config import MAX_BULLETS_PER_SECTION
from scripts.models import Release
from scripts.utils import http_post_json

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
                    "text": {"type": "mrkdwn", "text": f"*AI 요약*\n{trimmed[:2700]}"},
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
