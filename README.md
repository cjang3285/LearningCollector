# LearningCollector

개인 학습 활동 자동 수집 및 블로그 초안 생성 도구

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 개요

학습 활동을 자동으로 수집하고 Gemini API를 활용해 블로그 초안을 생성하는 CLI 도구입니다.

### 수집 대상

- **GitHub 커밋**: 모든 레포지토리, 모든 브랜치에서 커밋 수집 (GraphQL API)
- **백준 문제풀이**: BaekjoonHub 연동 레포지토리에서 자동 푸시된 풀이
- **AI 채팅 기록**: Claude, ChatGPT, Gemini 대화 마크다운 파일

### 주요 기능

1. **자동 수집**: 마지막 실행 이후 증분 수집 (exec_date.log 기반)
2. **중복 제거**: SHA 기반 커밋 중복 체크, 파일명 기반 AI Chat 중복 체크
3. **블로그 초안 생성**: Gemini API로 카테고리별 초안 자동 생성
   - 알고리즘 풀이 (백준)
   - 개발 진척 (커밋 요약)
   - 학습 노트 (AI 채팅)
4. **자동 블로그 포스팅**: 생성된 초안을 자동으로 블로그에 업로드

---

## 빠른 시작

### 1. 설치

```bash
# 클론
git clone https://github.com/cjang3285/LearningCollector.git
cd LearningCollector

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

첫 실행 시 CLI로 환경변수 입력:

```bash
python main.py
```

또는 `.env` 파일을 직접 생성:

```env
# 인증 정보
GITHUB_TOKEN=ghp_your_token_here
GEMINI_API_KEY=your_gemini_api_key

# 감시 대상
AI_CHAT_DOWNLOAD_DIR=/path/to/downloads
LOG_FILE_PATH=./log/err.log

# 필터링
GITHUB_USERNAME=your_github_username
EDITOR_COMMAND=code
```

### 3. 실행

```bash
# 기본 실행 (첫 실행 시 최근 30일 수집)
python main.py

# 강제 30일 전체 수집
FORCE_FULL_COLLECTION=true python main.py
```

---

## 프로젝트 구조

```
LearningCollector/
├── main.py                          # 메인 실행 파일
│
├── core/                            # 핵심 로직
│   ├── orchestrator.py              # 전체 흐름 조율
│   ├── github_collector.py          # GitHub 커밋 수집
│   ├── ai_chat_collector.py         # AI Chat 마크다운 수집
│   ├── gemini_draft_generator.py    # Gemini로 초안 생성
│   ├── classifier.py                # 커밋 분류 (백준/개발)
│   ├── env_validator.py             # 환경변수 검증
│   └── startup_register.py          # 시작프로그램 등록
│
├── api/                             # 외부 API 클라이언트
│   ├── github_graphql.py            # GitHub GraphQL API
│   └── gemini_client.py             # Gemini API
│
├── policies/                        # 정책 및 저장 로직
│   ├── collection_period.py         # 수집 기간 계산
│   └── storage/                     # 저장 정책
│       ├── json_saver.py            # JSON 파일 저장
│       ├── draft_saver.py           # Draft 마크다운 저장
│       └── duplicate_checker.py     # 중복 체크
│
├── prompts/                         # Gemini 프롬프트 템플릿
│   ├── 알고리즘_풀이_포스팅_프롬프트.md
│   ├── 프로젝트_진척_및_의사결정_요약_프롬프트.md
│   └── AI와의_대화를_통한_학습_요약_프롬프트.md
│
├── data/                            # 수집된 데이터 (JSON)
│   ├── baekjoon/                    # 백준 풀이
│   ├── commits/                     # 개발 커밋
│   ├── ai_chat/                     # AI 채팅 기록
│   └── draft/                       # 생성된 초안
│       ├── algorithm/
│       ├── dev/
│       └── study/
│
└── log/                             # 로그
    └── exec_date.log                # 마지막 실행 시간 기록
```

---

## 작동 원리

### 1. 수집 기간 계산 (UTC 기준)

- **첫 실행**: 최근 30일
- **이후 실행**: 마지막 실행 시간(exec_date.log) ~ 현재
- 모든 datetime은 UTC로 통일 (`datetime.now(timezone.utc)`)

### 2. GitHub 커밋 수집 (GraphQL API)

```python
# 모든 레포지토리 조회
repositories = fetch_user_repositories(username)

# 각 레포의 모든 브랜치 조회
for repo in repositories:
    branches = fetch_branches(repo)

    # 각 브랜치의 커밋 수집
    for branch in branches:
        commits = fetch_branch_commits(repo, branch, since, until)
```

**중복 제거**:
- SHA 기반 중복 체크
- 백준 커밋 / 개발 커밋 분류
- JSON 파일로 저장 (`data/baekjoon/`, `data/commits/`)

### 3. AI Chat 수집

- 다운로드 폴더 감시 (`AI_CHAT_DOWNLOAD_DIR`)
- 파일명 패턴: `Claude-*.md`, `ChatGPT-*.md`, `Gemini-*.md`
- 중복: 파일명 기반 체크
- JSON 저장: `data/ai_chat/`

### 4. Gemini 초안 생성

```python
for json_file in json_files:
    # 중복 체크 (이미 생성된 draft가 있는지)
    if is_duplicate_draft(json_file):
        continue

    # Gemini API 호출
    prompt = load_prompt("알고리즘_풀이_포스팅_프롬프트.md")
    draft = gemini_client.generate_draft(prompt, json_content)

    # Draft 저장
    save_draft(draft, category="algorithm")
