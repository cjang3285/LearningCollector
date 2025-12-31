# Standalone Mode (단독 실행 모드)

## 📖 개요

**한 대의 머신**에서 모든 ETL 작업을 수행하는 전통적인 방식입니다.

```
┌────────────────────────────────┐
│  라즈베리파이 (또는 단일 서버)  │
│                                 │
│  ┌──────────────────────────┐  │
│  │  main.py (매일 실행)     │  │
│  │  - GitHub 커밋 수집      │  │
│  │  - Baekjoon 풀이 수집    │  │
│  └──────────────────────────┘  │
│                                 │
│  ┌──────────────────────────┐  │
│  │  수동 AI Chat 수집       │  │
│  │  --ai-chat-scan          │  │
│  └──────────────────────────┘  │
│                                 │
│  ┌──────────────────────────┐  │
│  │  PostgreSQL              │  │
│  └──────────────────────────┘  │
└────────────────────────────────┘
```

---

## ✅ 이런 경우 적합

-  한 머신에서 모든 작업 수행
-  AI 채팅을 해당 머신의 특정 디렉터리에 복사 가능한 상황
-  간단한 설정 원함
-  1대 머신만 사용

---

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
cd LearningETL
pip install -r requirements.txt
```

**requirements.txt 포함 패키지:**
- requests (GitHub API)
- psycopg2-binary (PostgreSQL)
- python-dotenv (환경변수)
- watchdog (파일 감시)

### 2. 환경 변수 설정

`.env` 파일 생성:

```bash
# GitHub
GITHUB_TOKEN=ghp_xxxxx
GITHUB_USERNAME=your_username
COLLECT_GITHUB=true

# Baekjoon
BAEKJOON_HANDLE=your_handle
COLLECT_BAEKJOON=true

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=learning
DB_USER=learning_user
DB_PASSWORD=your_password
```

### 3. 실행 방법

#### A. 수동 실행 (테스트)

```bash
# GitHub + Baekjoon 수집
python main.py

# 특정 날짜
python main.py --date 2025-12-25

# AI 채팅 파일 포함
python main.py --ai-chat ~/Downloads/Claude-Export.md

# AI 채팅 다운로드 폴더 스캔
python main.py --ai-chat-scan
```

#### B. 주기적으로 자동 실행
-> 수정 필요.
```bash
crontab -e
```

```cron
# 매일 오전 6시에 GitHub/Baekjoon 수집
0 6 * * * cd /home/jcw/LearningETL && /home/jcw/LearningETL/venv/bin/python main.py >> logs/cron.log 2>&1
```

---

## 📂 AI 채팅 수집 방법

### Downloads 폴더 스캔

readme.md에서 다룬 ai chat exporter들을 사용 시 파일들은 특정 접두사들을 가지게 됩니다.
지정해둔 폴더에서 해당 접두사들(Claude-, Gemini-, ChatGPT-)을 가지는 파일들을 감지합니다.

```bash
# Downloads 폴더에서 AI 채팅 파일 자동 감지
python main.py --ai-chat-scan

# 특정 폴더 지정
python main.py --ai-chat-scan --download-dir /home/user/Downloads
```

---

## 🔍 로그 확인

```bash
# 메인 로그
tail -f logs/main.log

# GitHub 수집 로그
tail -f logs/github_collector.log

# Baekjoon 수집 로그
tail -f logs/baekjoon_collector.log

# AI Chat 수집 로그
tail -f logs/ai_chat_collector.log
```

---

## 📊 DB 확인

```sql
-- 오늘 수집된 아티팩트
SELECT
    artifact_type,
    COUNT(*) as count
FROM learning.learning_artifacts
WHERE artifact_date = CURRENT_DATE
GROUP BY artifact_type;

-- GitHub 커밋
SELECT repo, message, commit_date
FROM learning.github_commits
WHERE DATE(commit_date) = CURRENT_DATE
ORDER BY commit_date DESC;

-- AI 대화
SELECT provider, title, created_at
FROM learning.ai_conversations
WHERE DATE(created_at) = CURRENT_DATE
ORDER BY created_at DESC;

-- 백준 풀이
SELECT problem_number, title, tier, language
FROM learning.baekjoon_solutions
WHERE DATE(solved_date) = CURRENT_DATE
ORDER BY solved_date DESC;
```

---

## 🐛 트러블슈팅

### DB 연결 실패

```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# DB 접속 테스트
psql -h localhost -U learning_user -d learning
```

### AI 채팅 파일 파싱 실패

```bash
# 파일 형식 확인
head -20 ~/Downloads/Claude-yourmdname.md

# 수동 파싱 테스트
python -c "
from parse.ai_chat_parse import AIMarkdownParser
parser = AIMarkdownParser()
result = parser.parse_file('~/Downloads/Claude-Export.md')
print(result)
"
```

---
