#!/bin/bash
#
# Learning ETL 테스트 실행 스크립트
#
# 사용법:
#   ./run_tests.sh              # 전체 테스트 실행
#   ./run_tests.sh config       # 특정 모듈만 테스트
#   ./run_tests.sh -v 1         # verbosity 레벨 지정
#

set -e  # 에러 시 중단

cd "$(dirname "$0")"

echo "======================================================================"
echo "Learning ETL 테스트 실행"
echo "======================================================================"
echo ""

# 환경 확인
echo "[1/3] Python 버전 확인..."
python --version
echo ""

# 필요한 패키지 확인
echo "[2/3] 필수 패키지 확인..."
python -c "import requests; print('✓ requests')" 2>/dev/null || echo "✗ requests (pip install requests)"
python -c "import psycopg2; print('✓ psycopg2')" 2>/dev/null || echo "✗ psycopg2 (pip install psycopg2-binary)"
python -c "import selenium; print('✓ selenium')" 2>/dev/null || echo "✗ selenium (pip install selenium)"
echo ""

# 테스트 실행
echo "[3/3] 테스트 실행..."
echo ""

if [ $# -eq 0 ]; then
    # 전체 테스트
    python run_all_tests.py
else
    # 인자와 함께 실행
    python run_all_tests.py --module "$1"
fi

echo ""
echo "======================================================================"
echo "테스트 완료"
echo "======================================================================"
