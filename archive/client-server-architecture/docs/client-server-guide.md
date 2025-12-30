# Client-Server Mode (클라이언트-서버 모드)

## 📖 개요

**노트북/데스크탑**과 **라즈베리파이**를 분리하여 자동화를 극대화하는 방식입니다.

```
┌──────────────────────┐          ┌──────────────────────┐
│  노트북/데스크탑      │          │  라즈베리파이 (서버)  │
│  (Client)            │          │  (Server)            │
│                      │          │                      │
│  ┌────────────────┐ │          │  ┌────────────────┐  │
│  │ Client Agent   │ │  HTTP    │  │ FastAPI Server │  │
│  │ - Downloads    │ │  ────▶   │  │ - 파일 수신    │  │
│  │   감시         │ │  POST    │  │ - 파싱         │  │
│  │ - 파일 전송    │ │          │  │ - DB 저장      │  │
│  └────────────────┘ │          │  └────────────────┘  │
│                      │          │                      │
│  ┌────────────────┐ │          │  ┌────────────────┐  │
│  │ 로컬 큐        │ │          │  │ main.py (cron) │  │
│  │ - pending/     │ │          │  │ - GitHub       │  │
│  │ - sent/        │ │          │  │ - Baekjoon     │  │
│  │ - failed/      │ │          │  └────────────────┘  │
│  └────────────────┘ │          │                      │
│                      │          │  ┌────────────────┐  │
│                      │          │  │ PostgreSQL     │  │
│                      │          │  └────────────────┘  │
└──────────────────────┘          └──────────────────────┘
```

---

## ✅ 이런 경우 적합

- ✅ 노트북에서 AI 채팅 다운로드 자주 함
- ✅ 수동 파일 복사 귀찮음
- ✅ 자동화 극대화 원함
- ✅ 오프라인 대응 필요 (외부에서 작업 시)
- ✅ 원본 파일 자동 백업 원함

---

## 🏗️ 시스템 구성

### Server (라즈베리파이)
- **FastAPI 서버** (port 8000) - AI 채팅 파일 수신 및 처리
- **main.py (cron)** - GitHub/Baekjoon 수집 (기존 방식 유지)
- **PostgreSQL** - 데이터 저장

### Client (노트북/데스크탑)
- **Client Agent** - Downloads 폴더 감시 및 파일 전송
- **로컬 큐** - 전송 실패 시 보관 및 재시도

---

## 🚀 설치 가이드

### 1️⃣ Server 설정 (라즈베리파이)

#### 1-1. 의존성 설치

```bash
cd /home/jcw/LearningETL
git pull

# Server 의존성 설치
pip install -r requirements-server.txt
```

**requirements-server.txt 포함 패키지:**
- fastapi (웹 서버)
- uvicorn (ASGI 서버)
- python-multipart (파일 업로드)
- requests (GitHub API)
- psycopg2-binary (PostgreSQL)
- python-dotenv (환경변수)
- watchdog (파일 감시)

#### 1-2. FastAPI 서버 실행

**테스트 실행:**
```bash
# 방법 1: Python으로 직접
python server/api.py

# 방법 2: uvicorn 직접
uvicorn server.api:app --host 0.0.0.0 --port 8000
```

**확인:**
- 브라우저: http://raspberrypi.local:8000
- API 문서: http://raspberrypi.local:8000/docs
- 헬스 체크: `curl http://raspberrypi.local:8000/health`

#### 1-3. systemd 서비스 등록 (자동 시작)

```bash
sudo nano /etc/systemd/system/learningetl-server.service
```

```ini
[Unit]
Description=LearningETL FastAPI Server
After=network.target postgresql.service

[Service]
Type=simple
User=jcw
WorkingDirectory=/home/jcw/LearningETL
Environment="PATH=/home/jcw/LearningETL/venv/bin"
ExecStart=/home/jcw/LearningETL/venv/bin/uvicorn server.api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable learningetl-server
sudo systemctl start learningetl-server

# 상태 확인
sudo systemctl status learningetl-server

# 로그 확인
sudo journalctl -u learningetl-server -f
```

#### 1-4. 기존 cron 유지

GitHub/Baekjoon 수집은 기존 방식 그대로:

```bash
crontab -e
```

```cron
# 매일 오전 6시에 GitHub/Baekjoon 수집
0 6 * * * cd /home/jcw/LearningETL && /home/jcw/LearningETL/venv/bin/python main.py >> logs/cron.log 2>&1
```

---

