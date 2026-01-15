#!/bin/bash
# LearningCollector Standalone Mode 설치 스크립트

set -e

echo "=========================================="
echo "LearningCollector 설치 시작"
echo "=========================================="
echo ""

# 프로젝트 루트
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

# Python 버전 확인
echo "[1/6] Python 버전 확인..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python $PYTHON_VERSION"
echo ""

# 가상환경 생성
if [ ! -d "venv" ]; then
    echo "[2/6] 가상환경 생성 중..."
    python3 -m venv venv
    echo "가상환경 생성 완료"
else
    echo "[2/6] 가상환경이 이미 존재합니다."
fi
echo ""

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
echo "[3/6] 의존성 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt
echo "의존성 설치 완료"
echo ""

# .env 파일 생성
if [ ! -f ".env" ]; then
    echo "[4/6] 환경 변수 설정..."
    cp .env.example .env
    echo ".env 파일 생성 완료"
    echo ""
    echo "[WARNING] .env 파일을 편집해주세요:"
    echo "  nano .env"
    echo ""
    read -p "지금 편집하시겠습니까? (y/N): " EDIT_ENV
    if [[ $EDIT_ENV =~ ^[Yy]$ ]]; then
        nano .env
    fi
else
    echo "[4/6] .env 파일이 이미 존재합니다."
fi
echo ""

# PostgreSQL 및 DB 설정
echo "[5/6] 데이터베이스 설정..."
read -p "PostgreSQL 데이터베이스를 설정하시겠습니까? (Y/n): " SETUP_DB
SETUP_DB=${SETUP_DB:-Y}

if [[ $SETUP_DB =~ ^[Yy]$ ]]; then
    bash scripts/installation/setup-database.sh
else
    echo "[SKIP] 데이터베이스 설정 건너뜀"
fi
echo ""

# systemd timer 설정
echo "[6/6] 자동 수집 설정..."
read -p "매일 자동으로 데이터를 수집하시겠습니까? (systemd timer) (Y/n): " SETUP_TIMER
SETUP_TIMER=${SETUP_TIMER:-Y}

if [[ $SETUP_TIMER =~ ^[Yy]$ ]]; then
    bash scripts/installation/setup-daily-timer.sh
else
    echo "[SKIP] 자동 수집 설정 건너뜀"
fi
echo ""

# 설치 테스트
echo "[TEST] 설치 테스트 중..."
if bash scripts/maintenance/test-installation.sh; then
    echo "[SUCCESS] 설치 테스트 통과"
else
    echo "[WARNING] 일부 테스트 실패 (수동으로 확인 필요)"
fi
echo ""

# 완료
echo "=========================================="
echo "설치 완료"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "  1. 테스트 실행: python main.py"
echo "  2. systemd timer가 매일 자동으로 수집합니다"
echo "  3. 로그 확인: journalctl -u learningcollector-daily.service -f"
echo ""
echo "문서:"
echo "  - README.md"
echo "  - INSTALL.md"
echo "  - docs/STANDALONE_GUIDE.md"
echo ""
