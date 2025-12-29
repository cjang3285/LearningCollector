# LearningETL 배포 가이드

## 📦 시스템 구성

### 라즈베리파이 (서버)
- FastAPI 서버 실행 (포트 8000)
- PostgreSQL DB
- 매일 cron으로 GitHub/Baekjoon 수집

### 노트북/데스크탑 (클라이언트)
- Client Agent 실행
- Downloads 폴더 감시
- AI 채팅 파일 자동 업로드

---

## 🚀 설치 가이드

### 1. 라즈베리파이 설정

#### 1-1. 의존성 설치
```bash
cd /home/jcw/LearningETL

# 서버 의존성 설치
pip install -r requirements-server.txt
```

#### 1-2. FastAPI 서버 실행
```bash
# 수동 실행 (테스트)
python server/api.py

# 또는 uvicorn 직접 실행
uvicorn server.api:app --host 0.0.0.0 --port 8000

# 백그라운드 실행
nohup uvicorn server.api:app --host 0.0.0.0 --port 8000 > logs/server.log 2>&1 &
```

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

#### 1-4. 기존 cron 설정 유지
```bash
crontab -e
```

```cron
# 매일 오전 6시에 GitHub/Baekjoon 수집
0 6 * * * cd /home/jcw/LearningETL && /home/jcw/LearningETL/venv/bin/python main.py >> logs/cron.log 2>&1
```

---

### 2. 노트북/데스크탑 설정

#### 2-1. 의존성 설치
```bash
# 프로젝트 클론 (또는 client/ 폴더만 복사)
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 클라이언트 의존성만 설치
pip install -r requirements-client.txt
```

#### 2-2. Client Agent 실행
```bash
# 라즈베리파이 IP 주소 확인 (파이에서 실행)
hostname -I

# Client Agent 실행
python client/agent.py --server http://192.168.1.100:8000

# 또는 호스트명 사용
python client/agent.py --server http://raspberrypi.local:8000
```

#### 2-3. 백그라운드 실행 (선택)

**Linux/Mac:**
```bash
nohup python client/agent.py --server http://raspberrypi.local:8000 > client.log 2>&1 &
```

**Windows (작업 스케줄러):**
1. 작업 스케줄러 열기
2. 기본 작업 만들기
3. 트리거: "컴퓨터 시작 시"
4. 작업: `C:\...\venv\Scripts\python.exe client\agent.py --server http://192.168.1.100:8000`

---

## 🔧 설정 파일

### 라즈베리파이 `.env`
```bash
# GitHub
GITHUB_TOKEN=ghp_xxxxx
GITHUB_USERNAME=cjang3285
COLLECT_GITHUB=true

# Baekjoon
BAEKJOON_HANDLE=your_handle
COLLECT_BAEKJOON=true

# DB
DB_HOST=localhost
DB_PORT=5432
DB_NAME=learning
DB_USER=learning_user
DB_PASSWORD=your_password
```

### 클라이언트 (설정 불필요)
- 환경변수 없음
- `--server` 인자로 서버 URL만 지정

---

## 📊 사용 흐름

### 일상 사용
1. **노트북에서 Claude/ChatGPT 사용**
2. **대화 마크다운으로 내보내기** → `~/Downloads/Claude-Export.md`
3. **Client Agent가 자동 감지** → 로컬 큐에 추가
4. **10초마다 서버로 전송** → 파이에서 파싱 + DB 저장
5. **확인**: 파이 로그 또는 DB 쿼리

### 수동 업로드 (curl)
```bash
curl -X POST http://raspberrypi.local:8000/api/upload \
  -F "file=@Claude-Export.md" \
  -F "md5=$(md5sum Claude-Export.md | cut -d' ' -f1)"
```

---

## 🧪 테스트

### 1. 서버 연결 테스트
```bash
# 헬스 체크
curl http://raspberrypi.local:8000/health

# 응답: {"status":"healthy","timestamp":"..."}
```

### 2. 파일 업로드 테스트
```bash
# 테스트 마크다운 파일 생성
echo "# Test Conversation" > test-claude-export.md

# 업로드
curl -X POST http://raspberrypi.local:8000/api/upload \
  -F "file=@test-claude-export.md"

# 파이 로그 확인
tail -f logs/server.log
```

### 3. Client Agent 테스트
```bash
# 에이전트 실행
python client/agent.py --server http://raspberrypi.local:8000

# 다른 터미널에서 테스트 파일 생성
cp test-claude-export.md ~/Downloads/Claude-Export-Test.md

# 에이전트 로그 확인 (자동 업로드 확인)
```

---

## 🔍 모니터링

### 서버 로그
```bash
# FastAPI 서버 로그
tail -f logs/server.log

# AI Chat Collector 로그
tail -f logs/ai_chat_collector.log

# Systemd 로그
sudo journalctl -u learningetl-server -f
```

### 클라이언트 로그
```bash
# Client Agent 로그
tail -f client.log
```

### DB 확인
```sql
-- 최근 업로드된 AI 대화
SELECT
    id, provider, title, created_at
FROM learning.ai_conversations
ORDER BY created_at DESC
LIMIT 10;

-- 오늘 수집된 전체 아티팩트
SELECT
    artifact_type, COUNT(*) as count
FROM learning.learning_artifacts
WHERE artifact_date = CURRENT_DATE
GROUP BY artifact_type;
```

---

## 🐛 트러블슈팅

### 서버 연결 안 됨
```bash
# 1. 서버 실행 확인
sudo systemctl status learningetl-server

# 2. 포트 리스닝 확인
sudo netstat -tlnp | grep 8000

# 3. 방화벽 확인 (필요시)
sudo ufw allow 8000
```

### 파일 전송 실패
```bash
# 1. 클라이언트 큐 확인
ls -lh ~/.learningetl/queue/pending/
ls -lh ~/.learningetl/queue/failed/

# 2. 실패한 파일 재시도
# Client Agent 재시작하면 자동으로 재시도
```

### 파싱 실패
```bash
# 1. 서버 로그 확인
tail -100 logs/server.log | grep ERROR

# 2. 원본 파일 확인 (sent/ 폴더에 백업됨)
ls -lh ~/.learningetl/queue/sent/
```

---

## 📈 성능 최적화

### 서버
- **worker 수 증가**: `uvicorn --workers 2`
- **업로드 디렉토리 정리**: 주기적으로 `/uploads/temp/` 정리

### 클라이언트
- **큐 처리 주기 조정**: `client/agent.py` 의 `time.sleep(10)` 수정
- **sent 폴더 정리**: 30일 이상 파일 삭제

---

## 🚧 향후 확장

### Docker 배포 (Phase 3)
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements-server.txt
CMD ["uvicorn", "server.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  server:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: learning
```

### 클라이언트 실행파일 (PyInstaller)
```bash
# Windows/Mac/Linux 실행파일 빌드
pip install pyinstaller
pyinstaller --onefile --name learningetl-client client/agent.py

# 결과: dist/learningetl-client.exe (약 8MB)
```
