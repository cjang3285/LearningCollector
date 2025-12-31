#!/bin/bash
# LearningETL 매일 자정 실행 systemd timer 설정

set -e

echo "=========================================="
echo "LearningETL 매일 자정 실행 Timer 설정"
echo "=========================================="
echo ""

# 프로젝트 루트 경로 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CURRENT_USER="$(whoami)"

# 1. systemd 서비스 및 타이머 복사 (경로 치환)
echo "[1/4] systemd 파일 복사..."
sed -e "s|{{PROJECT_ROOT}}|$PROJECT_ROOT|g" \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    scripts/systemd/learningetl-daily.service | sudo tee /etc/systemd/system/learningetl-daily.service > /dev/null
sudo cp scripts/systemd/learningetl-daily.timer /etc/systemd/system/

# 2. systemd 리로드
echo "[2/4] systemd 리로드..."
sudo systemctl daemon-reload

# 3. 타이머 활성화 (부팅 시 자동 시작)
echo "[3/4] 타이머 활성화..."
sudo systemctl enable learningetl-daily.timer

# 4. 타이머 시작
echo "[4/4] 타이머 시작..."
sudo systemctl start learningetl-daily.timer

echo ""
echo "=========================================="
echo "설정 완료"
echo "=========================================="
echo ""
echo "사용 방법:"
echo ""
echo "  타이머 상태:   sudo systemctl status learningetl-daily.timer"
echo "  타이머 목록:   systemctl list-timers learningetl-daily.timer"
echo "  수동 실행:     sudo systemctl start learningetl-daily.service"
echo "  로그:         tail -f ~/LearningETL/logs/daily-scan.log"
echo ""
echo "  타이머 중지:   sudo systemctl stop learningetl-daily.timer"
echo "  타이머 비활성화: sudo systemctl disable learningetl-daily.timer"
echo ""
