#!/bin/bash
# LearningETL 데이터베이스 초기 설정 스크립트

set -e

echo "=========================================="
echo "LearningETL 데이터베이스 설정"
echo "=========================================="
echo ""

# 프로젝트 루트
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# .env 파일에서 DB 설정 읽기
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "❌ .env 파일이 없습니다."
    echo "먼저 .env 파일을 생성해주세요:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# 기본값 설정
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-learning}
DB_USER=${DB_USER:-learning_user}

echo "DB 설정:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# PostgreSQL 설치 확인
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL이 설치되어 있지 않습니다."
    echo ""
    read -p "PostgreSQL을 설치하시겠습니까? (y/N): " INSTALL_PG
    if [[ $INSTALL_PG =~ ^[Yy]$ ]]; then
        echo "PostgreSQL 설치 중..."
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        echo "✅ PostgreSQL 설치 완료"
    else
        echo "PostgreSQL 설치를 건너뜁니다."
        exit 0
    fi
fi

echo "✅ PostgreSQL 설치 확인"

# PostgreSQL 실행 확인
if ! sudo systemctl is-active --quiet postgresql; then
    echo "PostgreSQL 시작 중..."
    sudo systemctl start postgresql
fi

echo "✅ PostgreSQL 실행 중"
echo ""

# 데이터베이스 및 사용자 생성
echo "데이터베이스 및 사용자를 생성합니다..."
echo ""

sudo -u postgres psql << EOF
-- 데이터베이스 생성
SELECT 'CREATE DATABASE $DB_NAME'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- 사용자 생성
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

\c $DB_NAME

-- learning 스키마 생성
CREATE SCHEMA IF NOT EXISTS learning;
GRANT ALL ON SCHEMA learning TO $DB_USER;

\q
EOF

echo "✅ 데이터베이스 및 사용자 생성 완료"
echo ""

# 테이블 생성
echo "테이블을 생성합니다..."
echo ""

PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < "$SCRIPT_DIR/create-schema.sql"

# 권한 부여
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << EOF
GRANT ALL ON SCHEMA learning TO $DB_USER;
GRANT ALL ON ALL TABLES IN SCHEMA learning TO $DB_USER;
GRANT ALL ON ALL SEQUENCES IN SCHEMA learning TO $DB_USER;
EOF

echo "✅ 테이블 생성 완료"
echo ""

# 연결 테스트
echo "데이터베이스 연결 테스트..."
if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo "✅ 데이터베이스 연결 성공"
else
    echo "❌ 데이터베이스 연결 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 데이터베이스 설정 완료!"
echo "=========================================="
echo ""
echo "테이블 확인:"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt learning.*"
echo ""
echo "이제 LearningETL을 실행할 수 있습니다:"
echo "  python main.py"
echo ""
