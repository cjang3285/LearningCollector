#!/bin/bash
# LearningCollector - 일일 수집 스크립트
# 용도: systemd timer에서 매일 실행하여 데이터 수집

set -e  # 에러 발생 시 중단

# 프로젝트 루트 디렉토리 (이 스크립트 위치 기준)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# 가상환경 활성화
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
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
log_message "LearningCollector - 일일 수집 시작"
log_message "=========================================="

# main.py 실행 (데이터 수집)
cd "$PROJECT_ROOT"
log_message "작업 디렉토리: $PROJECT_ROOT"

if "$PROJECT_ROOT/venv/bin/python" main.py >> "$LOG_FILE" 2>&1; then
    log_message "[SUCCESS] 데이터 수집 성공"

    # 블로그 초안 생성
    log_message "블로그 초안 생성 중..."
    if "$PROJECT_ROOT/venv/bin/python" generate_post_draft.py >> "$LOG_FILE" 2>&1; then
        log_message "[SUCCESS] 블로그 초안 생성 성공"
        EXIT_CODE=0
    else
        log_message "[WARNING] 블로그 초안 생성 실패 (exit code: $?)"
        EXIT_CODE=0  # 데이터 수집은 성공했으므로 0 반환
    fi
else
    log_message "[ERROR] 데이터 수집 실패 (exit code: $?)"
    EXIT_CODE=1
fi

log_message "=========================================="
log_message "LearningCollector - 일일 수집 완료"
log_message "=========================================="
log_message ""

exit $EXIT_CODE