### 2️⃣ Client 설정 (노트북/데스크탑)

#### 2-1. 프로젝트 설치

```bash
# 방법 1: 전체 클론
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 방법 2: client/ 폴더만 복사 (경량)
# server에서:
scp -r client/ user@laptop:/path/to/LearningETL/
scp requirements-client.txt user@laptop:/path/to/LearningETL/
```

#### 2-2. 의존성 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Client 의존성만 설치
pip install -r requirements-client.txt
```

**requirements-client.txt 포함 패키지:**
- requests (HTTP 통신)
- watchdog (파일 감시)

#### 2-3. 라즈베리파이 IP 확인

**라즈베리파이에서:**
```bash
hostname -I
# 예: 192.168.1.100
```

#### 2-4. Client Agent 실행

```bash
# 방법 1: IP 주소 사용
python client/agent.py --server http://192.168.1.100:8000

# 방법 2: 호스트명 사용 (mDNS 지원 시)
python client/agent.py --server http://raspberrypi.local:8000

# Downloads 폴더 커스텀
python client/agent.py \
  --server http://raspberrypi.local:8000 \
  --download-dir ~/다운로드
```

**예상 출력:**
```
============================================================
LearningETL Client Agent 시작
============================================================
서버: http://raspberrypi.local:8000
감시 폴더: /Users/user/Downloads
큐 폴더: /Users/user/.learningetl/queue
============================================================
서버 연결 성공: http://raspberrypi.local:8000
기존 파일 스캔 중: /Users/user/Downloads
파일 감시 시작
```

#### 2-5. 백그라운드 실행 (선택)

**Linux/Mac:**
```bash
nohup python client/agent.py \
  --server http://raspberrypi.local:8000 \
  > client.log 2>&1 &

# 프로세스 확인
ps aux | grep agent.py
```

**Windows (작업 스케줄러):**
1. `작업 스케줄러` 열기
2. `기본 작업 만들기`
3. 트리거: `컴퓨터 시작 시`
4. 작업:
   - 프로그램: `C:\...\venv\Scripts\python.exe`
   - 인수: `client\agent.py --server http://192.168.1.100:8000`
   - 시작 위치: `C:\...\LearningETL`

---

## 🧪 테스트

### 1. Server 연결 테스트

```bash
# 헬스 체크
curl http://raspberrypi.local:8000/health

# 예상 응답
{"status":"healthy","timestamp":"2025-12-29T12:00:00"}

# 서버 통계
curl http://raspberrypi.local:8000/api/stats
```

### 2. 파일 업로드 테스트

```bash
# 테스트 파일 생성
echo "# Test Conversation

**User:**
Hello

**Assistant:**
Hi there!" > test-claude-export.md

# 수동 업로드
curl -X POST http://raspberrypi.local:8000/api/upload \
  -F "file=@test-claude-export.md"

# 예상 응답
{
  "success": true,
  "filename": "test-claude-export.md",
  "size": 123,
  "md5": "abc123...",
  "message": "파일이 처리 중입니다"
}
```

### 3. Client Agent 테스트

**터미널 1: Agent 실행**
```bash
python client/agent.py --server http://raspberrypi.local:8000
```

**터미널 2: 테스트 파일 생성**
```bash
# AI 채팅 파일 패턴으로 생성
cp test-claude-export.md ~/Downloads/Claude-Export-Test.md
```

**예상 동작:**
1. Agent 로그: "AI 채팅 파일 감지: Claude-Export-Test.md"
2. Agent 로그: "로컬 큐에 추가"
3. Agent 로그: "파일 전송 중..."
4. Agent 로그: "전송 성공"
5. Server 로그: "파일 수신 완료"
6. Server 로그: "파일 처리 완료"

---

## 📊 사용 흐름

### 일상적인 사용

1. **노트북에서 Claude/ChatGPT 사용**
2. **대화 내보내기** → `~/Downloads/Claude-Export.md`
3. **Client Agent가 자동 감지** (1초 이내)
4. **로컬 큐에 복사** (`~/.learningetl/queue/pending/`)
5. **10초 이내 서버로 전송**
6. **서버에서 자동 파싱 + DB 저장**
7. **전송 완료 파일은 sent/ 폴더로 백업**

### 오프라인 시나리오

1. **노트북이 WiFi에 연결 안 됨**
2. **AI 채팅 다운로드** → 로컬 큐에 보관
3. **WiFi 연결 시** → 자동으로 서버에 전송

---

## 🔍 모니터링

