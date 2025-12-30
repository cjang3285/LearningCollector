# NAS 기반 아키텍처
## WireGuard VPN + NAS를 활용한 파일 전송

---

## 🏗️ 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    WireGuard VPN Tunnel                     │
│  (노트북 ↔ 라즈베리파이 ↔ NAS 모두 연결됨)                │
└─────────────────────────────────────────────────────────────┘
           ↓                    ↓                    ↓

노트북 (클라이언트)          NAS (공유 스토리지)       라즈베리파이 (서버)
┌──────────────────┐         ┌──────────────────┐    ┌───────────────────┐
│  Downloads/      │         │  /volume1/       │    │  watchdog         │
│  Claude-xxx.md   │         │  learningetl/    │    │  감시 시작        │
│                  │         │  ├─ inbox/       │    │                   │
│  👇 watchdog     │  SMB/   │  ├─ processing/  │    │  👇 파일 발견     │
│     감지         │  NFS    │  ├─ completed/   │    │                   │
│                  │  Mount  │  └─ failed/      │    │  parser/          │
│  client/         ├────────►│                  │◄───┤  ai_chat_parse.py │
│  nas_agent.py    │  복사   │  ✓ 중앙 저장소   │    │                   │
│  ├─ 파일 감지    │         │  ✓ 동기화        │    │  👇 파싱 완료     │
│  ├─ NAS 복사    │         │  ✓ 이력 관리     │    │                   │
│  └─ inbox/이동   │         │                  │    │  storage/         │
│                  │         │                  │    │  ai_chat_saver.py │
│  ✓ HTTP 불필요   │         │                  │    │  ├─ JSON 저장     │
│  ✓ 간단한 구조   │         │                  │    │  └─ PostgreSQL    │
└──────────────────┘         └──────────────────┘    └───────────────────┘
```

---

## 🎯 왜 NAS 방식?

### HTTP 업로드 방식의 한계
```
❌ FastAPI 서버 필요 (포트 개방, 관리)
❌ 네트워크 에러 처리 복잡
❌ 재시도 로직 필요
❌ MD5 계산 & 검증 오버헤드
```

### NAS 방식의 장점
```
✅ 파일 시스템 기반 (간단!)
✅ NAS가 자동 동기화
✅ WireGuard VPN으로 보안
✅ 실패 시 재처리 쉬움
✅ 파일 이력 자동 관리
✅ 서버 다운되어도 파일 보존
```

---

## 📁 NAS 디렉토리 구조

```
/volume1/learningetl/           # NAS 공유 폴더
├── inbox/                      # 클라이언트가 파일 업로드
│   ├── Claude-xxx.md
│   ├── ChatGPT-yyy.md
│   └── ...
│
├── processing/                 # 서버가 처리 중
│   └── Claude-xxx.md
│
├── completed/                  # 처리 완료
│   ├── 2025-12-30/
│   │   ├── Claude-xxx.md
│   │   └── ChatGPT-yyy.md
│   └── ...
│
├── failed/                     # 처리 실패
│   ├── Claude-error.md
│   └── error.log
│
└── metadata/                   # 메타데이터
    ├── processed.json          # 처리 이력
    └── stats.json              # 통계
```

---

## 💻 클라이언트 (노트북) 설정

### 1. NAS 마운트

**Windows:**
```batch
REM NAS를 Z: 드라이브로 마운트
net use Z: \\nas-ip\learningetl /user:your-user your-password /persistent:yes

REM 또는 파일 탐색기에서:
REM \\nas-ip\learningetl 접속 → 네트워크 드라이브 연결
```

**macOS:**
```bash
# NAS 마운트
mkdir -p ~/nas
mount_smbfs //your-user@nas-ip/learningetl ~/nas

# 또는 Finder:
# Cmd+K → smb://nas-ip/learningetl
```

**Linux:**
```bash
# SMB 마운트
sudo mkdir -p /mnt/nas
sudo mount -t cifs //nas-ip/learningetl /mnt/nas \
  -o username=your-user,password=your-password

# 또는 NFS
sudo mount -t nfs nas-ip:/volume1/learningetl /mnt/nas

# /etc/fstab에 추가 (자동 마운트):
//nas-ip/learningetl /mnt/nas cifs username=your-user,password=your-password,uid=1000,gid=1000 0 0
```

### 2. 클라이언트 설정

**config.json:**
```json
{
  "nas_mount_point": "/mnt/nas",
  "nas_inbox": "inbox",
  "download_dir": "~/Downloads",
  "ai_chat_patterns": [
    "Claude-*.md",
    "ChatGPT-*.md",
    "Gemini-*.md"
  ],
  "check_interval": 5
}
```

### 3. 클라이언트 실행

```bash
# NAS 기반 클라이언트
python client/nas_agent.py

