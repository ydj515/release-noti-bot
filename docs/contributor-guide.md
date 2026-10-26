# 기여 및 개발 가이드

이 문서는 `release-noti-bot` 저장소의 로컬 개발 환경, `mise` 환경 프로필 정책, 설정 및 검증 방법을 안내합니다.

## 요구 사항 및 초기 설정

도구 버전(Python `3.14.6`)은 [`mise.toml`](../mise.toml)에 고정되어 있습니다.

```bash
mise trust ./mise.toml   # 최초 1회, task와 overlay를 검토한 뒤 신뢰
mise run bootstrap       # 고정된 버전의 Python 설치 및 환경 준비
mise run config:check    # task 참조·순환 검사 (앱 실행 없음)
mise run verify          # 프로젝트 구문 검증
```

## mise 환경 구성 및 프로필 정책

`mise.toml`은 도구 버전과 공통 task를 정의하며, `mise.dev.toml`과 `mise.prod.toml`은 공유 환경 선택을 담당합니다.

### 1. 환경 프로필 (`APP_ENV`)
- 기본 실행은 `APP_ENV=local`이며, `-E dev`는 개발 overlay, `-E prod`는 운영 설정을 선택합니다.
  ```bash
  mise run verify
  mise -E dev run verify
  ```
- 환경 선택 자체가 배포나 서비스 시작을 수행하지 않습니다.
- `APP_ENV`는 공통 환경 식별자이며, 애플리케이션의 기존 실행·배포 설정은 그대로 유지됩니다.
- `-E local`은 사용하지 않습니다.

### 2. 개인 로컬 설정 및 `.env` 관리
- **개인 개발 설정 (`mise.dev.local.toml`)**: [`mise.dev.local.toml.example`](../mise.dev.local.toml.example)을 검토해 `mise.dev.local.toml`로 복사합니다. `.env.dev.local`을 만든 뒤 `env._.file`을 활성화하면 `-E dev` 실행 시에만 읽습니다. 기존 개인 파일을 덮어쓰지 않습니다.
- **전역 로컬 오버라이드 (`mise.local.toml`)**: `mise.local.toml`은 **모든 환경**에서 로드됩니다. 운영(prod) 실행 체크아웃 경로에는 개인 override나 개발용 dotenv(`.env`)를 두지 마세요.
- **애플리케이션 `.env` 자동 로드**: `python -m scripts.main` 실행 시 프로젝트 루트의 `.env` 파일을 표준 라이브러리로 자동 로드합니다. 운영 실행 체크아웃에는 `.env` 파일도 두지 않습니다.

### 3. 버전 고정 및 Lockfile 정책
- `mise`는 개발 도구의 정확한 버전 고정과 프로필 분리에 사용합니다.
- `[settings] lockfile = false`로 도구 lock 생성을 비활성화하고 `mise.lock`은 관리하지 않습니다. 공통 표준의 `mise.lock` 지침보다 이 저장소의 정책을 우선하며, 향후 설치 아티팩트 해시까지 고정해야 하는 요구가 생기면 다시 도입합니다.
- 도구 버전은 `mise.toml`의 `[tools]`에서 관리하며 `dev`/`prod` 및 GitHub Actions CI에서도 동일한 버전(`Python 3.14.6`)을 사용합니다. 로컬과 CI는 `mise install` 또는 동일한 정확한 버전의 setup action으로 도구를 준비합니다.
- 추후 외부 패키지 매니저(`uv.lock` 등)를 도입하더라도 애플리케이션 의존성 잠금과 검증 옵션은 별도로 유지합니다.
- 지원 OS는 각 도구와 실행 스크립트의 호환성에 따릅니다 (`mise.lock` 미사용이 Windows 실행 보장을 의미하지는 않습니다).
- `mise run bootstrap`은 이 프로젝트의 초기 설정 task입니다. OS 패키지·dotfile·서비스를 관리하는 `mise bootstrap` 명령은 개인 머신 설정에서 별도로 채택합니다.

## 로컬 실행 및 검증

### 구문 검증 (`verify`)
`mise run verify` (또는 `mise run check`)는 네트워크 호출이나 알림 발송 없이 `scripts/*.py`의 Python AST 구문 검사만 수행합니다.

```bash
mise run verify
```

### 실제 알림 발송 테스트
실제 GitHub API 조회 및 Slack 웹훅 전송을 테스트하려면 루트에 `.env` 파일을 작성한 뒤 직접 모듈을 실행합니다.

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
GEMINI_API_KEY=your-api-key  # 선택 사항
```

```bash
mise exec -- python -m scripts.main
```

## 커스터마이징 가이드

- **감시 대상 변경**: [`scripts/targets.py`](../scripts/targets.py)의 `TARGETS` 리스트에 `("owner/repo", "표시 이름")` 튜플을 추가하거나 수정합니다.
- **섹션 파싱 규칙**: [`scripts/config.py`](../scripts/config.py)의 `SECTION_PATTERNS` 정규표현식과 `MAX_BULLETS_PER_SECTION` 상수를 조정합니다.
- **AI 요약 프롬프트 및 모델**: [`scripts/ai_summarizer.py`](../scripts/ai_summarizer.py) 및 [`scripts/config.py`](../scripts/config.py)에서 기본 모델과 요약 최대 길이(`MAX_RELEASE_BODY_FOR_AI`)를 관리합니다.
