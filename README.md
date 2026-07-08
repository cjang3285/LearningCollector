# LearningCollector

개인 학습·개발 활동 자동 수집 및 블로그 초안 생성 도구

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 개요

GitHub 활동과 AI 채팅 기록을 자동으로 수집하고, Gemini API로 블로그 초안을 생성해 자동으로 게시하는 CLI 도구입니다.

### 수집 대상

- **GitHub 커밋**: 개인 레포는 물론, 소속된 조직(organization) 레포까지 모든 브랜치에서 커밋 수집 (GraphQL API)
- **GitHub PR**: 병합되었거나 닫힌 Pull Request (진행 중인 PR은 나중에 바뀔 수 있어 제외)
- **AI 채팅 기록**: Claude, ChatGPT, Gemini 대화 마크다운 파일 (Claude Code 세션 기록도 별도 export 스크립트로 같은 방식으로 활용 가능)

### 주요 기능

1. **자동 수집**: 마지막 실행 이후 증분 수집 (소스별 수집 시간 로그 기반), 비활성 레포는 사전 필터링·병렬 조회로 빠르게 처리
2. **중복 제거**: SHA/PR ID/파일명 기반 중복 체크 (메모리 캐싱)
3. **블로그 초안 생성**: Gemini API로 카테고리별 초안 자동 생성
   - 개발 진척 (커밋 요약)
   - PR 요약 (병합/닫힌 PR)
   - 학습 노트 (AI 채팅 기록)
4. **콘텐츠 기반 태그**: 카테고리별 고정 태그 대신, 초안 내용을 보고 AI가 직접 구체적인 태그를 붙임 (레포지토리명 포함)
5. **자동 블로그 포스팅**: 생성된 초안을 자동으로 블로그에 업로드

> 백준 문제풀이 수집 기능은 백준허브 연동 서비스 종료로 현재 비활성화되어 있습니다 (`core/github_collector.py`에 주석 처리, 필요 시 복구 가능).

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

또는 `.env` 파일을 직접 생성 (`.env.example` 참고):

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

`GITHUB_TOKEN`은 조직 레포까지 조회하므로 `repo` 스코프가 필요합니다.

### 3. 실행

```bash
# 기본 실행 (첫 실행 시 최근 30일 수집)
python main.py

# 강제 30일 전체 수집
FORCE_FULL_COLLECTION=true python main.py

# cron 등 자동화용 (모든 레포/브랜치 자동 조회)
python main.py --auto
```

---

## 프로젝트 구조

```
LearningCollector/
├── main.py                          # 메인 실행 파일
│
├── core/                            # 핵심 로직
│   ├── orchestrator.py              # 전체 흐름 조율
│   ├── github_collector.py          # GitHub 커밋/PR 수집
│   ├── ai_chat_collector.py         # AI Chat 마크다운 수집
│   ├── gemini_draft_generator.py    # Gemini로 초안 생성
│   ├── env_validator.py             # 환경변수 검증
│   └── startup_register.py          # 시작프로그램 등록
│
├── api/                             # 외부 API 클라이언트
│   ├── github_graphql.py            # GitHub GraphQL API
│   ├── gemini_client.py             # Gemini API
│   ├── groq_client.py               # Groq API (현재 미사용, 폴백용으로 남겨둠)
│   ├── ai_client.py                 # Gemini 호출 통합 클라이언트
│   └── blog_api.py                  # 블로그 포스팅 API
│
├── policies/                        # 정책 및 저장 로직
│   ├── collection_period.py         # 수집 기간 계산
│   ├── collection_rules.py          # 수집 대상 판별 규칙
│   └── storage/                     # 저장 정책
│       ├── json_saver.py            # JSON 파일 저장
│       ├── draft_saver.py           # Draft 마크다운 저장
│       └── duplicate_checker.py     # 중복 체크 (메모리 캐싱)
│
├── prompts/                         # Gemini 프롬프트 템플릿
│   ├── 프로젝트_진척_및_의사결정_요약_프롬프트.md
│   ├── PR_리뷰_및_병합_요약_프롬프트.md
│   ├── 당일_공부_요약_프롬프트.md
│   ├── 알고리즘_풀이_포스팅_프롬프트.md      # 백준 수집 비활성화로 현재 미사용
│   └── 대화_내용_압축_요약_프롬프트.md        # 대용량 입력 압축용 (현재 미사용 경로)
│
├── data/                            # 수집된 데이터 (JSON, git 미포함)
│   ├── commits/                     # 개발 커밋
│   ├── prs/                         # PR
│   ├── ai_chat/                     # AI 채팅 기록
│   ├── baekjoon/                    # 백준 풀이 (레거시, 현재 미수집)
│   └── draft/                       # 생성된 초안
│       ├── dev/
│       ├── pr/
│       ├── study/
│       └── algorithm/               # 레거시, 현재 미생성
│
└── log/                             # 로그 (git 미포함)
```