# 출력:
# [INFO] NAS Agent 시작
# [INFO] NAS 마운트 포인트: /mnt/nas
# [INFO] Inbox: /mnt/nas/inbox
# [INFO] Downloads 감시: /Users/you/Downloads
# [INFO] 파일 감시 시작...
#
# [INFO] AI 채팅 파일 감지: Claude-Test.md
# [INFO] NAS inbox로 복사: /mnt/nas/inbox/Claude-Test.md
# [INFO] ✅ 업로드 완료!
```

---

## 🖥️ 서버 (라즈베리파이) 설정

### 1. NAS 마운트

```bash
# SMB 마운트
sudo mkdir -p /mnt/nas
sudo apt-get install -y cifs-utils

# 마운트
sudo mount -t cifs //nas-ip/learningetl /mnt/nas \
  -o username=your-user,password=your-password,uid=pi,gid=pi

# /etc/fstab에 추가 (자동 마운트)
echo "//nas-ip/learningetl /mnt/nas cifs username=your-user,password=your-password,uid=1000,gid=1000 0 0" | sudo tee -a /etc/fstab
```

### 2. 서버 설정

**.env:**
```bash
# NAS 설정
NAS_MOUNT_POINT=/mnt/nas
NAS_INBOX=inbox
NAS_PROCESSING=processing
NAS_COMPLETED=completed
NAS_FAILED=failed

# PostgreSQL (기존)
DB_HOST=localhost
DB_NAME=my_blog
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. 서버 실행

```bash
# NAS 기반 서버
python server/nas_processor.py

# 출력:
# [INFO] NAS Processor 시작
# [INFO] NAS 마운트 포인트: /mnt/nas
# [INFO] Inbox 감시: /mnt/nas/inbox
# [INFO] Processing: /mnt/nas/processing
# [INFO] Completed: /mnt/nas/completed
# [INFO] Failed: /mnt/nas/failed
# [INFO] 파일 감시 시작...
#
# [INFO] 새 파일 발견: inbox/Claude-Test.md
# [INFO] processing/로 이동
# [INFO] 파싱 시작...
# [INFO] Provider: claude
# [INFO] DB 저장 완료!
# [INFO] completed/2025-12-30/로 이동
# [INFO] ✅ 처리 완료!
```

---

## 🔄 전체 플로우

### 1단계: 클라이언트 (노트북)
```
1. Claude에서 대화
   ↓
2. Extension으로 다운로드
   ~/Downloads/Claude-Test.md
   ↓
3. watchdog 감지
   [INFO] AI 채팅 파일 감지
   ↓
4. NAS inbox로 복사
   /mnt/nas/inbox/Claude-Test.md
   ↓
5. 로컬 파일 삭제 (선택)
```

### 2단계: NAS (자동 동기화)
```
클라이언트가 inbox/에 파일 쓰기
   ↓
NAS가 자동 동기화
   ↓
서버에서 inbox/ 파일 보임
```

### 3단계: 서버 (라즈베리파이)
```
1. inbox/ 감시 (watchdog)
   ↓
2. 새 파일 발견
   inbox/Claude-Test.md
   ↓
3. processing/로 이동
   processing/Claude-Test.md
   ↓
4. 파싱 & DB 저장
   [파싱] → [JSON 저장] → [PostgreSQL]
   ↓
5. completed/로 이동
   completed/2025-12-30/Claude-Test.md
   ↓
6. 처리 이력 기록
   metadata/processed.json 업데이트
```

---

## 🛠️ 구현 코드

### client/nas_agent.py (노트북)
```python
#!/usr/bin/env python3
"""
NAS 기반 AI Chat 클라이언트

Downloads 폴더를 감시하고 NAS inbox/로 복사
"""

import os
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import logging

class NASUploadHandler(FileSystemEventHandler):
    """NAS inbox로 파일 업로드"""

    def __init__(self, nas_inbox: Path, patterns: list):
        self.nas_inbox = nas_inbox
        self.patterns = patterns
        self.nas_inbox.mkdir(parents=True, exist_ok=True)

    def is_ai_chat_file(self, filename: str) -> bool:
        """AI Chat 파일인지 확인"""
        import fnmatch
        return any(fnmatch.fnmatch(filename, pattern) for pattern in self.patterns)

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if self.is_ai_chat_file(file_path.name):
            time.sleep(0.5)  # 파일 쓰기 완료 대기

            # NAS inbox로 복사
            dest = self.nas_inbox / file_path.name
            shutil.copy2(file_path, dest)

            logging.info(f"✅ NAS 업로드: {file_path.name}")

            # 로컬 파일 삭제 (선택)
            # file_path.unlink()


if __name__ == '__main__':
    import json

    # 설정 로드
    with open('client/config.json') as f:
        config = json.load(f)

    nas_mount = Path(config['nas_mount_point'])
    nas_inbox = nas_mount / config['nas_inbox']
    download_dir = Path(config['download_dir']).expanduser()

    # 파일 감시
    handler = NASUploadHandler(nas_inbox, config['ai_chat_patterns'])
    observer = Observer()
    observer.schedule(handler, str(download_dir), recursive=False)
    observer.start()

    logging.info(f"[NAS Agent] 시작")
    logging.info(f"  Downloads: {download_dir}")
    logging.info(f"  NAS Inbox: {nas_inbox}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
```

