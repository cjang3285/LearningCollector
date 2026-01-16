#!/bin/bash
# LearningCollector 간소화 버전 설치 스크립트

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
echo "[1/4] Python 버전 확인..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python $PYTHON_VERSION"
echo ""

# 가상환경 생성
if [ ! -d "venv" ]; then
    echo "[2/4] 가상환경 생성 중..."
    python3 -m venv venv
    echo "가상환경 생성 완료"
else
    echo "[2/4] 가상환경이 이미 존재합니다."
fi
echo ""

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
echo "[3/4] 의존성 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt
echo "의존성 설치 완료"
echo ""

# .env 파일 생성
if [ ! -f ".env" ]; then
    echo "[4/4] 환경 변수 설정..."
    cp .env.example .env
    echo ".env 파일 생성 완료"
    echo ""
    echo "[WARNING] .env 파일을 편집해주세요:"
    echo "  필수: GITHUB_TOKEN, GITHUB_COMMIT_AUTHORS, ANTHROPIC_API_KEY"
    echo "  nano .env"
    echo ""
    read -p "지금 편집하시겠습니까? (y/N): " EDIT_ENV
    if [[ $EDIT_ENV =~ ^[Yy]$ ]]; then
        nano .env
    fi
else
    echo "[4/4] .env 파일이 이미 존재합니다."
fi
echo ""

# systemd timer 설정 (선택)
echo "=========================================="
echo "자동 수집 설정 (선택)"
echo "=========================================="
read -p "매일 자정에 자동으로 데이터를 수집하시겠습니까? (systemd timer) (Y/n): " SETUP_TIMER
SETUP_TIMER=${SETUP_TIMER:-Y}

if [[ $SETUP_TIMER =~ ^[Yy]$ ]]; then
    bash scripts/installation/setup-daily-timer.sh
else
    echo "[SKIP] 자동 수집 설정 건너뜀"
    echo "수동으로 실행하려면: python main.py"
fi
echo ""

# 완료
echo "=========================================="
echo "설치 완료"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "  1. 환경변수 설정: nano .env"
echo "  2. 테스트 실행: python main.py"
echo "  3. 블로그 초안 생성: python generate_post_draft.py"
echo ""
if [[ $SETUP_TIMER =~ ^[Yy]$ ]]; then
    echo "systemd timer가 매일 자정에 자동 실행합니다:"
    echo "  - 로그 확인: journalctl -u learningcollector-daily.service -f"
    echo "  - 타이머 상태: systemctl status learningcollector-daily.timer"
    echo ""
fi
echo "수집된 데이터:"
echo "  - data/{날짜}.json - 원본 데이터"
echo "  - data/post_draft_{날짜}.md - 블로그 초안"
echo ""
