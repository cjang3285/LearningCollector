# 클라이언트-서버 모드 완전 가이드
## 노트북(클라이언트) ↔ 라즈베리파이(서버)

---

## 🎯 아키텍처

```
노트북/데스크탑 (클라이언트)                라즈베리파이 (서버)
┌─────────────────────────┐              ┌──────────────────────────┐
│                         │              │                          │
│  Downloads/             │              │  FastAPI 서버            │
│  ├─ Claude-xxx.md       │              │  ├─ 파일 수신 (POST)     │
│  ├─ ChatGPT-xxx.md      │              │  ├─ MD5 체크섬 검증      │
│  └─ Gemini-xxx.md       │              │  └─ 백그라운드 처리      │
│                         │              │                          │
│  👇 watchdog 감지        │   HTTP       │  👇 파싱                 │
│                         │   Upload     │                          │
│  client/agent.py        ├──────────────►│  parse/ai_chat_parse.py  │
│  ├─ 파일 감지           │   (파일)     │  ├─ 제목, 메시지 추출    │
│  ├─ MD5 계산            │              │  ├─ 코드 블록 추출       │
│  ├─ 업로드              │              │  └─ 메타데이터 추출      │
│  └─ 로컬 큐 관리        │              │                          │
│     ├─ pending/         │              │  👇 저장                 │
│     ├─ sent/            │              │                          │
│     └─ failed/          │              │  storage/ai_chat_saver.py│
│                         │              │  ├─ JSON 파일 저장       │
│                         │              │  └─ PostgreSQL 저장      │
│                         │              │                          │
└─────────────────────────┘              └──────────────────────────┘
```

---

## 📦 Step 1: 라즈베리파이 (서버) 설정

### 1-1. SSH 접속
```bash
ssh user@raspberry-pi-ip
cd /path/to/LearningETL
```

### 1-2. 최신 코드 받기
```bash
git pull origin claude/review-code-tests-alignment-DtRbe
```

### 1-3. 서버 의존성 설치
```bash
# 가상환경 생성 (처음이면)
python3 -m venv venv
source venv/bin/activate

# 서버 전용 의존성 설치
pip install -r requirements-server.txt

# 설치 내용:
# - fastapi (웹 서버)
# - uvicorn (ASGI 서버)
# - python-multipart (파일 업로드)
# - requests (HTTP 클라이언트)
# - psycopg2-binary (PostgreSQL)
# - watchdog (파일 감시)
# - python-dotenv (.env 파일)
```

### 1-4. .env 파일 설정
```bash
cp .env.example .env
nano .env
```

**서버 .env 설정:**
```bash
# AI Chat 수집 활성화
COLLECT_AI_CHAT=true

# GitHub, Baekjoon (선택)
COLLECT_GITHUB=true
COLLECT_BAEKJOON=true
GITHUB_TOKEN=ghp_xxxxx
GITHUB_USERNAME=your_username
BAEKJOON_HANDLE=your_handle

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=my_blog
DB_USER=postgres
DB_PASSWORD=your_password

# 파일 저장 경로
ARTIFACT_DIR=./learning_artifacts
LOG_DIR=./logs
```

### 1-5. 데이터베이스 마이그레이션
```bash
# 기존 claude 데이터 삭제 & 새 구조로
bash scripts/clean-migrate-db.sh

# 입력:
# yes → 비밀번호 → DELETE
```

### 1-6. 서버 시작!
```bash
# 개발 모드 (테스트)
python server/api.py

# 출력:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Application startup complete.
```

**또는 백그라운드 실행:**
```bash
nohup python server/api.py > logs/server.log 2>&1 &

# PID 확인
ps aux | grep "server/api.py"

# 로그 확인
tail -f logs/server.log
```

### 1-7. 서버 동작 확인
```bash
# 별도 터미널에서
curl http://localhost:8000/health

# 출력:
# {"status":"healthy","service":"LearningETL Server"}
```

---

## 💻 Step 2: 노트북 (클라이언트) 설정

