# Release Notification Bot

[![Release note notification to Slack](https://github.com/ydj515/release-noti-bot/actions/workflows/release-to-slack.yml/badge.svg)](https://github.com/ydj515/release-noti-bot/actions/workflows/release-to-slack.yml)
[![Python 3.14.6](https://img.shields.io/badge/python-3.14.6-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

GitHub 저장소의 신규 릴리즈를 주기적으로 감지해 **Slack**으로 요약 알림을 전송하는 봇입니다.
릴리즈 노트에서 주요 섹션(Breaking Changes, Deprecations, New Features, Bug Fixes 등)을 자동 분류하며, **Google Gemini** 연동을 통해 한국어 요약본을 함께 제공합니다.
외부 패키지 의존성 없이 Python 표준 라이브러리만으로 동작하며, 별도 DB 없이 GitHub Actions 캐시와 전용 브랜치(`release-notifier-state`)로 알림 상태를 관리합니다.

**기술 스택:** Python 3.14 (Standard Library) · GitHub Actions · Slack Block Kit · Google Gemini API · mise

## 주요 기능

- **릴리즈 자동 감지 및 상태 관리:** [`scripts/targets.py`](./scripts/targets.py)에 등록된 저장소의 최신 릴리즈를 확인하고, [`state/last_seen.json`](./state/last_seen.json)으로 중복 발송을 방지
- **스마트 요약 및 섹션 파싱:** `GEMINI_API_KEY` 설정 시 Gemini가 핵심 변경 사항을 한글로 요약하며, 미설정 시에도 정규표현식 기반으로 주요 섹션을 추출
- **유연한 알림 구성:** 여러 릴리즈를 한 메시지로 묶는 `combined` 모드와 저장소별로 전송하는 `per_repo` 모드, 프리릴리즈 포함 여부 설정 지원

## 알림 메시지 예시

Slack Block Kit 형식으로 전송되며, AI 요약과 원문 섹션 파싱 결과가 함께 표시됩니다.

> **Spring Boot 업데이트: v3.4.2**
> [Release notes 열기](https://github.com/spring-projects/spring-boot/releases/tag/v3.4.2)
> `Published: 2026-01-23T10:15:30Z`
>
> **AI 요약 (Gemini)**
> Features:
> - 카프카 및 OTel 자동 설정 프로퍼티 확장 지원
> BugFixes:
> - Actuator 헬스 체크 시 간헐적 타임아웃 오류 수정
> Dependency:
> - Spring Framework 6.2.2, Tomcat 10.1.34 등 주요 의존성 업그레이드
>
> **Bug Fixes**
> - Fix ConcurrentModificationException in ConfigurationProperties (#43210)
> - Resolve metrics tag collision when using custom observation convention (#43198)
>
> **Dependency Upgrades**
> - Upgrade to Spring Framework 6.2.2 (#43250)
> - Upgrade to Jackson Bom 2.18.2 (#43245)

## 요구 사항

- [mise](https://mise.jdx.dev/) — Python 버전(`3.14.6`)은 [`mise.toml`](./mise.toml)에 고정되어 있으며 `mise`가 설치합니다.

## 빠른 시작

### 로컬 실행

```bash
mise trust ./mise.toml          # 최초 1회, mise.toml 검토 후 신뢰
mise run bootstrap              # 고정된 Python 3.14.6 설치
mise run verify                 # 구문 검증 (알림 발송 없음)
```

실제 Slack 알림 발송을 테스트하려면 프로젝트 루트에 `.env` 파일을 생성하고 실행하세요:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
GEMINI_API_KEY=your-api-key  # 선택 사항
```

```bash
mise exec -- python -m scripts.main
```

### GitHub Actions 배포

1. 이 저장소를 포크하거나 복사합니다.
2. `Settings` → `Secrets and variables` → `Actions`에서 시크릿을 등록합니다 (`SLACK_WEBHOOK_URL` 필수, `GEMINI_API_KEY` 선택).
3. [`.github/workflows/release-to-slack.yml`](./.github/workflows/release-to-slack.yml) 워크플로우가 매일 **09:05 KST**에 자동 실행됩니다 (`Actions` 탭에서 수동 실행 가능).

## 주요 명령

| 명령                    | 설명                                               |
| ----------------------- | -------------------------------------------------- |
| `mise run bootstrap`    | 고정된 Python 버전 설치 및 초기 환경 준비          |
| `mise run config:check` | `mise` 태스크 참조 및 순환 의존성 검사             |
| `mise run check`        | 네트워크 호출·알림 발송 없이 Python AST 구문 검사 |
| `mise run verify`       | 프로젝트 전체 검증 (`check` 실행)                  |
| `python -m scripts.main`| `.env` 로드 후 릴리즈 조회 및 Slack 알림 발송      |

전체 태스크 목록은 `mise tasks`로 확인할 수 있습니다. `dev`/`prod` 환경 프로필(`-E dev`, `-E prod`)과 `mise.dev.local.toml` 등 상세 설정 정책은 [기여 및 개발 가이드](./docs/contributor-guide.md#mise-환경-구성-및-프로필-정책)를 참고하세요.

## 설정 및 환경 변수

감시 대상 저장소는 [`scripts/targets.py`](./scripts/targets.py)의 `TARGETS` 리스트에서 수정합니다.

| 환경 변수              | 필수 여부 | 기본값             | 설명                                                 |
| ---------------------- | --------- | ------------------ | ---------------------------------------------------- |
| `SLACK_WEBHOOK_URL`    | **필수**  | -                  | Slack Incoming Webhook URL                           |
| `GEMINI_API_KEY`       | 선택      | -                  | Google Gemini API Key (설정 시 AI 한글 요약 활성화)  |
| `GEMINI_MODEL`         | 선택      | `gemini-2.5-flash` | 요약에 사용할 Gemini 모델                            |
| `SLACK_SEND_MODE`      | 선택      | `combined`         | 알림 묶음 방식 (`combined` 또는 `per_repo`)          |
| `INCLUDE_PRERELEASES`  | 선택      | `false`            | 프리릴리즈(RC, Milestone 등) 알림 포함 여부          |
| `GITHUB_TOKEN`         | 선택      | -                  | GitHub API Rate Limit 완화용 토큰                    |

## 프로젝트 구조

```text
.
├── .github/workflows/      # GitHub Actions 스케줄 및 실행 워크플로우
├── docs/                   # 개발 및 환경 구성 가이드
├── scripts/                # Python 소스 코드 (외부 의존성 없음)
│   ├── main.py             # 애플리케이션 진입점
│   ├── targets.py          # 감시 대상 GitHub 저장소 목록
│   ├── config.py           # 섹션 파싱 정규식 및 기본 설정
│   ├── github_client.py    # GitHub Releases REST API 클라이언트
│   ├── release_parser.py   # 릴리즈 노트 섹션 추출기
│   ├── ai_summarizer.py    # AI 요약기 (Gemini 연동)
│   ├── slack_client.py     # Slack Block Kit 메시지 빌더 및 전송기
│   └── utils.py            # 상태 관리 및 .env 로더
├── state/                  # 마지막 알림 버전 기록 (last_seen.json)
└── mise.toml               # 도구 버전 및 태스크 정의
```

## 문서 및 기여

- [기여 및 개발 가이드 (mise 환경 구성 정책)](./docs/contributor-guide.md)

## 라이선스

MIT License
