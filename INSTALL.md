# 설치 가이드

LearningETL 파이프라인의 전체 설치 과정을 단계별로 안내합니다.

---

## 사전 준비

### 1. 시스템 요구사항

- **OS**: Linux (Ubuntu 20.04+ 권장), macOS, Windows (WSL2)
- **Python**: 3.8 이상
- **PostgreSQL**: 12 이상
- **Git**: 2.0 이상

### 2. 필수 계정/토큰

- **GitHub Personal Access Token** - [생성 방법](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
  - 권한: `repo` (전체), `user:email`
- **PostgreSQL 접속 정보** - DB명, 사용자명, 비밀번호
- **백준허브 Chrome 확장** - [설치](https://github.com/BaekjoonHub/BaekjoonHub)
- **AI 채팅 Exporter Chrome 확장**:
  - [Claude Exporter](https://chromewebstore.google.com/detail/claude-exporter/elhmfakncmnghlnabnolalcjkdpfjnin)
  - [ChatGPT Exporter](https://chromewebstore.google.com/detail/chatgpt-exporter/pldlpacbeonbjfhlongcdflcgfcnglkl)
  - [Gemini Chat Exporter](https://chromewebstore.google.com/detail/gemini-chat-exporter/bhmoomcflhcfhingnjjieheeadmdefkc)

---

## 설치 단계

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
CREATE DATABASE my_db;

-- 사용자 생성 및 권한 부여
CREATE USER your_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE my_db TO your_user;

-- 연결 확인
\c my_db
\q
```

#### 연결 테스트

```bash
psql -h localhost -U your_user -d my_db
```

---

### Step 2: 프로젝트 클론 및 의존성 설치

```bash
# 1. 레포지토리 클론
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 2. Python 가상환경 생성
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
DB_NAME=my_db
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

# 백준허브 레포
BAEKJOON_REPO_PATH=/path/to/baekjoon_hub_repo
```

---

### Step 4: DB 스키마 생성

```bash
# SQL 스크립트 실행
psql -h localhost -U your_user -d my_db -f scripts/create-schema.sql
```

**스키마 확인**:

```bash
psql -h localhost -U your_user -d my_db

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

# 3. 수집 테스트 (--date 옵션으로 날짜 제한)
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

## 자동화 설정

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

### 옵션 B: 매일 자정 전체 스캔 (systemd timer 권장)

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

**systemd timer 장점**:
- 시스템 재부팅 시 놓친 작업 자동 실행 (`Persistent=true`)
- `journalctl`로 통합 로그 관리
- 실행 상태 추적 및 실패 알림
- DB 준비 후 실행 (`After=postgresql.service`)

---

## 설치 검증

### 전체 흐름 테스트

```bash
# 1. 기본 실행 (GitHub + Baekjoon + AI Chat)
python main.py

# 2. 특정 날짜
python main.py --date 2025-12-30

# 3. DB 조회
python -m cli stats
python -m cli list github
python -m cli list ai-chat

# 4. 특정 대화 보기
python -m cli show ai-chat 1
```

---

## 트러블슈팅

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

### 2. AI 채팅 파일 감지 안 됨

**증상**: 파일을 찾지 못함

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

### 3. 백준 풀이 수집 안 됨

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

### 4. 의존성 설치 실패

**증상**: `pip install -r requirements.txt` 실패

**해결**:

```bash
# Python 버전 확인 (3.8 이상 필요)
python --version

# pip 업그레이드
pip install --upgrade pip

# 개별 패키지 설치
pip install psycopg2-binary requests python-dotenv watchdog PyYAML
```

---

### 5. 자동 수집이 작동하지 않을 때

**증상**: systemd timer를 설정했는데 데이터가 매일 수집되지 않음 (예: 어제 백준 문제를 풀었는데 오늘 DB에 없음)

#### 5.1 systemd timer 상태 확인

```bash
# Timer가 활성화되어 있는지 확인
systemctl list-timers learningetl-daily.timer

# 출력 예시 (정상):
# NEXT                         LEFT          LAST                         PASSED  UNIT                       ACTIVATES
# Wed 2025-12-31 00:00:00 KST  5h 23min left Tue 2025-12-30 00:00:05 KST  18h ago learningetl-daily.timer    learningetl-daily.service

# 위와 같이 NEXT, LAST가 표시되면 정상
# 아무것도 표시되지 않으면 timer가 비활성화됨
```

**Timer가 목록에 없을 경우**:

```bash
# Timer 활성화
sudo systemctl enable learningetl-daily.timer
sudo systemctl start learningetl-daily.timer

# 다시 확인
systemctl list-timers learningetl-daily.timer
```

#### 5.2 마지막 실행 로그 확인

```bash
# 최근 10개 로그 확인
journalctl -u learningetl-daily.service -n 10

# 오늘 로그만 확인
journalctl -u learningetl-daily.service --since today

# 실시간 로그 모니터링
journalctl -u learningetl-daily.service -f
```

**로그에서 확인할 사항**:
- 마지막 실행 시각이 어제 자정인지
- 에러 메시지가 있는지 (`[ERROR]`, `FAILED`)
- `[SUCCESS] 수집 성공` 메시지가 있는지

#### 5.3 수동 실행 테스트

```bash
# systemd service 수동 실행
sudo systemctl start learningetl-daily.service

# 실행 상태 확인
sudo systemctl status learningetl-daily.service

# 로그 확인
journalctl -u learningetl-daily.service -f
```

**성공 시 출력**:
```
[날짜 시각] ==========================================
[날짜 시각] LearningETL 일일 수집 시작
[날짜 시각] ==========================================
[날짜 시각] 작업 디렉토리: /home/user/LearningETL
...
[날짜 시각] [SUCCESS] 수집 성공
```

#### 5.4 DB에서 마지막 수집 날짜 확인

```bash
# CLI로 최근 데이터 확인
python -m cli stats

# 백준 최근 풀이 날짜 확인
python -m cli list baekjoon --limit 5

# GitHub 최근 커밋 날짜 확인
python -m cli list github --limit 5
```

**예상 출력**:
```
최근 7일

  2025-12-30:
    github           5개
    baekjoon        2개
    ai_chat         3개

  2025-12-29:
    ...
```

만약 어제 날짜가 누락되었다면 timer가 실행되지 않은 것입니다.

#### 5.5 자동 수집이 계속 실패하는 경우

**원인 1: 가상환경 경로 문제**

```bash
# learningetl-daily.service 파일 확인
sudo systemctl cat learningetl-daily.service

# ExecStart 경로가 올바른지 확인
# 출력 예시:
# ExecStart=/home/user/LearningETL/scripts/daily-collect.sh

# 스크립트 내부 가상환경 경로 확인
cat /home/user/LearningETL/scripts/daily-collect.sh | grep venv

# 경로가 틀렸다면 수정
nano /home/user/LearningETL/scripts/daily-collect.sh
```

**원인 2: 환경 변수 미설정**

```bash
# .env 파일이 있는지 확인
ls -la /home/user/LearningETL/.env

# 없으면 생성
cp /home/user/LearningETL/.env.example /home/user/LearningETL/.env
nano /home/user/LearningETL/.env
```

**원인 3: PostgreSQL 서비스 미실행**

```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# 실행 중이 아니면 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 5.6 systemd가 없는 환경 (Docker, WSL 등)

**증상**: `System has not been booted with systemd`

**해결**: cron 사용

```bash
# crontab 편집
crontab -e

# 다음 줄 추가 (매일 자정 실행)
0 0 * * * /home/user/LearningETL/scripts/daily-collect.sh

# crontab 확인
crontab -l

# cron 로그 확인 (Ubuntu/Debian)
grep CRON /var/log/syslog | tail -20
```

**또는 수동 실행**:

```bash
# 매일 아침 직접 실행
cd /home/user/LearningETL
source venv/bin/activate
python main.py
```

---

## 사용 예시

### 일일 사용 (매일 밤 자동 실행 설정 후)

```bash
# systemd timer가 자동으로 수집
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
# 기본 실행 (AI Chat 포함)
python main.py

# AI Chat 제외
python main.py --skip-ai-chat

# 특정 파일 지정
python main.py --ai-chat ~/Downloads/Claude-*.md ~/Downloads/ChatGPT-*.md
```

---

## 다음 단계

설치가 완료되었습니다.

**더 알아보기**:
- [README](README.md) - 전체 기능 및 사용법
- [아키텍처 가이드](docs/ARCHITECTURE_EVOLUTION.md) - SOLID 리팩토링 설명
- [설계 패턴](docs/DESIGN_PATTERNS.md) - Factory, Registry 패턴
- [DB 가이드](docs/DATABASE_GUIDE.md) - DB 스키마 상세

**새 Collector 추가해보기**:
1. `ICollector` 인터페이스 구현
2. `config/collectors.yaml`에 등록
3. 즉시 사용 가능 (코드 수정 불필요)

**문제 발생 시**:
- [Issues](https://github.com/cjang3285/LearningETL/issues) - 버그 리포트
- [Documentation](docs/) - 전체 문서

---
