# -*- coding: utf-8 -*-
import json
import os
import re
import urllib.request
from typing import Any, Dict, Optional, Tuple

from scripts.config import STATE_PATH

def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")

def load_env_file(path: str = ".env") -> None:
    """
    간단한 .env 파일 로더입니다.
    외부 라이브러리 없이 로컬 개발 환경을 지원하기 위해 사용합니다.
    이미 환경 변수가 설정되어 있다면 덮어쓰지 않습니다.
    """
    if not os.path.exists(path):
        return

    print(f"[info] Loading environment variables from {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                
                # 따옴표 제거
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                if key and key not in os.environ:
                    os.environ[key] = value

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
