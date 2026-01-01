## learningetl.*이 아니라 learningetl-daily.timer/.service 가 항시 돌고 있다
### timer -> service -> daily-collect.sh -> python main.py 실행 순서
그냥 learningetl은 실행 후 종료되므로 -daily를 확인할 것.
그리고 git pull 하여 main.py의 실행 로직이 변경되면 이미 pull만으로 반영된 것이다. 
자정에는 pull된 코드가 실행되기 때문이다.

(venv) jcw@jcw: **/etc/systemd/system** $ cat **learningetl-daily.timer** 
[Unit]
Description=LearningETL Daily Scan Timer
Requires=learningetl-daily.service

[Timer]
# 매일 자정 (00:00) 실행
OnCalendar=daily

# 시스템 재부팅 시 놓친 작업 실행
Persistent=true

[Install]
WantedBy=timers.target
(venv) jcw@jcw:/etc/systemd/system$ cat **learningetl-daily.service** 
[Unit]
Description=LearningETL Daily Scan
After=network.target postgresql.service

[Service]
Type=oneshot
User=jcw
WorkingDirectory=/home/jcw/LearningETL
ExecStart=/home/jcw/LearningETL/scripts/runtime/**daily-collect.sh**

[Install]
WantedBy=multi-user.target
(venv) jcw@jcw:/etc/systemd/system$ cat /home/jcw/LearningETL/scripts/runtime/**daily-collect.sh**
#!/bin/bash
# LearningETL 일일 수집 스크립트
# 용도: systemd timer에서 매일 실행하여 데이터 수집

set -e  # 에러 발생 시 중단

# 프로젝트 루트 디렉토리 (이 스크립트 위치 기준)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# 가상환경 활성화
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/**activate**"
else
    echo "가상환경을 찾을 수 없습니다: $PROJECT_ROOT/venv"
    exit 1
fi

# 로그 파일 설정
LOG_DIR="$PROJECT_ROOT/logs"
DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/cron_$DATE.log"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 타임스탬프 함수
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "=========================================="
log_message "LearningETL 일일 수집 시작"
log_message "=========================================="

# main.py 실행
cd "$PROJECT_ROOT"
log_message "작업 디렉토리: $PROJECT_ROOT"

if **python main.py** >> "$LOG_FILE" 2>&1; then
    log_message "[SUCCESS] 수집 성공"
    EXIT_CODE=0
else
    log_message "[ERROR] 수집 실패 (exit code: $?)"
    EXIT_CODE=1
fi

log_message "=========================================="
log_message "LearningETL 일일 수집 완료"
log_message "=========================================="
log_message ""

exit $EXIT_CODE


(venv) jcw@jcw:/etc/systemd/system$ sudo systemctl list-units --type=service,timer | grep -i learningetl
  learningetl-daily.timer                                  loaded active waiting LearningETL Daily Scan Timer
(venv) jcw@jcw:/etc/systemd/system$ sudo systemctl list-timers | grep learningetl
Fri 2026-01-02 00:00:00 KST       8h Thu 2026-01-01 00:00:00 KST      15h ago learningetl-daily.timer        learningetl-daily.service
(venv) jcw@jcw:/etc/systemd/system$ sudo journalctl -u learningetl-daily.service --since today
Jan 01 00:00:00 jcw systemd[1]: Starting learningetl-daily.service - LearningETL Daily Scan...
Jan 01 00:00:00 jcw daily-collect.sh[64756]: [2026-01-01 00:00:00] ==========================================
Jan 01 00:00:00 jcw daily-collect.sh[64760]: [2026-01-01 00:00:00] LearningETL 일일 수집 시작
Jan 01 00:00:00 jcw daily-collect.sh[64763]: [2026-01-01 00:00:00] ==========================================
Jan 01 00:00:01 jcw daily-collect.sh[64766]: [2026-01-01 00:00:00] 작업 디렉토리: /home/jcw/LearningETL
Jan 01 00:00:09 jcw daily-collect.sh[64789]: [2026-01-01 00:00:09] [SUCCESS] 수집 성공
Jan 01 00:00:09 jcw daily-collect.sh[64792]: [2026-01-01 00:00:09] ==========================================
Jan 01 00:00:09 jcw daily-collect.sh[64795]: [2026-01-01 00:00:09] LearningETL 일일 수집 완료
Jan 01 00:00:09 jcw daily-collect.sh[64798]: [2026-01-01 00:00:09] ==========================================
Jan 01 00:00:09 jcw daily-collect.sh[64801]: [2026-01-01 00:00:09]
Jan 01 00:00:09 jcw systemd[1]: learningetl-daily.service: Deactivated successfully.
Jan 01 00:00:09 jcw systemd[1]: Finished learningetl-daily.service - LearningETL Daily Scan.
Jan 01 00:00:09 jcw systemd[1]: learningetl-daily.service: Consumed 3.937s CPU time.