### 2-1. 프로젝트 클론
```bash
# 노트북에서
cd ~/Projects
git clone https://github.com/your-username/LearningETL.git
cd LearningETL
git checkout claude/review-code-tests-alignment-DtRbe
```

### 2-2. 클라이언트 의존성 설치
```bash
# 가상환경 생성
python3 -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 클라이언트 전용 의존성 설치
pip install -r requirements-client.txt

# 설치 내용:
# - requests (HTTP 업로드)
# - watchdog (파일 감시)
```

### 2-3. 클라이언트 설정 파일 생성
```bash
# Windows
copy client\config.example.json client\config.json
notepad client\config.json

# macOS/Linux
cp client/config.example.json client/config.json
nano client/config.json
```

**config.json 설정:**
```json
{
  "server_url": "http://raspberry-pi-ip:8000",
  "download_dir": "~/Downloads",
  "queue_dir": "./client_queue",
  "check_interval": 5,
  "retry_count": 3,
  "retry_delay": 5
}
```

**중요**: `raspberry-pi-ip`를 실제 라즈베리파이 IP 주소로 변경!

### 2-4. 클라이언트 시작!
```bash
python client/agent.py

# 출력:
# [INFO] AI Export Agent 시작
# [INFO] 서버: http://192.168.1.100:8000
# [INFO] 감시 폴더: /Users/you/Downloads
# [INFO] 로컬 큐: ./client_queue
# [INFO] 파일 감시 시작...
```

---

## 🎬 Step 3: 전체 플로우 테스트!

### 3-1. 테스트 파일 생성 (노트북에서)
```bash
cat > ~/Downloads/Claude-Test-Flow-2025-12-30.md << 'EOF'
# Test Client-Server Flow

**Created:** 2025-12-30T15:00:00Z
**Updated:** 2025-12-30T15:30:00Z
**Link:** [Open](https://claude.ai/chat/test-flow)

---

## Prompt:
클라이언트-서버 모드 잘 작동하나요?

## Response:
네, 정상 작동합니다!

```python
def test_client_server():
    print("Client → Server 업로드 성공!")
    print("파싱 완료!")
    print("DB 저장 완료!")
```

---

*Powered by Claude Exporter*
EOF
```

### 3-2. 자동 감지 확인 (노트북)
```
[INFO] AI 채팅 파일 감지: Claude-Test-Flow-2025-12-30.md
[INFO] MD5 계산: a1b2c3d4e5f6...
[INFO] 로컬 큐에 복사: client_queue/pending/20251230_150000_Claude-Test-Flow.md
[INFO] 서버로 업로드 중: http://192.168.1.100:8000/api/upload
[INFO] ✅ 업로드 성공! (서버 응답: 200)
[INFO] sent/로 이동: client_queue/sent/20251230_150000_Claude-Test-Flow.md
```

### 3-3. 서버 처리 확인 (라즈베리파이)
```bash
# 서버 로그
tail -f logs/server.log

# 출력:
# [INFO] POST /api/upload - 파일 수신: Claude-Test-Flow-2025-12-30.md
# [INFO] MD5 검증 통과: a1b2c3d4e5f6
# [INFO] 임시 파일 저장: /tmp/upload_xxx.md
# [INFO] 백그라운드 처리 시작
# [INFO] 감지된 제공자: claude
# [INFO] 파일 저장: learning_artifacts/2025/12/30/ai_chat_claude/...
# [INFO] [DB] learning_artifacts 저장: id=1
# [INFO] [DB] ai_chat_conversations 저장: id=1
# [INFO] ✅ 처리 완료: Claude-Test-Flow-2025-12-30.md
```

### 3-4. DB 확인
```bash
# 라즈베리파이에서
python cli.py list ai-chat

# 출력:
# ========================================
# AI Chat 대화 목록
# ========================================
#
# [2025-12-30] Claude
# Test Client-Server Flow
# - 메시지: 2개 (사용자: 1, AI: 1)
# - 코드: 1개 블록 (python)
# - 링크: https://claude.ai/chat/test-flow
```

---

## 🚀 Step 4: 실제 사용하기

