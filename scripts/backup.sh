#!/bin/bash
# LearningETL 백업 스크립트

set -e

echo "=========================================="
echo "💾 LearningETL 백업"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 백업 디렉토리
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="learningetl_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

mkdir -p "$BACKUP_PATH"

echo "백업 위치: $BACKUP_PATH"
echo ""

# .env 로드
if [ -f ".env" ]; then
    source .env
else
    echo "❌ .env 파일이 없습니다."
    exit 1
fi

# 1. PostgreSQL 백업
echo "1️⃣ PostgreSQL 백업 중..."
DB_BACKUP_FILE="$BACKUP_PATH/database.sql"

if PGPASSWORD=$DB_PASSWORD pg_dump \
    -h ${DB_HOST:-localhost} \
    -p ${DB_PORT:-5432} \
    -U ${DB_USER:-learning_user} \
    -d ${DB_NAME:-learning} \
    -F c \
    -f "$DB_BACKUP_FILE" 2>/dev/null; then

    DB_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
    echo "  ✅ 데이터베이스 백업 완료 ($DB_SIZE)"
else
    echo "  ❌ 데이터베이스 백업 실패"
    exit 1
fi
echo ""

# 2. JSON 파일 백업
echo "2️⃣ JSON 파일 백업 중..."
if [ -d "learning_artifacts" ]; then
    tar -czf "$BACKUP_PATH/artifacts.tar.gz" learning_artifacts 2>/dev/null
    ARTIFACTS_SIZE=$(du -h "$BACKUP_PATH/artifacts.tar.gz" | cut -f1)
    echo "  ✅ JSON 파일 백업 완료 ($ARTIFACTS_SIZE)"
else
    echo "  ⏭️  learning_artifacts 폴더 없음"
fi
echo ""

# 3. 로그 백업
echo "3️⃣ 로그 파일 백업 중..."
if [ -d "logs" ]; then
    tar -czf "$BACKUP_PATH/logs.tar.gz" logs 2>/dev/null
    LOGS_SIZE=$(du -h "$BACKUP_PATH/logs.tar.gz" | cut -f1)
    echo "  ✅ 로그 파일 백업 완료 ($LOGS_SIZE)"
else
    echo "  ⏭️  logs 폴더 없음"
fi
echo ""

# 4. 설정 파일 백업
echo "4️⃣ 설정 파일 백업 중..."
cp .env "$BACKUP_PATH/.env" 2>/dev/null || true
echo "  ✅ .env 파일 백업 완료"
echo ""

# 5. 백업 정보 저장
cat > "$BACKUP_PATH/backup_info.txt" << EOF
LearningETL 백업 정보
========================================
백업 날짜: $(date)
백업 이름: $BACKUP_NAME

포함 항목:
- database.sql: PostgreSQL 데이터베이스
- artifacts.tar.gz: JSON 파일
- logs.tar.gz: 로그 파일
- .env: 환경 설정

복원 방법:
1. 데이터베이스 복원:
   pg_restore -h localhost -U learning_user -d learning -c database.sql

2. JSON 파일 복원:
   tar -xzf artifacts.tar.gz

3. 로그 파일 복원:
   tar -xzf logs.tar.gz

4. .env 파일 복원:
   cp .env /path/to/LearningETL/
========================================
EOF

echo "  ✅ 백업 정보 저장 완료"
echo ""

# 6. 백업 압축
echo "5️⃣ 백업 압축 중..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
rm -rf "$BACKUP_NAME"

echo "  ✅ 백업 압축 완료 ($BACKUP_SIZE)"
echo ""

# 7. 오래된 백업 정리 (선택)
echo "6️⃣ 오래된 백업 정리..."
read -p "30일 이상 된 백업을 삭제하시겠습니까? (y/N): " CLEANUP
if [[ $CLEANUP =~ ^[Yy]$ ]]; then
    find "$BACKUP_DIR" -name "learningetl_backup_*.tar.gz" -mtime +30 -delete
    echo "  ✅ 오래된 백업 삭제 완료"
else
    echo "  ⏭️  백업 정리 건너뜀"
fi
echo ""

# 8. 원격 백업 (선택)
if [ -n "$BACKUP_REMOTE_PATH" ]; then
    echo "7️⃣ 원격 백업 중..."
    if rsync -avz "${BACKUP_NAME}.tar.gz" "$BACKUP_REMOTE_PATH/" 2>/dev/null; then
        echo "  ✅ 원격 백업 완료: $BACKUP_REMOTE_PATH"
    else
        echo "  ❌ 원격 백업 실패"
    fi
    echo ""
fi

# 완료
echo "=========================================="
echo "✅ 백업 완료!"
echo "=========================================="
echo ""
echo "백업 파일: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo "크기: $BACKUP_SIZE"
echo ""
echo "복원 방법:"
echo "  1. 압축 해제: tar -xzf ${BACKUP_NAME}.tar.gz"
echo "  2. 백업 폴더로 이동: cd ${BACKUP_NAME}"
echo "  3. backup_info.txt 참고"
echo ""
