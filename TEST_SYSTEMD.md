# systemd 즉시 테스트 가이드

## 업데이트 후 즉시 테스트

### 1. 수동으로 서비스 실행 (자정 기다리지 않고)

```bash
# 터미널 1: 로그 실시간 확인
sudo journalctl -u learningcollector-daily.service -f

# 터미널 2: 서비스 수동 실행
sudo systemctl start learningcollector-daily.service
```

**예상 출력 (터미널 1):**
```
Jan 14 14:30:00 raspberrypi systemd[1]: Starting learningcollector-daily.service...
Jan 14 14:30:00 raspberrypi daily-collect.sh[12345]: [2026-01-14 14:30:00] ==========================================
Jan 14 14:30:00 raspberrypi daily-collect.sh[12345]: [2026-01-14 14:30:00] LearningCollector - 일일 수집 시작
Jan 14 14:30:00 raspberrypi daily-collect.sh[12345]: [2026-01-14 14:30:00] ==========================================
Jan 14 14:30:00 raspberrypi daily-collect.sh[12345]: [2026-01-14 14:30:00] 작업 디렉토리: /home/jcw/LearningCollector
Jan 14 14:30:01 raspberrypi systemd[1]: learningcollector-daily.service: Succeeded.
Jan 14 14:30:01 raspberrypi daily-collect.sh[12345]: [2026-01-14 14:30:01] [SUCCESS] 수집 성공
Jan 14 14:30:01 raspberrypi daily-collect.sh[12345]: [2026-01-14 14:30:01] ==========================================
Jan 14 14:30:01 raspberrypi daily-collect.sh[12345]: [2026-01-14 14:30:01] LearningCollector - 일일 수집 완료
Jan 14 14:30:01 raspberrypi daily-collect.sh[12345]: [2026-01-14 14:30:01] ==========================================
```

---

### 2. 서비스 상태 확인

```bash
# 마지막 실행 상태 확인
sudo systemctl status learningcollector-daily.service
```

**성공 시:**
```
● learningcollector-daily.service - LearningCollector - Daily Collection Service
   Loaded: loaded (/etc/systemd/system/learningcollector-daily.service; static)
   Active: inactive (dead) since Tue 2026-01-14 14:30:01 KST; 1min ago
  Process: 12345 ExecStart=/home/jcw/LearningCollector/scripts/runtime/daily-collect.sh (code=exited, status=0/SUCCESS)
```

**실패 시:**
```
   Active: failed (Result: exit-code) since ...
  Process: ... (code=exited, status=1/FAILURE)
```

---

### 3. 수집 결과 파일 확인

```bash
# 오늘 날짜 결과 파일 확인
ls -lh ~/LearningCollector/logs/collect_result_$(date +%Y-%m-%d).json

# 내용 확인
cat ~/LearningCollector/logs/collect_result_$(date +%Y-%m-%d).json | jq '.'
# jq 없으면: cat ~/LearningCollector/logs/collect_result_$(date +%Y-%m-%d).json
```

**예상 출력:**
```json
{
  "date": "2026-01-14",
  "timestamp": "2026-01-14T14:30:01.123456",
  "github": {
    "success": true,
    "commits_count": 5,
    "artifact_ids": [101, 102, 103, 104, 105]
  },
  "baekjoon": {
    "success": true,
    "solutions_count": 2,
    "artifact_ids": [201, 202]
  },
  "summary": {
    "total_artifacts": 7,
    "github_commits": 5,
    "baekjoon_solutions": 2,
    "success": true
  }
}
```

---

### 4. 타이머 상태 확인

```bash
# 타이머가 다음 자정에 예약되었는지 확인
systemctl list-timers learningcollector-daily.timer
```

**예상 출력:**
```
NEXT                        LEFT          LAST                        PASSED  UNIT                            ACTIVATES
Wed 2026-01-15 00:00:00 KST 9h 29min left Tue 2026-01-14 14:30:00 KST 1min ago learningcollector-daily.timer   learningcollector-daily.service
```

---

### 5. cron 로그 확인

```bash
# 오늘 cron 로그 확인
cat ~/LearningCollector/logs/cron_$(date +%Y-%m-%d).log
```

