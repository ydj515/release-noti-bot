# spring-release-slack-bot-template

GitHub Actions로 Spring Boot / Spring Framework 릴리즈를 감지해 Slack으로 요약 알림을 보내는 MVP 템플릿입니다.

## 빠른 시작
1) 이 폴더 구조 그대로 리포지토리에 커밋합니다.
2) GitHub → Repository → Settings → Secrets and variables → Actions → **New repository secret**
   - `SLACK_WEBHOOK_URL` 추가
3) Actions 탭에서 워크플로우 수동 실행(workflow_dispatch)으로 1회 테스트합니다.

## 커스터마이징 포인트
- `scripts/release-notfier.py`
  - TARGETS에 repo 추가/제거
  - SECTION_PATTERNS / MAX_BULLETS_PER_SECTION 조정
- `.github/workflows/release-to-slack.yml`
  - schedule cron 시간 변경
  - `INCLUDE_PRERELEASES` 옵션 변경

## 전송 모드
- `SLACK_SEND_MODE=combined` (기본): 여러 repo 업데이트를 한 메시지로 묶어서 전송
- `SLACK_SEND_MODE=per_repo`: repo별로 메시지를 각각 전송

## 환경 변수
- 필수: `SLACK_WEBHOOK_URL`
- 옵션:
  - `GITHUB_TOKEN` (레이트리밋/프라이빗 접근)
  - `INCLUDE_PRERELEASES` (true/false)
  - `SLACK_SEND_MODE` (combined/per_repo)
  - `GEMINI_API_KEY` (있으면 릴리스 노트를 Gemini로 요약해서 추가 전송)
  - `GEMINI_MODEL` (선택, 기본 `gemini-2.5-flash`)

### Gemini 요약 활성화하기
1) Google AI Studio에서 API Key를 발급받아 GitHub Repo Secrets에 `GEMINI_API_KEY`로 저장합니다.
2) 워크플로우 실행 시 `scripts/release-notfier.py`가 릴리즈 본문을 Gemini에 보내 짧은 bullet 요약을 생성하고, Slack 메시지에 `AI 요약 (Gemini)` 섹션으로 포함합니다.
3) 키가 없으면 기존 룰 기반 섹션만 전송됩니다.

## 상태 저장
- 최근에 전송한 릴리스 태그는 `state/last_seen.json`에 기록됩니다.
- GitHub Actions가 매 실행 후 전용 브랜치(`release-notifier-state`)에 이 파일만 커밋/푸시합니다. 캐시가 비어도 중복 전송을 막을 수 있습니다.
- 여러 repo를 추적해도 상태는 한 파일/한 브랜치에 함께 저장합니다. 추가 브랜치가 필요 없습니다.
