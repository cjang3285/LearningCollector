#!/bin/bash
# LearningETL cron 설정 자동 설치 스크립트

set -e

echo "=========================================="
echo "LearningETL cron 설정 자동 설치"
echo "=========================================="
echo ""

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 실행 권한 추가
chmod +x "$PROJECT_ROOT/scripts/daily-collect.sh"
echo "✅ daily-collect.sh 실행 권한 추가"

# cron 시간 설정
echo ""
echo "매일 몇 시에 수집을 실행할까요?"
read -p "시간 입력 (0-23, 기본값 6): " HOUR
HOUR=${HOUR:-6}

# 분 설정
read -p "분 입력 (0-59, 기본값 0): " MINUTE
MINUTE=${MINUTE:-0}

# cron 표현식 생성
CRON_EXPRESSION="$MINUTE $HOUR * * *"
CRON_COMMAND="$PROJECT_ROOT/scripts/daily-collect.sh"

# 기존 cron 확인
EXISTING_CRON=$(crontab -l 2>/dev/null | grep "daily-collect.sh" || true)

if [ -n "$EXISTING_CRON" ]; then
    echo ""
    echo "⚠️  기존 LearningETL cron 작업이 있습니다:"
    echo "$EXISTING_CRON"
    echo ""
    read -p "덮어쓰시겠습니까? (y/N): " OVERWRITE
    if [[ ! $OVERWRITE =~ ^[Yy]$ ]]; then
        echo "취소되었습니다."
        exit 0
    fi

    # 기존 항목 제거
    (crontab -l 2>/dev/null | grep -v "daily-collect.sh") | crontab -
    echo "✅ 기존 cron 작업 제거"
fi

# 새 cron 작업 추가
(crontab -l 2>/dev/null; echo "$CRON_EXPRESSION $CRON_COMMAND") | crontab -

echo ""
echo "=========================================="
echo "✅ cron 설정 완료!"
echo "=========================================="
echo ""
echo "실행 시간: 매일 $HOUR:$MINUTE"
echo "실행 명령: $CRON_COMMAND"
echo ""
echo "cron 작업 확인:"
crontab -l | grep "daily-collect.sh"
echo ""
echo "로그 위치: $PROJECT_ROOT/logs/cron_*.log"
echo ""
echo "=========================================="
echo ""
echo "💡 추가 명령:"
echo "  - cron 목록 보기: crontab -l"
echo "  - cron 편집: crontab -e"
echo "  - cron 삭제: crontab -r"
echo "  - 로그 확인: tail -f $PROJECT_ROOT/logs/cron_\$(date +%Y-%m-%d).log"
echo ""