**예상 출력:**
```
[2026-01-14 14:30:00] ==========================================
[2026-01-14 14:30:00] LearningCollector - 일일 수집 시작
[2026-01-14 14:30:00] ==========================================
[2026-01-14 14:30:00] 작업 디렉토리: /home/jcw/LearningCollector
[2026-01-14 14:30:00] ============================================================
[2026-01-14 14:30:00] 개인 학습 정보 수집 자동화 도구 - 2026-01-14
[2026-01-14 14:30:00] ============================================================
[2026-01-14 14:30:00]
[GitHub] 데이터 수집 시작...
[2026-01-14 14:30:01] [SUCCESS] 수집 성공
[2026-01-14 14:30:01] ==========================================
[2026-01-14 14:30:01] LearningCollector - 일일 수집 완료
[2026-01-14 14:30:01] ==========================================
```

---

## 문제 해결

### ❌ 서비스 실행 실패

```bash
# 상세 에러 로그 확인
sudo journalctl -u learningcollector-daily.service -n 100 --no-pager

# daily-collect.sh 직접 실행하여 에러 확인
cd ~/LearningCollector
bash scripts/runtime/daily-collect.sh
```

### ❌ 가상환경 에러

```bash
# venv 경로 확인
ls -la ~/LearningCollector/venv/bin/activate

# venv 없으면 생성
cd ~/LearningCollector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ 권한 에러

```bash
# 스크립트 실행 권한 확인
chmod +x ~/LearningCollector/scripts/runtime/daily-collect.sh

# 로그 디렉토리 권한 확인
ls -ld ~/LearningCollector/logs/
```

### ❌ 타이머가 활성화되지 않음

```bash
# 타이머 활성화 상태 확인
systemctl is-enabled learningcollector-daily.timer

# 비활성화되어 있으면 활성화
sudo systemctl enable learningcollector-daily.timer
sudo systemctl start learningcollector-daily.timer
```

---

## 완전한 테스트 스크립트

모든 것을 한번에 테스트:

```bash
#!/bin/bash
echo "===== LearningCollector 테스트 시작 ====="
echo ""

echo "[1/6] 서비스 수동 실행..."
sudo systemctl start learningcollector-daily.service
sleep 3

echo "[2/6] 서비스 상태 확인..."
sudo systemctl status learningcollector-daily.service --no-pager

echo ""
echo "[3/6] 타이머 상태 확인..."
systemctl list-timers learningcollector-daily.timer --no-pager

echo ""
echo "[4/6] 결과 파일 확인..."
RESULT_FILE=~/LearningCollector/logs/collect_result_$(date +%Y-%m-%d).json
if [ -f "$RESULT_FILE" ]; then
    echo "✓ 결과 파일 존재: $RESULT_FILE"
    echo "파일 크기: $(du -h "$RESULT_FILE" | cut -f1)"
else
    echo "✗ 결과 파일 없음: $RESULT_FILE"
fi

echo ""
echo "[5/6] cron 로그 확인..."
CRON_LOG=~/LearningCollector/logs/cron_$(date +%Y-%m-%d).log
if [ -f "$CRON_LOG" ]; then
    echo "✓ cron 로그 존재"
    tail -5 "$CRON_LOG"
else
    echo "✗ cron 로그 없음"
fi

echo ""
echo "[6/6] 최근 서비스 로그..."
sudo journalctl -u learningcollector-daily.service --since "5 minutes ago" --no-pager | tail -20

echo ""
echo "===== 테스트 완료 ====="
```

**사용법:**
```bash
# 스크립트 저장
cat > ~/test-collector.sh << 'EOF'
#!/bin/bash
# (위 스크립트 내용 복사)
EOF

# 실행 권한 부여
chmod +x ~/test-collector.sh

# 실행
~/test-collector.sh
```

---

## 자정 자동 실행 확인 (다음날)

```bash
# 다음날 아침 확인
sudo journalctl -u learningcollector-daily.service --since "00:00:00"

# 타이머가 실행되었는지 확인
systemctl list-timers learningcollector-daily.timer
```

LAST 컬럼에 오늘 00:00:00이 표시되면 정상 실행된 것입니다.
