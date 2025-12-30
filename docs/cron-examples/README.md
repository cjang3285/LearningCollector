# cron 설정 예시

## 📖 개요

LearningETL을 매일 자동으로 실행하기 위한 cron 설정 템플릿입니다.

---

## 🚀 빠른 설정 (자동)

**자동 설치 스크립트 사용:**

```bash
cd /home/jcw/LearningETL
bash scripts/setup-cron.sh
```

대화형으로 실행 시간을 선택하면 자동으로 cron이 설정됩니다.

---

## 🔧 수동 설정

### 1. cron 편집

```bash
crontab -e
```

### 2. 다음 줄 추가

```cron
# LearningETL 일일 수집 (매일 오전 6시)
0 6 * * * /home/jcw/LearningETL/scripts/daily-collect.sh
```

**시간 변경:**
- `0 6` → 오전 6시 0분
- `30 23` → 오후 11시 30분
- `0 */6` → 6시간마다

**cron 표현식 형식:**
```
분(0-59) 시(0-23) 일(1-31) 월(1-12) 요일(0-7)
```

### 3. 저장 후 확인

```bash
# cron 목록 확인
crontab -l

# 로그 확인
tail -f /home/jcw/LearningETL/logs/cron_$(date +%Y-%m-%d).log
```

---

## 📝 템플릿 예시

### 기본 (매일 오전 6시)
```cron
0 6 * * * /home/jcw/LearningETL/scripts/daily-collect.sh
```

### 매일 자정
```cron
0 0 * * * /home/jcw/LearningETL/scripts/daily-collect.sh
```

### 매일 오후 11시
```cron
0 23 * * * /home/jcw/LearningETL/scripts/daily-collect.sh
```

### 6시간마다
```cron
0 */6 * * * /home/jcw/LearningETL/scripts/daily-collect.sh
```

### 평일만 (월~금 오전 9시)
```cron
0 9 * * 1-5 /home/jcw/LearningETL/scripts/daily-collect.sh
```

---

## 🔍 로그 관리

### 로그 위치
```bash
logs/
├── cron_2025-12-29.log    # 일별 cron 로그
├── main.log               # 메인 애플리케이션 로그
├── github_collector.log   # GitHub 수집 로그
├── baekjoon_collector.log # Baekjoon 수집 로그
└── ai_chat_collector.log  # AI Chat 수집 로그
```

### 로그 확인
```bash
# 오늘 cron 로그
tail -f logs/cron_$(date +%Y-%m-%d).log

# 최근 100줄
tail -100 logs/cron_$(date +%Y-%m-%d).log

# 에러만 보기
grep ERROR logs/cron_$(date +%Y-%m-%d).log
```

### 오래된 로그 정리 (선택)
```bash
# cron에 추가 (30일 이상 로그 삭제)
0 3 * * 0 find /home/jcw/LearningETL/logs -name "cron_*.log" -mtime +30 -delete
```

---

## 🐛 트러블슈팅

### cron이 실행 안 됨

**1. cron 서비스 확인:**
```bash
sudo systemctl status cron
```

**2. cron 목록 확인:**
```bash
crontab -l
```

**3. 스크립트 실행 권한 확인:**
```bash
ls -la scripts/daily-collect.sh
# -rwxr-xr-x 여야 함 (실행 권한)

# 권한 없으면 추가
chmod +x scripts/daily-collect.sh
```

**4. 수동 실행 테스트:**
```bash
/home/jcw/LearningETL/scripts/daily-collect.sh
```

### 환경 변수 문제

cron은 기본 환경 변수만 사용하므로 `.env` 파일을 확인하세요:

```bash
# .env 파일 존재 확인
ls -la .env

# .env 파일 내용 확인 (토큰은 가려짐)
cat .env | grep -v "TOKEN"
```

### 가상환경 문제

`daily-collect.sh` 스크립트가 자동으로 가상환경을 활성화합니다:

```bash
# 가상환경 경로 확인
ls -la venv/bin/activate

# 수동 테스트
source venv/bin/activate
python main.py
```

---

## 📧 알림 설정 (선택)

### 이메일 알림

```cron
MAILTO=your-email@example.com
0 6 * * * /home/jcw/LearningETL/scripts/daily-collect.sh
```

### 텔레그램 알림 (고급)

`scripts/daily-collect.sh` 수정:

```bash
# 텔레그램 설정
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"

# 에러 발생 시 알림
if ! python main.py >> "$LOG_FILE" 2>&1; then
    curl -s -X POST \
      "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
      -d chat_id="$TELEGRAM_CHAT_ID" \
      -d text="❌ LearningETL 수집 실패: $(date)"
fi
```

---

## 📋 체크리스트

설정 후 확인사항:

- [ ] `scripts/daily-collect.sh` 실행 권한 확인
- [ ] `.env` 파일 존재 및 설정 확인
- [ ] 가상환경 존재 확인 (`venv/`)
- [ ] cron 작업 추가 확인 (`crontab -l`)
- [ ] 수동 실행 테스트
- [ ] 다음 날 로그 확인

---

## 💡 권장 설정

### Standalone Mode
```cron
# 매일 오전 6시 데이터 수집
0 6 * * * /home/jcw/LearningETL/scripts/daily-collect.sh
```

### Client-Server Mode
**Server (라즈베리파이):**
```cron
# 매일 오전 6시 GitHub/Baekjoon 수집
0 6 * * * /home/jcw/LearningETL/scripts/daily-collect.sh
```

**Client (노트북):**
- cron 불필요 (Client Agent가 24시간 실시간 감시)
- systemd 서비스 사용 권장
