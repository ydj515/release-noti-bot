from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Release:
    tag_name: str
    name: str
    html_url: str
    body: str
    prerelease: bool
    published_at: Optional[str]