---

## 작동 원리

### 1. GitHub 수집 (GraphQL + REST)

- 개인 계정 레포뿐 아니라 소속된 조직 레포까지 `viewer` 쿼리로 조회
- 레포별 `pushedAt`을 먼저 확인해, 이번 수집 기간에 변경 없는 레포는 브랜치/커밋 조회 자체를 생략
- 남은 레포는 브랜치 목록 + 커밋 히스토리를 레포당 요청 1번(중첩 GraphQL 쿼리)으로 조회하며, 레포 간 조회는 병렬 실행
- 병합/닫힌 PR도 같은 방식으로 조회 (열려있는 PR은 이후 내용이 바뀔 수 있어 제외)
- 커밋/PR의 변경 파일 상세(diff)는 REST API로 추가 조회 (레포별 실제 소유자 기준)

### 2. AI Chat 수집

- 다운로드 폴더 감시 (`AI_CHAT_DOWNLOAD_DIR`)
- 파일명 패턴: `Claude-*.md`, `ChatGPT-*.md`, `Gemini-*.md`
- 중복: 원본 파일명 기반 체크

### 3. Gemini 초안 생성

```python
for json_file in json_files:
    if is_duplicate_draft(json_file):
        continue

    prompt = load_prompt(...)
    draft = ai_client.generate_draft(prompt, json_content)
    save_draft(draft, category=...)
```

- 초안 마지막 줄에 AI가 직접 붙인 `**태그:** ...` 를 파싱해서 블로그 태그로 사용 (없으면 카테고리 고정 태그로 폴백)
- 제목(H1)과 발췌(첫 문단)는 별도 필드로 추출되고 본문에서는 제거되어, 블로그에 제목/발췌가 중복 표시되지 않음

**에러 처리**:
- Gemini 서버 일시적 과부하(503): 지수 백오프로 재시도
- 일일 한도 초과 등 영구적 실패: 해당 실행의 나머지 초안 생성은 중단하고 다음 실행에서 재시도 (일시적 실패는 해당 항목만 건너뛰고 계속 진행)
- 오류 draft 자동 삭제 후 재생성

### 4. 블로그 포스팅

- 생성된 초안을 자동으로 블로그에 업로드
- 에디터로 draft 파일 열기

---

## 중복 제거 전략

각 소스 폴더를 인스턴스당 한 번만 스캔해 키 값을 메모리에 캐싱하고, 이후 조회는 O(1) 집합 조회로 처리합니다.

| 소스 | 중복 키 |
|------|---------|
| 개발 커밋 | 커밋 SHA |
| PR | PR의 GraphQL 전역 ID |
| AI Chat | 원본 마크다운 파일명 |
| Draft | 소스 JSON 파일명 (경로 직접 확인) |

---

## 자동화 설정

### Cron (매일 자정 실행)

```bash
crontab -e

0 0 * * * cd /home/user/LearningCollector && /home/user/LearningCollector/venv/bin/python main.py --auto >> /home/user/LearningCollector/log/cron.log 2>&1
```

---

## 환경 변수

| 변수 | 설명 | 필수 |
|------|------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token (`repo` 권한, 조직 레포 조회용) | ✅ |
| `GEMINI_API_KEY` | Gemini API Key | ✅ |
| `GITHUB_USERNAME` | GitHub 사용자명 | ✅ |
| `AI_CHAT_DOWNLOAD_DIR` | AI Chat 마크다운 다운로드 폴더 | ✅ |
| `LOG_FILE_PATH` | 로그 파일 경로 (기본: ./log/err.log) | ❌ |
| `EDITOR_COMMAND` | 에디터 명령어 (기본: nano) | ❌ |
| `FORCE_FULL_COLLECTION` | 강제 30일 수집 (true/false) | ❌ |

---

## 의존성

- Python 3.8+
- GitHub Personal Access Token
- Gemini API Key
- AI Chat Exporter Chrome Extensions:
  - [Claude Exporter](https://chromewebstore.google.com/detail/claude-exporter/elhmfakncmnghlnabnolalcjkdpfjnin)
  - [ChatGPT Exporter](https://chromewebstore.google.com/detail/chatgpt-exporter/pldlpacbeonbjfhlongcdflcgfcnglkl)
  - [Gemini Chat Exporter](https://chromewebstore.google.com/detail/gemini-chat-exporter/bhmoomcflhcfhingnjjieheeadmdefkc)

---

## 라이선스

[MIT License](LICENSE)
