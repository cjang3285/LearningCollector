#!/bin/bash
# ========================================
# LearningETL 깔끔한 마이그레이션
# 기존 claude 데이터 삭제 & 새로운 구조로 시작
# ========================================
#
# ⚠️  경고: 이 스크립트는 기존 claude 데이터를 모두 삭제합니다!
#
# 실행 방법 (라즈베리파이에서):
# bash scripts/clean-migrate-db.sh
# ========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "⚠️  LearningETL 깔끔한 마이그레이션"
echo "=========================================="
echo ""
echo "⚠️  경고: 이 스크립트는 다음을 삭제합니다:"
echo ""
echo "  1. learning.claude_conversations 테이블 (전체)"
echo "  2. learning_artifacts의 claude 데이터 (1,114개)"
echo ""
echo "삭제 후에는 복구할 수 없습니다!"
echo ""
read -p "계속하시겠습니까? (yes/no): " CONFIRM

if [[ $CONFIRM != "yes" ]]; then
    echo "취소되었습니다."
    exit 0
fi

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

# 마지막 확인
echo "=========================================="
echo "⚠️  마지막 확인"
echo "=========================================="
echo ""
echo "정말로 claude 데이터 (1,114개)를 삭제하시겠습니까?"
echo ""
read -p "정말 삭제하시겠습니까? (DELETE 입력): " FINAL_CONFIRM

if [[ $FINAL_CONFIRM != "DELETE" ]]; then
    echo "취소되었습니다."
    exit 0
fi

echo ""
echo "마이그레이션을 시작합니다..."
echo ""

# 마이그레이션 실행
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$SCRIPT_DIR/clean-migrate-db.sql"

echo ""
echo "=========================================="
echo "✅ 마이그레이션 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo ""
echo "1. .env 파일 설정:"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. 데이터 수집 시작:"
echo "   python main.py"
echo ""
echo "3. CLI로 확인:"
echo "   python cli.py stats"
echo ""
echo "4. AI Chat 파일 수집:"
echo "   - Claude Exporter로 대화 다운로드"
echo "   - ChatGPT Exporter로 대화 다운로드"
echo "   - Downloads 폴더에 .md 파일 저장"
echo "   - 자동으로 감지 & 파싱 & DB 저장!"
echo ""