```

**에러 처리**:
- 일일 한도 초과: 나머지 스킵 (다음 실행 때 재시도)
- Rate limit: Exponential backoff (2s, 4s, 8s)
- 오류 draft 자동 삭제 (키워드: "오류", "RESOURCE_EXHAUSTED", "429")

### 5. 블로그 포스팅

- VS Code로 생성된 draft 열기
- 자동으로 블로그에 포스팅

---

## 주요 API

### GitHub GraphQL API

**장점**:
- 한 번의 요청으로 여러 브랜치 조회
- 필요한 필드만 요청 (효율적)

**제약**:
- `history` 필드에서 `since`와 `until` 동시 사용 불가
- 해결: `since`만 사용, 클라이언트에서 `end_date` 필터링

**중요 설정**:
```python
# ISO 포맷에서 마이크로초 제거 (GitHub API 호환성)
since_param = start_date.replace(microsecond=0).isoformat() + "Z"
```

### Gemini API

**모델**: `gemini-2.5-flash-lite`

**Retry 로직**:
- 일일 한도 초과: 즉시 중단
- Rate limit: Exponential backoff (최대 3회)

---

## 중복 제거 전략

### 1. GitHub 커밋

- **키**: 커밋 SHA (`oid`)
- **저장**: `data/baekjoon/duplicate.json`, `data/commits/duplicate.json`
- **체크 시점**: 수집 직후, JSON 저장 전

### 2. AI Chat

- **키**: 파일명 (예: `Claude-학습etl마무리.md`)
- **저장**: `data/ai_chat/duplicate.json`
- **체크 시점**: 수집 직후, JSON 저장 전

### 3. Draft

- **키**: 원본 JSON 파일명
- **체크 시점**: Gemini API 호출 전
- **예외**: 오류가 포함된 draft는 자동 삭제 후 재생성

---

## 자동화 설정

### Cron (매일 자정 실행)

```bash
# crontab 편집
crontab -e

# 매일 자정 실행
0 0 * * * cd /home/user/LearningCollector && /home/user/LearningCollector/venv/bin/python main.py >> /home/user/LearningCollector/log/cron.log 2>&1
```

---

## 환경 변수

| 변수 | 설명 | 필수 |
|------|------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token (repo 권한) | ✅ |
| `GEMINI_API_KEY` | Gemini API Key | ✅ |
| `GITHUB_USERNAME` | GitHub 사용자명 | ✅ |
| `AI_CHAT_DOWNLOAD_DIR` | AI Chat 마크다운 다운로드 폴더 | ✅ |
| `LOG_FILE_PATH` | 로그 파일 경로 (기본: ./log/err.log) | ❌ |
| `EDITOR_COMMAND` | 에디터 명령어 (기본: code) | ❌ |
| `FORCE_FULL_COLLECTION` | 강제 30일 수집 (true/false) | ❌ |

---

## 문제 해결

### 1. 커밋이 수집되지 않음

**증상**: "0개 커밋" 메시지

**원인**:
- `exec_date.log`에 KST 시간이 기록되어 있음 (UTC로 읽으려고 시도)
- 시작 시간 > 종료 시간 (역전된 범위)

**해결**:
```bash
# exec_date.log 삭제 후 재실행
rm log/exec_date.log
python main.py
```

### 2. Gemini API 한도 초과

**증상**: "⚠️ API 한도 초과" 메시지

**해결**:
- 무료 티어: 분당 15개 제한
- 다음날 재실행 (중복 체크 덕분에 이미 생성된 draft는 건너뜀)

### 3. Draft에 오류 메시지만 있음

**증상**: Draft 내용이 "# 오류", "RESOURCE_EXHAUSTED" 등

**해결**:
- 자동으로 감지 및 삭제됨
- 다음 실행 때 재생성됨

---

## 의존성

- Python 3.8+
- GitHub Personal Access Token
- Gemini API Key
- BaekjoonHub 연동 레포지토리
- AI Chat Exporter Chrome Extensions:
  - [Claude Exporter](https://chromewebstore.google.com/detail/claude-exporter/elhmfakncmnghlnabnolalcjkdpfjnin)
  - [ChatGPT Exporter](https://chromewebstore.google.com/detail/chatgpt-exporter/pldlpacbeonbjfhlongcdflcgfcnglkl)
  - [Gemini Chat Exporter](https://chromewebstore.google.com/detail/gemini-chat-exporter/bhmoomcflhcfhingnjjieheeadmdefkc)

---

## 라이선스

MIT License

---

## 관련 프로젝트

- [BaekjoonHub](https://github.com/BaekjoonHub/BaekjoonHub) - 백준 자동 커밋 푸시
- [Claude Exporter](https://github.com/jasonkneen/claude-exporter)
- [ChatGPT Exporter](https://github.com/pionxzh/chatgpt-exporter)
- [Gemini Chat Exporter](https://github.com/jiajunhang/gemini-chat-exporter)
