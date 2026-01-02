# LearningETL 시스템 동작 구조

## 핵심 개념
`learningetl.service`가 아닌 **`learningetl-daily.timer/.service`**가 실제 운영 중인 유닛이다.

## 실행 흐름
```
learningetl-daily.timer 
  → learningetl-daily.service 
    → daily-collect.sh 
      → python main.py
```

## 코드 업데이트 반영 메커니즘
- `git pull`로 `main.py` 변경사항을 pull하면 **즉시 반영 완료**
- 별도 재시작 불필요 - 자정에 실행되는 타이머가 pull된 코드를 실행
- `learningetl.service`는 oneshot 타입으로 실행 후 종료되므로 상시 active 상태가 아님

---

## systemd 유닛 구성

### 1. Timer Unit
**파일**: `/etc/systemd/system/learningetl-daily.timer`
```ini
[Unit]
Description=LearningETL Daily Scan Timer
Requires=learningetl-daily.service

[Timer]
OnCalendar=daily              # 매일 00:00 실행
Persistent=true               # 재부팅 시 놓친 작업 실행

[Install]
WantedBy=timers.target
```

### 2. Service Unit
**파일**: `/etc/systemd/system/learningetl-daily.service`
```ini
[Unit]
Description=LearningETL Daily Scan
After=network.target postgresql.service

[Service]
Type=oneshot                  # 작업 완료 후 종료
User=jcw
WorkingDirectory=/home/jcw/LearningETL
ExecStart=/home/jcw/LearningETL/scripts/runtime/daily-collect.sh

[Install]
WantedBy=multi-user.target
```

### 3. Shell Script
**파일**: `/home/jcw/LearningETL/scripts/runtime/daily-collect.sh`
```bash
#!/bin/bash
set -e  # 에러 발생 시 중단

# 경로 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# venv 활성화
source "$PROJECT_ROOT/venv/bin/activate"

# 로그 설정
LOG_DIR="$PROJECT_ROOT/logs"
DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/cron_$DATE.log"
mkdir -p "$LOG_DIR"

# 로그 함수
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 실행
log_message "=========================================="
log_message "LearningETL 일일 수집 시작"
log_message "작업 디렉토리: $PROJECT_ROOT"

cd "$PROJECT_ROOT"
if python main.py >> "$LOG_FILE" 2>&1; then
    log_message "[SUCCESS] 수집 성공"
    EXIT_CODE=0
else
    log_message "[ERROR] 수집 실패 (exit code: $?)"
    EXIT_CODE=1
fi

log_message "LearningETL 일일 수집 완료"
log_message "=========================================="
exit $EXIT_CODE
```

---

## 운영 상태 확인

### 타이머 상태
```bash
$ sudo systemctl list-timers | grep learningetl
Fri 2026-01-02 00:00:00 KST  8h    Thu 2026-01-01 00:00:00 KST  15h ago  learningetl-daily.timer
```
- **다음 실행**: 2026-01-02 00:00:00
- **마지막 실행**: 2026-01-01 00:00:00 (15시간 전)

### 서비스 로그
```bash
$ sudo journalctl -u learningetl-daily.service --since today
Jan 01 00:00:00 jcw systemd[1]: Starting learningetl-daily.service...
Jan 01 00:00:00 jcw daily-collect.sh[64756]: [2026-01-01 00:00:00] LearningETL 일일 수집 시작
Jan 01 00:00:01 jcw daily-collect.sh[64766]: [2026-01-01 00:00:00] 작업 디렉토리: /home/jcw/LearningETL
Jan 01 00:00:09 jcw daily-collect.sh[64789]: [2026-01-01 00:00:09] [SUCCESS] 수집 성공
```

---

## 주요 특징
- **Type=oneshot**: 작업 완료 후 서비스 종료, 타이머가 주기적으로 재실행
- **Persistent=true**: 시스템 다운타임 동안 놓친 작업을 부팅 후 실행
- **로그 분리**: 일자별 로그 파일 (`logs/cron_YYYY-MM-DD.log`)
- **가상환경 자동 활성화**: 스크립트 내에서 venv 관리
- **에러 핸들링**: `set -e`로 중간 실패 시 즉시 중단, exit code 로깅
