# Release Notification Bot

GitHub Actions를 기반으로 **Spring Boot**, **Spring Framework** (또는 설정된 다른 저장소)의 새 릴리즈를 감지하여 **Slack**으로 요약 알림을 보내는 봇입니다. 

단순한 텍스트 알림을 넘어, **Google Gemini** 또는 **OpenAI**를 활용해 릴리즈 노트를 자동으로 요약해주며, 중요한 변경 사항(Breaking Changes, Deprecations)을 섹션별로 정리해서 보여줍니다.

## 주요 기능

- **자동 감지**: 지정된 GitHub 저장소의 최신 릴리즈를 주기적으로 확인합니다.
- **스마트 요약 (AI Powered)**: 
  - `GEMINI_API_KEY` 설정 시 **Google Gemini**가 릴리즈 노트를 한글로 요약합니다.
  - (준비 중) `OPENAI_API_KEY`를 이용한 OpenAI 모델 연동도 구조적으로 지원합니다 (현재 코드에서는 비활성화 상태).
  - AI 설정이 없으면 정규표현식 기반의 기본 요약만 전송됩니다.
- **섹션별 정리**: Breaking Changes, New Features, Bug Fixes 등을 자동으로 파싱하여 보여줍니다.
- **상태 관리**: `state/last_seen.json` 파일을 통해 중복 알림을 방지하며, 별도의 DB 없이 GitHub Branch/Cache를 이용해 상태를 유지합니다.
- **모듈화된 구조**: 유지보수와 확장이 용이하도록 코드가 모듈화되어 있습니다.

## 빠른 시작 (Quick Start)

### 1. 리포지토리 설정
이 프로젝트를 자신의 GitHub 리포지토리로 복사하거나 포크합니다.

### 2. GitHub Secrets 설정
`Settings` → `Secrets and variables` → `Actions` → `New repository secret`에서 다음 변수들을 추가합니다.

| Secret 이름 | 필수 여부 | 설명 |
|---|---|---|
| `SLACK_WEBHOOK_URL` | **필수** | Slack Incoming Webhook URL |
| `GEMINI_API_KEY` | 선택 | Google Gemini API Key (AI 요약 기능 활성화 시) |
| `OPENAI_API_KEY` | 선택 | OpenAI API Key (현재 준비 중) |
| `GITHUB_TOKEN` | 선택 | 기본 제공 토큰 사용 권장 (API Rate Limit 회피용) |

### 3. 워크플로우 실행
`.github/workflows/release-to-slack.yml` 워크플로우는 기본적으로 매일 **09:05 KST**에 실행됩니다.
테스트를 위해 **Actions** 탭에서 `Release note notification to Slack` 워크플로우를 선택하고 **Run workflow**를 클릭하여 수동으로 실행해볼 수 있습니다.

## 설정 및 커스터마이징

소스 코드는 `scripts/` 디렉토리에 모듈화되어 있습니다.

### 감시 대상 변경 (`scripts/config.py`)
`TARGETS` 리스트를 수정하여 감시할 저장소를 추가하거나 변경할 수 있습니다.
```python
TARGETS = [
    ("spring-projects/spring-boot", "Spring Boot"),
    ("facebook/react", "React"),  # 예시: React 추가
]
```

### 환경 변수 옵션
워크플로우 파일(`.github/workflows/release-to-slack.yml`)의 `env` 섹션에서 다음 옵션들을 조정할 수 있습니다.

- `SLACK_SEND_MODE`: 
  - `combined` (기본값): 여러 저장소의 업데이트를 하나의 슬랙 메시지로 묶어서 전송합니다.
  - `per_repo`: 각 저장소마다 별도의 슬랙 메시지를 전송합니다.
- `INCLUDE_PRERELEASES`: `true`로 설정하면 프리릴리즈(RC, Milestone 등)도 알림 대상에 포함합니다.
- `GEMINI_MODEL`: 사용할 Gemini 모델 (기본값: `gemini-2.5-flash`)
- `OPENAI_MODEL`: 사용할 OpenAI 모델 (기본값: `gpt-4o`)

## 프로젝트 구조

```
.
├── .github/workflows/      # GitHub Actions 워크플로우 정의
├── scripts/                # Python 소스 코드
│   ├── main.py             # 진입점 (Entry point)
│   ├── config.py           # 설정 (대상 저장소, 정규식 등)
│   ├── ai_summarizer.py    # AI 요약 로직 (Gemini, OpenAI)
│   ├── github_client.py    # GitHub API 클라이언트
│   ├── slack_client.py     # Slack 메시지 생성 및 전송
│   ├── release_parser.py   # 릴리즈 노트 파싱 (섹션 분류)
│   └── utils.py            # 유틸리티 함수
├── state/                  # 릴리즈 상태 저장소 (자동 관리됨)
└── README.md               # 문서
```

## 로컬 실행 방법

로컬 환경에서 테스트하려면 Python 3.8 이상이 필요합니다.

1. **의존성 없음**: 외부 라이브러리(`python-dotenv` 등) 없이 표준 라이브러리만으로 `.env` 파일을 지원합니다. 별도의 `pip install`이 필요 없습니다.
2. **환경 변수 설정**:
   프로젝트 루트에 `.env` 파일을 생성하고 다음과 같이 작성합니다:
   ```env
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   GEMINI_API_KEY=your-api-key  # 선택 사항
   ```
3. **실행**:
   프로젝트 루트에서 다음 명령어를 실행합니다. `.env` 파일이 있으면 자동으로 로드됩니다.
   ```bash
   python -m scripts.main
   ```

## 라이선스

MIT License
