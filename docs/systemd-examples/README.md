# systemd 서비스 파일 템플릿

이 폴더에는 LearningETL을 systemd로 자동 시작하기 위한 서비스 파일 템플릿이 있습니다.

## 📁 파일

- `learningetl-server.service` - Server (라즈베리파이)용
- `learningetl-client.service` - Client (노트북/데스크탑)용

## 🚀 사용 방법

### Server (라즈베리파이)

```bash
# 1. 파일 수정
nano docs/systemd-examples/learningetl-server.service
# User, WorkingDirectory, 가상환경 경로 변경

# 2. systemd로 복사
sudo cp docs/systemd-examples/learningetl-server.service /etc/systemd/system/

# 3. 활성화
sudo systemctl daemon-reload
sudo systemctl enable learningetl-server
sudo systemctl start learningetl-server

# 4. 상태 확인
sudo systemctl status learningetl-server

# 5. 로그 확인
sudo journalctl -u learningetl-server -f
```

### Client (노트북/데스크탑)

```bash
# 1. 파일 수정
nano docs/systemd-examples/learningetl-client.service
# User, WorkingDirectory, 서버 URL 변경

# 2. systemd로 복사
sudo cp docs/systemd-examples/learningetl-client.service /etc/systemd/system/

# 3. 활성화
sudo systemctl daemon-reload
sudo systemctl enable learningetl-client
sudo systemctl start learningetl-client

# 4. 상태 확인
sudo systemctl status learningetl-client

# 5. 로그 확인
sudo journalctl -u learningetl-client -f
```

## 🔧 필수 수정 항목

### Server 파일
- `User=jcw` → 본인 사용자명
- `WorkingDirectory=/home/jcw/LearningETL` → 본인 경로
- `Environment="PATH=/home/jcw/LearningETL/venv/bin"` → 본인 가상환경 경로
- `ExecStart=/home/jcw/LearningETL/venv/bin/uvicorn ...` → 본인 경로

### Client 파일
- `User=username` → 본인 사용자명
- `WorkingDirectory=/home/username/LearningETL` → 본인 경로
- `Environment="PATH=/home/username/LearningETL/venv/bin"` → 본인 가상환경 경로
- `ExecStart=... --server http://raspberrypi.local:8000` → 실제 서버 URL

## 📝 주의사항

- 서비스 파일 수정 후 반드시 `sudo systemctl daemon-reload` 실행
- 로그는 `journalctl`로 확인 (파일 로그는 `logs/` 폴더)
- 서비스 중지: `sudo systemctl stop learningetl-server`
- 서비스 비활성화: `sudo systemctl disable learningetl-server`
