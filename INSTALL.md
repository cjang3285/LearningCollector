# 설치 가이드 (E2E)

> LearningETL 파이프라인의 전체 설치 과정을 단계별로 안내합니다.

---

## 📋 사전 준비

### 1. 시스템 요구사항

- **OS**: Linux (Ubuntu 20.04+ 권장), macOS, Windows (WSL2)
- **Python**: 3.8 이상
- **PostgreSQL**: 12 이상
- **Git**: 2.0 이상

### 2. 필수 계정/토큰

- [x] **GitHub Personal Access Token** - [생성 방법](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
  - 권한: `repo` (전체), `user:email`
- [x] **PostgreSQL 접속 정보** - DB명, 사용자명, 비밀번호

### 3. 선택 사항

- [ ] **백준허브 Chrome 확장** - [설치](https://github.com/BaekjoonHub/BaekjoonHub)
- [ ] **AI 채팅 Exporter 확장**:
  - [Claude Exporter](https://chromewebstore.google.com/detail/claude-exporter/elhmfakncmnghlnabnolalcjkdpfjnin)
  - [ChatGPT Exporter](https://chromewebstore.google.com/detail/chatgpt-exporter/pldlpacbeonbjfhlongcdflcgfcnglkl)
  - [Gemini Chat Exporter](https://chromewebstore.google.com/detail/gemini-chat-exporter/bhmoomcflhcfhingnjjieheeadmdefkc)

---

## 🚀 설치 단계

### Step 1: PostgreSQL 설치 및 설정

#### Ubuntu/Debian

```bash
# PostgreSQL 설치
sudo apt update
sudo apt install postgresql postgresql-contrib

# PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# DB 및 사용자 생성
sudo -u postgres psql
```

```sql
-- DB 생성
CREATE DATABASE my_blog;

-- 사용자 생성 및 권한 부여
CREATE USER your_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE my_blog TO your_user;

-- 연결 확인
\c my_blog
\q
```

#### macOS (Homebrew)

```bash
brew install postgresql@15
brew services start postgresql@15
createdb my_blog
```

#### 연결 테스트

```bash
psql -h localhost -U your_user -d my_blog
```

---

### Step 2: 프로젝트 클론 및 의존성 설치

```bash
# 1. 레포지토리 클론
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 2. Python 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt
```

---

### Step 3: 환경 변수 설정

```bash
# 1. .env 파일 생성
cp .env.example .env

# 2. 편집
nano .env  # 또는 vim, code 등
```

**.env 설정 예시**:

```bash
# PostgreSQL 연결 정보
DB_HOST=localhost
DB_PORT=5432
DB_NAME=my_blog
DB_USER=your_user
DB_PASSWORD=your_password

# GitHub 설정
GITHUB_TOKEN=ghp_your_personal_access_token_here
GITHUB_USERNAME=your_github_username

# Collector 활성화 (true/false)
COLLECT_GITHUB=true
COLLECT_BAEKJOON=true

# AI 채팅 다운로드 폴더
AI_CHAT_DOWNLOAD_DIR=/home/your_user/Downloads

# 백준허브 레포 (선택)
BAEKJOON_REPO_PATH=/path/to/baekjoon_hub_repo
```

---

### Step 4: DB 스키마 생성

```bash
# SQL 스크립트 실행
psql -h localhost -U your_user -d my_blog -f scripts/create-schema.sql

# 또는 Python 헬퍼 스크립트 사용
python scripts/init-db.py
```

**스키마 확인**:

```bash
psql -h localhost -U your_user -d my_blog

# 테이블 확인
\dt learning.*

# 다음이 보여야 함:
# learning.learning_artifacts
# learning.github_commits
# learning.baekjoon_solutions
# learning.ai_chat_conversations
```

---

### Step 5: 설치 확인

```bash
# 1. main.py 실행 테스트 (도움말)
python main.py --help

# 2. CLI 테스트
python -m cli stats

# 3. 수집 테스트 (--date 옵션으로 안전하게)
python main.py --date 2025-12-30

# 성공 시 출력:
# ============================================================
# Learning Artifacts ETL - 2025-12-30
# ============================================================
# [GitHub] 데이터 수집 시작...
# ...
# 수집 완료
```

---

## 🔧 자동화 설정 (선택)

### 옵션 A: 실시간 파일 감지 (Daemon)

AI 채팅 파일 다운로드 즉시 처리

```bash
# 1. Daemon 설치
bash scripts/install-daemon.sh

# 2. 서비스 시작
sudo systemctl start learningetl
sudo systemctl enable learningetl  # 부팅 시 자동 시작

# 3. 상태 확인
sudo systemctl status learningetl

# 4. 로그 확인
tail -f ~/LearningETL/logs/daemon.log
```

---

### 옵션 B: 매일 자정 전체 스캔 (systemd timer 권장 ⭐)

```bash
# 1. Timer 설치
bash scripts/setup-daily-timer.sh

# 2. Timer 활성화
sudo systemctl enable learningetl-daily.timer
sudo systemctl start learningetl-daily.timer

# 3. 다음 실행 시각 확인
systemctl list-timers learningetl-daily.timer

# 4. 수동 실행 테스트
sudo systemctl start learningetl-daily.service

# 5. 로그 확인
journalctl -u learningetl-daily.service -f
```

**왜 systemd timer?**
- ✅ 시스템 재부팅 시 놓친 작업 자동 실행 (`Persistent=true`)
- ✅ `journalctl`로 통합 로그 관리
- ✅ 실행 상태 추적 및 실패 알림
- ✅ DB 준비 후 실행 (`After=postgresql.service`)

---

## 🧪 설치 검증

### 전체 흐름 테스트

```bash
# 1. GitHub 커밋 수집
python main.py --date 2025-12-30

# 2. AI 채팅 파일 수집 (다운로드 폴더 스캔)
python main.py --ai-chat-scan

# 3. DB 조회
python -m cli stats
python -m cli list github
python -m cli list ai-chat

# 4. 특정 대화 보기
python -m cli show ai-chat 1
```

---

## 🐛 트러블슈팅

### 1. PostgreSQL 연결 실패

**증상**: `psycopg2.OperationalError: could not connect to server`

**해결**:

```bash
# PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# 서비스 시작
sudo systemctl start postgresql

# 수동 연결 테스트
psql -h localhost -U your_user -d my_blog
```

---

### 2. GitHub API Rate Limit

**증상**: `403 Forbidden: rate limit exceeded`

**해결**:

```bash
# 현재 rate limit 확인
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit

# 토큰이 유효한지 확인
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/user
```

**참고**: 인증된 요청은 시간당 5,000회, 미인증은 60회

---

### 3. AI 채팅 파일 감지 안 됨

**증상**: `--ai-chat-scan` 실행 시 파일을 찾지 못함

**체크리스트**:

1. 파일명이 `Claude-`, `ChatGPT-`, `Gemini-`로 시작하는지 확인
2. 확장자가 `.md`인지 확인
3. `.env`의 `AI_CHAT_DOWNLOAD_DIR` 경로 확인

```bash
# 수동 확인
ls -la $AI_CHAT_DOWNLOAD_DIR/*.md

# 파일 존재 시 직접 지정
python main.py --ai-chat ~/Downloads/Claude-Conversation-*.md
```

---

### 4. 백준 풀이 수집 안 됨

**증상**: 백준 Collector가 데이터를 찾지 못함

**해결**:

1. 백준허브 Chrome 확장 설치 확인
2. `.env`의 `BAEKJOON_REPO_PATH` 경로 확인
3. 레포에 푸시된 문제 확인

```bash
# 레포 확인
ls -la $BAEKJOON_REPO_PATH

# 수동 경로 지정
BAEKJOON_REPO_PATH=/path/to/baekjoon python main.py
```

---

### 5. 의존성 설치 실패

**증상**: `pip install -r requirements.txt` 실패

**해결**:

```bash
# Python 버전 확인 (3.8 이상 필요)
python --version

# pip 업그레이드
pip install --upgrade pip

# 개별 패키지 설치
pip install psycopg2-binary requests python-dotenv watchdog PyYAML

# macOS에서 psycopg2 오류 시
brew install postgresql
pip install psycopg2-binary
```

---

## 📊 사용 예시

### 일일 사용 (매일 밤 자동 실행 설정 후)

```bash
# 아무것도 하지 않음! systemd timer가 자동으로 수집
# 다음날 아침 DB 조회만 하면 됨
python -m cli stats
```

### 수동 실행 (특정 날짜)

```bash
# 어제 데이터 수집
python main.py --date 2025-12-29

# 오늘 데이터 재수집
python main.py
```

### AI 채팅만 수집

```bash
# 다운로드 폴더 스캔
python main.py --ai-chat-scan

# 특정 파일 지정
python main.py --ai-chat ~/Downloads/Claude-*.md ~/Downloads/ChatGPT-*.md
```

---

## 🎓 다음 단계

설치가 완료되었습니다! 🎉

**더 알아보기**:
- [📖 README](README.md) - 전체 기능 및 사용법
- [🏗️ 아키텍처 가이드](docs/ARCHITECTURE_EVOLUTION.md) - SOLID 리팩토링 설명
- [🧩 설계 패턴](docs/DESIGN_PATTERNS.md) - Factory, Registry 패턴
- [🗄️ DB 가이드](docs/DATABASE_GUIDE.md) - DB 스키마 상세

**새 Collector 추가해보기**:
1. `ICollector` 인터페이스 구현
2. `config/collectors.yaml`에 등록
3. 즉시 사용 가능! (코드 수정 불필요)

**문제 발생 시**:
- [🐛 Issues](https://github.com/cjang3285/LearningETL/issues) - 버그 리포트
- [📖 Documentation](docs/) - 전체 문서

---

<div align="center">

**Happy Learning! 📚**

Made with ❤️ using SOLID principles

</div>
