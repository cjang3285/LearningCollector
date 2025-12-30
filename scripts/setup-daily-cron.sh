#!/bin/bash
# LearningETL 매일 자정 실행 Cron 설정

echo "=========================================="
echo "LearningETL 매일 자정 실행 Cron 설정"
echo "=========================================="
echo ""

# Cron 항목
CRON_CMD="0 0 * * * /home/jcw/LearningETL/venv/bin/python /home/jcw/LearningETL/main.py --ai-chat-scan >> /home/jcw/LearningETL/logs/daily-scan.log 2>&1"

# 기존 crontab에 항목이 있는지 확인
if crontab -l 2>/dev/null | grep -q "LearningETL"; then
    echo "⚠️  이미 LearningETL cron 항목이 존재합니다."
    echo ""
    echo "현재 crontab:"
    crontab -l | grep "LearningETL"
    echo ""
    read -p "덮어쓰시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 취소되었습니다."
        exit 1
    fi
    # 기존 항목 제거
    crontab -l | grep -v "LearningETL" | crontab -
fi

# 새 cron 항목 추가
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron 설정 완료!"
echo ""
echo "설정된 cron:"
crontab -l | grep "LearningETL"
echo ""
echo "매일 자정(00:00)에 AI 채팅 스캔이 실행됩니다."
echo "로그: ~/LearningETL/logs/daily-scan.log"
echo ""
echo "확인: crontab -l"
echo "제거: crontab -e (해당 줄 삭제)"
echo ""