### Server 로그

```bash
# FastAPI 서버 로그
tail -f logs/server.log

# AI Chat Collector 로그
tail -f logs/ai_chat_collector.log

# systemd 로그
sudo journalctl -u learningetl-server -f -n 100

# 에러만 보기
sudo journalctl -u learningetl-server -p err -f
```

### Client 로그

```bash
# 포그라운드 실행 시: 콘솔에 직접 출력

# 백그라운드 실행 시
tail -f client.log
```

### 로컬 큐 상태

```bash
# 전송 대기 중
ls -lh ~/.learningetl/queue/pending/

# 전송 완료 (백업)
ls -lh ~/.learningetl/queue/sent/

# 전송 실패 (재시도 대기)
ls -lh ~/.learningetl/queue/failed/
```

### DB 확인

```sql
-- 오늘 업로드된 AI 대화
SELECT
    id, provider, title, created_at
FROM learning.ai_conversations
WHERE DATE(created_at) = CURRENT_DATE
ORDER BY created_at DESC;

-- 최근 1시간 아티팩트
SELECT
    artifact_type,
    COUNT(*) as count
FROM learning.learning_artifacts
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY artifact_type;
```

---

## 🐛 트러블슈팅

### 서버 연결 실패

**증상:** Client Agent에서 "서버 연결 실패"

**해결:**
```bash
# 1. 서버 실행 확인
sudo systemctl status learningetl-server

# 2. 포트 리스닝 확인
sudo netstat -tlnp | grep 8000

# 3. 방화벽 확인 (필요시)
sudo ufw status
sudo ufw allow 8000

# 4. 네트워크 연결 확인
ping raspberrypi.local
```

### 파일 전송 실패

**증상:** 파일이 failed/ 폴더에 쌓임

**해결:**
```bash
# 1. Server 로그 확인
tail -50 logs/server.log | grep ERROR

# 2. 수동 전송 테스트
curl -X POST http://raspberrypi.local:8000/api/upload \
  -F "file=@~/.learningetl/queue/failed/파일명.md"

# 3. Agent 재시작 (자동 재시도)
pkill -f "client/agent.py"
python client/agent.py --server http://raspberrypi.local:8000
```

### 파싱 실패

**증상:** Server 로그에 "파일 처리 실패"

**해결:**
```bash
# 1. Server 에러 로그 확인
tail -100 logs/ai_chat_collector.log | grep ERROR

# 2. 원본 파일 확인 (클라이언트 sent/ 폴더에 백업됨)
cat ~/.learningetl/queue/sent/문제파일.md

# 3. 파일 형식 확인
head -20 ~/.learningetl/queue/sent/문제파일.md
```

### Agent가 파일을 감지 안 함

**증상:** Downloads에 파일 있는데 전송 안 됨

**해결:**
```bash
# 1. 파일명 확인 (AI 채팅 패턴 포함 여부)
ls ~/Downloads/*.md

# AI 채팅 패턴: Claude-Export, ChatGPT-Export, Gemini-Chat

# 2. Agent 로그 확인
# "AI 채팅 파일 감지" 메시지 있는지

# 3. 수동으로 큐에 추가
cp ~/Downloads/파일명.md ~/.learningetl/queue/pending/

# 4. Agent 재시작
```

---

## 📈 성능 최적화

### Server

```bash
# Worker 수 증가 (CPU 코어 수만큼)
uvicorn server.api:app --host 0.0.0.0 --port 8000 --workers 2

# 임시 업로드 폴더 정리 (cron)
0 3 * * * find /home/jcw/LearningETL/uploads/temp -type f -mtime +1 -delete
```

### Client

**큐 처리 주기 조정:**
```python
# client/agent.py 수정
# 기본: time.sleep(10)  # 10초
# 빠르게: time.sleep(5)  # 5초
# 느리게: time.sleep(30)  # 30초
```

**sent 폴더 자동 정리:**
```bash
# crontab
0 3 * * * find ~/.learningetl/queue/sent -type f -mtime +30 -delete
```

---

## ⬇️ Standalone 모드로 돌아가기

Client-Server 모드가 복잡하다면 [Standalone 모드](standalone-guide.md)로 돌아갈 수 있습니다:

1. Server 서비스 중지: `sudo systemctl stop learningetl-server`
2. Client Agent 종료: `pkill -f client/agent.py`
3. 기존 방식으로 실행: `python main.py --ai-chat-scan`

기존 데이터는 그대로 유지됩니다.
