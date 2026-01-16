# LearningCollector

**간소화된 학습 데이터 수집 → 블로그 초안 생성 파이프라인**

매일의 학습 활동(GitHub 커밋, AI 채팅, 백준 풀이)을 자동 수집하여 Claude API로 블로그 포스트 초안을 생성합니다.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ 주요 특징

- **🔄 자동 수집**: GitHub 커밋, AI Chat 대화, Baekjoon 풀이
- **📝 블로그 초안 생성**: Claude API로 핵심 논점과 의사결정 추출
- **📁 파일 기반**: PostgreSQL 불필요, JSON 파일로 저장
- **⏰ 자동 실행**: systemd timer로 매일 자정 자동 실행

---

## 🚀 빠른 시작

### 1. 설치

```bash
# 클론
git clone https://github.com/cjang3285/LearningCollector.git
cd LearningCollector

# 자동 설치 (권장)
bash scripts/installation/install.sh

# 또는 수동 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # 환경변수 설정
```

### 2. 환경변수 설정 (.env)

```bash
# GitHub 설정
GITHUB_TOKEN=your_github_token
GITHUB_COMMIT_AUTHORS=JANG CHANWOOK,Claude  # 나 + AI

# Baekjoon 설정
BAEKJOON_HANDLE=your_handle
BAEKJOON_REPO=BaekjoonHub

# AI Chat 설정
AI_CHAT_DOWNLOAD_DIR=/home/user/Downloads

# Claude API (블로그 생성용)
ANTHROPIC_API_KEY=your_claude_api_key
```

### 3. 실행

```bash
# 오늘 데이터 수집
python main.py

# 블로그 초안 생성
python generate_post_draft.py

# 특정 날짜
python main.py --date 2026-01-15
python generate_post_draft.py --date 2026-01-15
```

---

## 📂 디렉토리 구조

```
LearningCollector/
├── main.py                    # 데이터 수집
├── generate_post_draft.py     # 블로그 초안 생성
│
├── data/
│   ├── 2026-01-16.json       # 수집 데이터
│   └── post_draft_2026-01-16.md  # 블로그 초안
│
├── load/                      # 데이터 수집
│   ├── github_load.py        # GitHub API
│   ├── ai_chat_load.py       # AI Chat 마크다운 스캔
│   └── baekjoon_load.py      # BaekjoonHub 레포
│
├── parse/                     # 데이터 파싱
│   ├── github_parse.py
│   ├── ai_chat_parse.py
│   └── baekjoon_parse.py
│
├── utils/
│   └── collection_tracker.py # 날짜 추적 (파일 기반)
│
└── scripts/
    ├── systemd/              # 자동 실행 설정
    └── runtime/
        └── daily-collect.sh  # 데이터 수집 + 블로그 생성
```

---

## 🔄 워크플로우

### 매일 자정 자동 실행 (systemd)

```
1. GitHub 커밋 수집 → data/{날짜}.json
2. AI Chat 마크다운 스캔 → 추가
3. Baekjoon 풀이 수집 → 추가
4. Claude API 호출 → data/post_draft_{날짜}.md
```

### 수집 데이터 구조 (data/2026-01-16.json)

```json
{
  "date": "2026-01-16",
  "timestamp": "2026-01-16T23:59:59",
  "github": {
    "commits": [...],
    "summary": {
      "total_commits": 3,
      "total_repos": 2,
      "languages": {"Python": 5, "JavaScript": 2}
    }
  },
  "ai_chat": {
    "conversations": [
      {
        "provider": "claude",
        "messages": [...],
        "code_blocks": [...]
      }
    ]
  },
  "baekjoon": {
    "solutions": [...]
  }
}
```

### 블로그 초안 (data/post_draft_2026-01-16.md)

```markdown
# 2026-01-16 학습 일지

## 오늘의 핵심 주제
[AI가 자동 생성한 요약]

## 주요 활동

### 개발 작업
[GitHub 커밋 기반 활동 요약]

### 학습 및 토론
[AI 대화의 핵심 논점 및 의사결정]
- 논의 주제: ...
- 주요 의사결정: ...
- 배운 점: ...

### 문제 해결
[백준 문제 풀이 요약]

## 오늘의 배움
[핵심 인사이트]

## 내일 할 일
[다음 학습 방향]
```

---

## ⚙️ 자동화 설정

### systemd timer 설정

```bash
# 자동 설치 시 설정됨
bash scripts/installation/setup-daily-timer.sh

# 상태 확인
systemctl status learningcollector-daily.timer

# 로그 확인
journalctl -u learningcollector-daily.service -f
```

### 수동 실행 (테스트용)

```bash
# 전체 실행
bash scripts/runtime/daily-collect.sh

# 수집만
python main.py

# 블로그 생성만
python generate_post_draft.py
```

---

## 📋 데이터 소스

| 소스 | 수집 방법 | 설정 |
|------|----------|------|
| **GitHub** | REST API | `GITHUB_TOKEN`, `GITHUB_COMMIT_AUTHORS` |
| **AI Chat** | 마크다운 파일 스캔 | `AI_CHAT_DOWNLOAD_DIR` |
| **Baekjoon** | BaekjoonHub 레포 | `BAEKJOON_HANDLE`, `BAEKJOON_REPO` |

### AI Chat 지원 형식

- Claude Exporter (Chrome Extension)
- ChatGPT Exporter
- Gemini Exporter

파일명: `Claude-chat.md`, `ChatGPT-conversation.md`, `Gemini-chat.md`

---

## 🛠️ 고급 사용법

### 특정 소스만 수집

```bash
# GitHub만
python main.py --skip-ai-chat --skip-baekjoon

# AI Chat만
python main.py --skip-github --skip-baekjoon
```

### Claude ZIP 마이그레이션 (일회성)

```bash
# 과거 대화 전체 임포트
python main.py --import-zip --all
```

---

## 📊 로그 및 디버깅

```bash
# 수집 로그
cat logs/cron_$(date +%Y-%m-%d).log

# 수집 결과
cat logs/collect_result_$(date +%Y-%m-%d).json

# 데이터 확인
cat data/$(date +%Y-%m-%d).json | jq

# 블로그 초안 확인
cat data/post_draft_$(date +%Y-%m-%d).md
```

---

## 🔧 트러블슈팅

### GitHub API Rate Limit

```bash
# Rate limit 확인
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

### Claude API 에러

- `ANTHROPIC_API_KEY` 확인
- API 크레딧 잔액 확인

### 파일 권한 에러

```bash
# 로그/데이터 디렉토리 권한 확인
chmod -R 755 logs/ data/
```

---

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 🙏 기여

Issue 및 Pull Request 환영합니다!

---

## 📝 변경 이력

최신 변경사항은 [docs/CHANGELOG.md](docs/CHANGELOG.md) 참조

---

**Made with ❤️ by cjang3285**
