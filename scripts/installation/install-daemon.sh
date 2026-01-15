#!/bin/bash
# LearningCollector 데몬 설치 스크립트

set -e

echo "=========================================="
echo "LearningCollector 데몬 설치"
echo "=========================================="
echo ""

# 프로젝트 루트 경로 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CURRENT_USER="$(whoami)"

# 1. watchdog 설치
echo "[1/5] watchdog 라이브러리 설치 중..."
pip install watchdog

# 2. 실행 권한 부여
echo "[2/5] 실행 권한 설정..."
chmod +x scripts/runtime/learningcollector-daemon.py

# 3. systemd 서비스 복사 (경로 치환)
echo "[3/5] systemd 서비스 등록..."
sed -e "s|{{PROJECT_ROOT}}|$PROJECT_ROOT|g" \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    scripts/systemd/learningcollector.service | sudo tee /etc/systemd/system/learningcollector.service > /dev/null

# 4. systemd 리로드
echo "[4/5] systemd 리로드..."
sudo systemctl daemon-reload

# 5. 서비스 활성화 (부팅 시 자동 시작)
echo "[5/5] 서비스 활성화..."
sudo systemctl enable learningcollector.service

echo ""
echo "=========================================="
echo "설치 완료"
echo "=========================================="
echo ""
echo "사용 방법:"
echo ""
echo "  시작:   sudo systemctl start learningcollector"
echo "  중지:   sudo systemctl stop learningcollector"
echo "  상태:   sudo systemctl status learningcollector"
echo "  로그:   journalctl -u learningcollector -f"
echo ""
echo "  또는:"
echo "  로그:   tail -f ~/LearningCollector/logs/daemon.log"
echo ""
