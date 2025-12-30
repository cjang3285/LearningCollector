#!/bin/bash
# ========================================
# LearningETL 기존 DB 마이그레이션 스크립트
# ========================================
#
# 목적:
# 1. public 스키마 → blog 스키마로 이동
# 2. learning 스키마 업데이트
# 3. 데이터베이스명은 my_blog 그대로 사용 (변경 안 함)
#
# 실행 방법 (라즈베리파이에서):
# bash scripts/migrate-existing-db.sh
# ========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "LearningETL DB 마이그레이션"
echo "=========================================="
echo ""

# DB 설정
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-my_blog}
DB_USER=${DB_USER:-postgres}

echo "DB 정보:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# PostgreSQL 비밀번호 입력
read -sp "PostgreSQL 비밀번호 입력: " DB_PASSWORD
echo ""
echo ""

# 연결 테스트
echo "DB 연결 테스트..."
if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo "✅ 연결 성공"
else
    echo "❌ 연결 실패"
    exit 1
fi
echo ""

# 마이그레이션 실행
echo "마이그레이션 실행 중..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$SCRIPT_DIR/migrate-existing-db.sql"

echo ""
echo "=========================================="
echo "✅ 마이그레이션 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. .env 파일 업데이트:"
echo "   DB_NAME=my_blog"
echo ""
echo "2. 데이터 수집 테스트:"
echo "   python main.py"
echo ""
echo "3. CLI로 데이터 확인:"
echo "   python cli.py stats"
echo ""
