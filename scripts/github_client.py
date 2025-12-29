# -*- coding: utf-8 -*-
from typing import Optional

from scripts.models import Release
from scripts.utils import http_get_json

def fetch_latest_release(repo: str, token: Optional[str] = None, include_prereleases: bool = False) -> Release:
    """
    주어진 저장소의 최신 릴리즈를 가져옵니다.
    include_prereleases가 True이면, 릴리즈 목록을 스캔하여 프리릴리즈를 포함한 최신 버전을 찾습니다.
    그렇지 않으면 /latest 엔드포인트를 사용합니다 (GitHub 기본적으로 안정 버전만 반환).
    """
    base_url = f"https://api.github.com/repos/{repo}/releases"
    
    try:
        if include_prereleases:
            # 릴리즈 목록을 조회하고 첫 번째 항목 선택 (GitHub는 보통 created_at 내림차순 정렬)
            # 절대적인 최신 버전만 필요하다면 효율성을 위해 1개로 제한
            data = http_get_json(f"{base_url}?per_page=1", token=token)
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
            else:
                return Release("", "", "", "", False, None)
        else:
            # 최신 안정 릴리즈를 위한 특정 엔드포인트 사용
            item = http_get_json(f"{base_url}/latest", token=token)
            if not isinstance(item, dict): # 비어있거나 404일 경우 우아하게 처리
                return Release("", "", "", "", False, None)

        tag_name = item.get("tag_name", "")
        if not tag_name:
            return Release("", "", "", "", False, None)

        return Release(
            tag_name=tag_name,
            name=item.get("name") or tag_name,
            html_url=item.get("html_url") or "",
            body=item.get("body") or "",
            prerelease=item.get("prerelease", False),
            published_at=item.get("published_at"),
        )
    except Exception as e:
        # 실제 앱에서는 로깅을 더 잘해야겠지만, 지금은 빈 객체 반환으로 넘어감
        # print(f"[debug] fetch failed for {repo}: {e}")
        return Release("", "", "", "", False, None)