### server/nas_processor.py (라즈베리파이)
```python
#!/usr/bin/env python3
"""
NAS 기반 AI Chat 서버

NAS inbox/를 감시하고 파싱 → DB 저장
"""

import os
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import time
import logging

# 프로젝트 import
from parse.ai_chat_parse import AIMarkdownParser
from storage.ai_chat_saver import AIChatSaver


class NASProcessorHandler(FileSystemEventHandler):
    """NAS inbox 파일 처리"""

    def __init__(self, nas_root: Path):
        self.inbox = nas_root / 'inbox'
        self.processing = nas_root / 'processing'
        self.completed = nas_root / 'completed'
        self.failed = nas_root / 'failed'

        # 디렉토리 생성
        for dir in [self.processing, self.completed, self.failed]:
            dir.mkdir(parents=True, exist_ok=True)

        self.parser = AIMarkdownParser()
        self.saver = AIChatSaver()

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # .md 파일만 처리
        if file_path.suffix != '.md':
            return

        time.sleep(1)  # 파일 쓰기 완료 대기

        # 처리
        self.process_file(file_path)

    def process_file(self, file_path: Path):
        """파일 처리"""
        processing_file = None

        try:
            # inbox → processing
            processing_file = self.processing / file_path.name
            shutil.move(file_path, processing_file)
            logging.info(f"[Processing] {file_path.name}")

            # 파싱
            data = self.parser.parse_file(processing_file)
            logging.info(f"  Provider: {data.provider}")

            # DB 저장
            artifact_id = self.saver.save_ai_chat_artifact(
                data.to_dict(),
                datetime.now().date()
            )
            logging.info(f"  DB 저장: artifact_id={artifact_id}")

            # processing → completed
            today = datetime.now().strftime('%Y-%m-%d')
            completed_dir = self.completed / today
            completed_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(processing_file, completed_dir / file_path.name)

            logging.info(f"✅ 완료: {file_path.name}")

        except Exception as e:
            logging.error(f"❌ 실패: {file_path.name} - {e}")

            # processing → failed
            if processing_file and processing_file.exists():
                shutil.move(processing_file, self.failed / file_path.name)


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    load_dotenv()

    nas_mount = Path(os.getenv('NAS_MOUNT_POINT', '/mnt/nas'))

    # 파일 감시
    handler = NASProcessorHandler(nas_mount)
    observer = Observer()
    observer.schedule(handler, str(handler.inbox), recursive=False)
    observer.start()

    logging.info(f"[NAS Processor] 시작")
    logging.info(f"  Inbox: {handler.inbox}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
```

---

## 🔧 트러블슈팅

### NAS 마운트 실패
```bash
# 연결 확인
ping nas-ip

# SMB 접근 확인
smbclient -L //nas-ip -U your-user

# 재마운트
sudo umount /mnt/nas
sudo mount -t cifs //nas-ip/learningetl /mnt/nas -o ...
```

### 파일이 안 보임
```bash
# 동기화 확인
ls -la /mnt/nas/inbox/

# 권한 확인
ls -ld /mnt/nas/inbox/

# 클라이언트에서 파일 생성 테스트
touch /mnt/nas/inbox/test.txt
```

### 처리가 안 됨
```bash
# 서버 로그
tail -f logs/nas_processor.log

# inbox 확인
ls /mnt/nas/inbox/

# 수동 처리 테스트
python server/nas_processor.py
```

---

## 🎉 장점 요약

| 항목 | HTTP 방식 | NAS 방식 |
|------|-----------|----------|
| 복잡도 | FastAPI 서버 필요 | 파일 복사만 |
| 네트워크 | 포트 개방, HTTPS | VPN으로 보안 |
| 에러 처리 | 재시도 로직 복잡 | 파일 재처리 쉬움 |
| 의존성 | fastapi, uvicorn | watchdog만 |
| 이력 관리 | 별도 구현 | NAS 자동 관리 |
| 서버 다운 | 업로드 실패 | 파일 보존됨 |

**NAS 방식이 훨씬 간단하고 안정적!** ✅
