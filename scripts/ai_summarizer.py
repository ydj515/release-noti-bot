from __future__ import annotations

import json
import urllib.request
from abc import ABC, abstractmethod
from typing import Optional

from scripts.config import MAX_RELEASE_BODY_FOR_AI
from scripts.models import Release


class AISummarizer(ABC):
    """AI 요약기를 위한 추상 기본 클래스입니다."""

    @abstractmethod
    def summarize(self, product: str, release: Release) -> Optional[str]:
        """
        릴리즈 노트의 짧은 Slack용 요약을 생성합니다.
        :param product: 제품 이름 (예: "Spring Boot").
        :param release: 태그, 이름, 본문 등을 포함하는 Release 객체.
        :return: 요약된 문자열, 또는 요약이 불가능/불필요한 경우 None.
        """
        pass


class GeminiAISummarizer(AISummarizer):
    """Google Gemini API를 사용하는 AI 요약 구현체입니다."""

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("GeminiAISummarizer를 위해 GEMINI_API_KEY가 비어있을 수 없습니다.")
        self._api_key = api_key
        self._model = model

    def summarize(self, product: str, rel: Release) -> Optional[str]:
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

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
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

# 다른 요약기를 추가하는 방법의 예시 (예: OpenAI의 GPT)
# class GptAISummarizer(AISummarizer):
#     def __init__(self, api_key: str, model: str):
#         self._api_key = api_key
#         self._model = model
#
#     def summarize(self, product: str, rel: Release) -> Optional[str]:
#         # 여기서 GPT 전용 API 호출 및 파싱 구현
#         # GeminiAISummarizer와 유사하지만 OpenAI의 클라이언트 라이브러리나 HTTP API 사용
#         pass


class SummarizerFactory:
    """AISummarizer 인스턴스를 생성하는 팩토리입니다."""

    @staticmethod
    def create(provider: str, api_key: str, model: str) -> Optional[AISummarizer]:
        provider = provider.lower().strip()
        if provider == "gemini":
            return GeminiAISummarizer(api_key=api_key, model=model)
        # elif provider == "openai":
        #    return OpenAISummarizer(api_key=api_key, model=model)
        
        return None

def get_summarizer(provider: str, api_key: str, model: str) -> Optional[AISummarizer]:
    """요약기 인스턴스를 가져오는 헬퍼 함수입니다."""
    return SummarizerFactory.create(provider, api_key, model)