### 노트북에서 작업
1. Claude/ChatGPT/Gemini에서 대화
2. Extension으로 다운로드 (~/Downloads에 .md 저장)
3. 클라이언트 자동 감지 & 업로드!

### 라즈베리파이에서 자동 처리
1. 파일 수신
2. 파싱
3. DB 저장
4. 완료!

### 어디서든 조회
```bash
# 라즈베리파이 SSH 접속
ssh pi@raspberry-pi-ip

# 오늘 통계
python cli.py stats

# AI Chat 목록
python cli.py list ai-chat --date 2025-12-30

# 특정 대화 보기
python cli.py show ai-chat 1
```

---

## 🔧 고급 설정

### systemd로 자동 시작 (라즈베리파이)

**서버 서비스 파일:**
```bash
sudo nano /etc/systemd/system/learningetl-server.service
```

```ini
[Unit]
Description=LearningETL Server
After=network.target postgresql.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/LearningETL
Environment="PATH=/home/pi/LearningETL/venv/bin"
ExecStart=/home/pi/LearningETL/venv/bin/python server/api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**활성화:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable learningetl-server
sudo systemctl start learningetl-server

# 상태 확인
sudo systemctl status learningetl-server

# 로그 확인
sudo journalctl -u learningetl-server -f
```

### 노트북 자동 시작

**Windows (작업 스케줄러):**
1. `Win+R` → `taskschd.msc`
2. 작업 만들기
3. 트리거: 로그온 시
4. 작업: `python client/agent.py`

**macOS (LaunchAgent):**
```bash
nano ~/Library/LaunchAgents/com.learningetl.client.plist
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.learningetl.client</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/you/LearningETL/venv/bin/python</string>
        <string>/Users/you/LearningETL/client/agent.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.learningetl.client.plist
```

---

## 🐛 트러블슈팅

### 클라이언트가 서버에 연결 안 됨
```bash
# 1. 서버 실행 확인 (라즈베리파이)
curl http://localhost:8000/health

# 2. 방화벽 확인
sudo ufw allow 8000

# 3. 네트워크 확인 (노트북)
ping raspberry-pi-ip
curl http://raspberry-pi-ip:8000/health

# 4. config.json의 server_url 확인 (노트북)
cat client/config.json
```

### 파일 업로드 실패
```bash
# 클라이언트 로그 확인 (노트북)
cat client_queue/failed/*.md

# 재시도
python client/agent.py --retry-failed
```

### 서버 처리 안 됨
```bash
# 서버 로그 확인 (라즈베리파이)
tail -100 logs/server.log
tail -100 logs/ai_chat_parse.log
tail -100 logs/ai_chat_saver.log

# DB 연결 확인
psql -d my_blog -c "SELECT 1"
```

---

## 📊 모니터링

### 실시간 모니터링 (라즈베리파이)
```bash
# tmux 사용
tmux new -s monitor

# 창 1: 서버 로그
tail -f logs/server.log

# 창 2: 클라이언트 연결 상태
watch -n 5 'netstat -an | grep :8000'

# 창 3: DB 통계
watch -n 10 'python cli.py stats'

# 창 전환: Ctrl+B, 숫자키
```

### 대시보드 (추후 추가)
```bash
# Web UI로 실시간 통계
python dashboard/app.py

# http://raspberry-pi-ip:5000 접속
```

---

## 🎯 성능 최적화

### 대량 파일 처리
```bash
# 노트북에서 한 번에 100개 업로드해도 OK
# 서버는 백그라운드로 순차 처리
```

### 네트워크 대역폭
```bash
# MD 파일은 보통 10-50KB
# 100개 = 5MB → 1Mbps 네트워크에서 40초
```

### DB 성능
```bash
# 인덱스 확인
psql -d my_blog -c "\di learning.*"

# 느린 쿼리 찾기
psql -d my_blog -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
"
```

---

## 🎉 완료!

이제 노트북에서 Claude로 코딩하고,
다운로드만 하면 라즈베리파이에서 자동으로:
1. 파일 수신 ✓
2. 파싱 ✓
3. DB 저장 ✓

**완전 자동화!** 🚀
