#!/bin/bash
# LearningETL 설치 테스트 스크립트

set -e

echo "=========================================="
echo "🧪 LearningETL 설치 테스트"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

PASS=0
FAIL=0

# 테스트 함수
test_check() {
    if [ $? -eq 0 ]; then
        echo "  ✅ $1"
        ((PASS++))
    else
        echo "  ❌ $1"
        ((FAIL++))
    fi
}

# 1. Python 버전
echo "1️⃣ Python 환경"
python3 --version > /dev/null 2>&1
test_check "Python 설치 확인"

if [ -d "venv" ]; then
    test_check "가상환경 존재"
else
    echo "  ❌ 가상환경 없음"
    ((FAIL++))
fi
echo ""

# 2. .env 파일
echo "2️⃣ 환경 설정"
if [ -f ".env" ]; then
    test_check ".env 파일 존재"

    source .env

    # GitHub 설정
    if [ -n "$GITHUB_TOKEN" ] && [ "$GITHUB_TOKEN" != "ghp_your_token_here" ]; then
        test_check "GITHUB_TOKEN 설정됨"
    else
        echo "  ❌ GITHUB_TOKEN 미설정"
        ((FAIL++))
    fi

    if [ -n "$GITHUB_USERNAME" ] && [ "$GITHUB_USERNAME" != "your_username" ]; then
        test_check "GITHUB_USERNAME 설정됨"
    else
        echo "  ❌ GITHUB_USERNAME 미설정"
        ((FAIL++))
    fi

    # PostgreSQL 설정
    if [ -n "$DB_NAME" ]; then
        test_check "DB_NAME 설정됨"
    else
        echo "  ❌ DB_NAME 미설정"
        ((FAIL++))
    fi
else
    echo "  ❌ .env 파일 없음"
    ((FAIL++))
fi
echo ""

# 3. PostgreSQL
echo "3️⃣ 데이터베이스"
if command -v psql &> /dev/null; then
    test_check "PostgreSQL 설치됨"

    if sudo systemctl is-active --quiet postgresql; then
        test_check "PostgreSQL 실행 중"

        # DB 연결 테스트
        source .env
        if PGPASSWORD=$DB_PASSWORD psql -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} -U ${DB_USER:-learning_user} -d ${DB_NAME:-learning} -c "SELECT 1" > /dev/null 2>&1; then
            test_check "데이터베이스 연결 성공"

            # 테이블 확인
            TABLES=$(PGPASSWORD=$DB_PASSWORD psql -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} -U ${DB_USER:-learning_user} -d ${DB_NAME:-learning} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'learning'" 2>/dev/null)
            if [ "$TABLES" -ge 4 ]; then
                test_check "테이블 생성됨 ($TABLES개)"
            else
                echo "  ❌ 테이블 부족 ($TABLES개)"
                ((FAIL++))
            fi
        else
            echo "  ❌ 데이터베이스 연결 실패"
            ((FAIL++))
        fi
    else
        echo "  ❌ PostgreSQL 실행 안 됨"
        ((FAIL++))
    fi
else
    echo "  ❌ PostgreSQL 미설치"
    ((FAIL++))
fi
echo ""

# 4. 의존성
echo "4️⃣ Python 패키지"
source venv/bin/activate 2>/dev/null || true

python -c "import requests" 2>/dev/null
test_check "requests 설치됨"

python -c "import psycopg2" 2>/dev/null
test_check "psycopg2 설치됨"

python -c "import watchdog" 2>/dev/null
test_check "watchdog 설치됨"

python -c "from dotenv import load_dotenv" 2>/dev/null
test_check "python-dotenv 설치됨"

echo ""

# 5. 디렉토리 구조
echo "5️⃣ 디렉토리 구조"
[ -d "logs" ]
test_check "logs/ 폴더"

[ -d "collectors" ]
test_check "collectors/ 폴더"

[ -d "export" ]
test_check "export/ 폴더"

[ -d "parse" ]
test_check "parse/ 폴더"

[ -d "storage" ]
test_check "storage/ 폴더"

echo ""

# 6. GitHub API 테스트
echo "6️⃣ API 연결"
source .env

if [ -n "$GITHUB_TOKEN" ] && [ "$GITHUB_TOKEN" != "ghp_your_token_here" ]; then
    RATE_LIMIT=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/rate_limit 2>/dev/null | grep -o '"remaining":[0-9]*' | grep -o '[0-9]*' | head -1)

    if [ -n "$RATE_LIMIT" ]; then
        echo "  ✅ GitHub API 연결 성공 (남은 호출: $RATE_LIMIT)"
        ((PASS++))
    else
        echo "  ❌ GitHub API 연결 실패"
        ((FAIL++))
    fi
else
    echo "  ⏭️  GitHub API 테스트 건너뜀 (토큰 미설정)"
fi

echo ""

# 7. main.py dry-run (선택)
echo "7️⃣ main.py 테스트"
if python -c "import main" 2>/dev/null; then
    test_check "main.py import 성공"
else
    echo "  ❌ main.py import 실패"
    ((FAIL++))
fi

echo ""

# 결과
echo "=========================================="
echo "📊 테스트 결과"
echo "=========================================="
echo ""
echo "  통과: $PASS"
echo "  실패: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✅ 모든 테스트 통과!"
    echo ""
    echo "이제 LearningETL을 실행할 수 있습니다:"
    echo "  python main.py"
    exit 0
else
    echo "⚠️  일부 테스트 실패"
    echo ""
    echo "다음을 확인해주세요:"
    echo "  1. .env 파일 설정"
    echo "  2. PostgreSQL 설치 및 실행"
    echo "  3. 데이터베이스 생성: bash scripts/setup-database.sh"
    exit 1
fi
