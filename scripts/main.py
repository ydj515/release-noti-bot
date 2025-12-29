#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Spring Boot / Spring Framework 릴리즈 감시 → 슬랙 알림 (MVP)

- state/last_seen.json을 읽고 써서 중복 알림을 방지합니다.
- GitHub REST API를 통해 GitHub 릴리즈 정보를 가져옵니다.
- 릴리즈 본문에서 주요 섹션을 추출합니다 (휴리스틱 방식).
- Block Kit을 사용하여 슬랙 Incoming Webhook 메시지를 전송합니다.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from scripts.ai_summarizer import AISummarizer, get_summarizer
from scripts.config import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    TARGETS,
)
from scripts.github_client import fetch_latest_release
from scripts.release_parser import extract_sections
from scripts.slack_client import post_to_slack, slack_blocks_for_release
from scripts.utils import env_bool, load_state, save_state, semver_gt, STATE_PATH, load_env_file


def main() -> int:
    # 로컬 실행 시 .env 파일 로드
    load_env_file()

    slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not slack_webhook:
        print("ERROR: SLACK_WEBHOOK_URL is required (set as GitHub Repo Secret).", file=sys.stderr)
        return 2

    # AI 설정 (우선순위 기반, 반복문 처리)
    ai_configs = [
        ("Gemini", "GEMINI_API_KEY", "GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        ("OpenAI", "OPENAI_API_KEY", "OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
    ]

    summarizer: Optional[AISummarizer] = None
    ai_provider_name: str = ""

    for name, key_env, model_env, default_model in ai_configs:
        api_key = os.getenv(key_env, "").strip()
        if not api_key:
            continue

        model = os.getenv(model_env, default_model).strip() or default_model
        try:
            summarizer = get_summarizer(name.lower(), api_key, model)
            if summarizer:
                print(f"[info] Using {name} (model={model})")
                ai_provider_name = name
                break
            else:
                print(f"[warn] {name} summarizer is not yet implemented.", file=sys.stderr)
        except Exception as e:
            print(f"[warn] Failed to initialize {name} summarizer: {e}", file=sys.stderr)

    if not summarizer and any(os.getenv(c[1], "").strip() for c in ai_configs):
        print("[warn] AI API keys found but summarizer initialization failed for all providers.", file=sys.stderr)

    state = load_state()
    updated = False
    send_mode = (os.getenv("SLACK_SEND_MODE", "combined").strip().lower() or "combined")
    if send_mode not in ("combined", "per_repo"):
        send_mode = "combined"

    all_blocks: List[Dict[str, Any]] = []
    pending_posts: List[Tuple[str, List[Dict[str, Any]], str]] = []  # (저장소, 블록목록, 태그)
    
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
        if summarizer:
            try:
                ai_summary = summarizer.summarize(product, rel)
            except Exception as e:
                print(f"[warn] AI summary failed for {product} {rel.tag_name}: {e}", file=sys.stderr)

        blocks = slack_blocks_for_release(product, rel, sections, ai_summary, ai_provider_name)
        if send_mode == "per_repo":
            pending_posts.append((repo, blocks, rel.tag_name))
        else:
            all_blocks.extend(blocks)
            pending_posts.append((repo, [], rel.tag_name))  # 태그 추적만 함

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
