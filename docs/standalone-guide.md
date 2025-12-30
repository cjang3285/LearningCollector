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

- ✅ 라즈베리파이에서 모든 작업 수행
- ✅ AI 채팅을 수동으로 라즈베리파이에 복사
- ✅ 간단한 설정 원함
- ✅ 1대 머신만 사용

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

#### B. Cron 자동 실행

```bash
crontab -e
```

```cron
# 매일 오전 6시에 GitHub/Baekjoon 수집
0 6 * * * cd /home/jcw/LearningETL && /home/jcw/LearningETL/venv/bin/python main.py >> logs/cron.log 2>&1
```

---

## 📂 AI 채팅 수집 방법

### 옵션 1: 수동 복사

```bash
# 1. 노트북에서 AI 채팅 다운로드
# 2. scp로 라즈베리파이에 복사
scp ~/Downloads/Claude-Export.md pi@raspberrypi:/tmp/

# 3. 라즈베리파이에서 실행
python main.py --ai-chat /tmp/Claude-Export.md
```

### 옵션 2: Downloads 폴더 스캔

라즈베리파이가 데스크탑으로 사용될 때:

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

### GitHub API Rate Limit

```bash
# 남은 API 호출 횟수 확인
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/rate_limit
```

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
head -20 ~/Downloads/Claude-Export.md

# 수동 파싱 테스트
python -c "
from parse.ai_chat_parse import AIMarkdownParser
parser = AIMarkdownParser()
result = parser.parse_file('~/Downloads/Claude-Export.md')
print(result)
"
```

---

## 🔄 향후 확장 계획

더 편리한 자동화를 원한다면 [NAS 기반 아키텍처](NAS_ARCHITECTURE.md)를 참고하세요:

- ✅ WireGuard VPN으로 노트북-라즈베리파이 연결
- ✅ NAS 파일 공유로 자동 전송
- ✅ Docker Compose로 전체 스택 관리

**미래 구현 예정** - 현재는 Standalone 모드 사용을 권장합니다.
