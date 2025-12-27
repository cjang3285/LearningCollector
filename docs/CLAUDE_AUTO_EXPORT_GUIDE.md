# Claude 자동 Export 시스템

Desktop/Laptop에서 자동으로 Claude 대화를 Export하고, Pi가 자동으로 파싱하여 DB에 저장하는 완전 자동화 시스템입니다.

## 🎯 시스템 구성

```
[Desktop/Laptop]
  ↓ Playwright 자동 Export
  ↓
[NAS: Z:\learning-etl\claude-exports\]  또는  [로컬 + SCP]
  ↓
[Raspberry Pi]
  ↓ 디렉토리 모니터링
  ↓ ZIP 파싱
  ↓ 증분 저장 (새 대화만)
  ↓
[PostgreSQL DB]
```

## 📊 두 가지 저장 방식

### 방식 1: NAS 직접 저장 (추천)

**장점:**
- ✅ 전송 단계 없음 (더 단순)
- ✅ 여러 기기 지원 (Desktop + Laptop)
- ✅ Desktop 꺼져도 Pi가 처리
- ✅ 파일 중복 없음

**설정:**
```python
# tools/auto_export_desktop.py
USE_NAS = True
EXPORT_DIR = Path("Z:/learning-etl/claude-exports")
```

**요구사항:**
- Pi NAS가 Z:로 마운트
- 쓰기 권한 있음

---

### 방식 2: 로컬 저장 후 전송

**장점:**
- ✅ NAS 독립적
- ✅ 로컬 백업 유지
- ✅ 빠른 로컬 저장

**설정:**
```python
# tools/auto_export_desktop.py
USE_NAS = False
EXPORT_DIR = Path("~/Downloads/claude-exports")
```

---

## 🚀 설치 및 설정

### Desktop/Laptop (Windows)

**1. 의존성 설치**
```bash
pip install playwright
playwright install chromium
```

**2. 쿠키 추출 (최초 1회)**
```bash
python tools/extract_cookies_playwright.py --upload
```

**3. Export 테스트**
```bash
python tools/auto_export_desktop.py
```

**4. 자동 실행 설정 (선택)**

**방법 A: 작업 스케줄러 (매일 자동)**
```
1. 작업 스케줄러 열기
2. 기본 작업 만들기
3. 트리거: 매일 오후 11시
4. 작업: python Z:\LearningConvertedToLog\tools\auto_export_desktop.py --headless
```

**방법 B: 수동 실행**
- 주 1회 수동으로 실행
- 백그라운드: `--headless` 옵션 추가

---

### Raspberry Pi

**1. 모니터링 스크립트 실행**

**포그라운드 (테스트):**
```bash
cd ~/learning-etl
source venv/bin/activate
python tools/monitor_claude_exports.py
```

**백그라운드 (운영):**
```bash
cd ~/learning-etl
source venv/bin/activate
nohup python tools/monitor_claude_exports.py > logs/export_monitor.log 2>&1 &
```

**2. 서비스로 등록 (자동 시작)**

`/etc/systemd/system/claude-export-monitor.service`:
```ini
[Unit]
Description=Claude Export Monitor
After=network.target

[Service]
Type=simple
User=jcw
WorkingDirectory=/home/jcw/learning-etl
ExecStart=/home/jcw/learning-etl/venv/bin/python tools/monitor_claude_exports.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**활성화:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable claude-export-monitor
sudo systemctl start claude-export-monitor

# 상태 확인
sudo systemctl status claude-export-monitor
```

---

## 🔄 증분 백업 (당일 대화만)

### 전략

**최초 Export (전체):**
```bash
# Desktop에서 실행 → 모든 대화 다운로드
python tools/auto_export_desktop.py
```

**이후 Export (증분):**
```bash
# 같은 명령어 실행
python tools/auto_export_desktop.py

# Pi가 자동으로 필터링:
# - 이미 DB에 있는 대화 UUID는 스킵
# - 새 대화 또는 업데이트된 대화만 저장
```

### 증분 로직

`tools/monitor_claude_exports.py`의 `filter_new_conversations()`:
```python
def filter_new_conversations(conversations):
    """이미 DB에 있는 대화 제외"""
    # DB에서 conversation_uuid 조회
    # 없으면 → 새 대화
    # 있으면 → 스킵
    return new_conversations
```

**장점:**
- ✅ 전체 Export 다운로드해도 DB에는 새 대화만 저장
- ✅ 중복 저장 방지
- ✅ 빠른 처리 (필터링으로 파싱 시간 단축)

---

## 📝 사용 워크플로우

### 매일 또는 주 1회

**Desktop (수동 또는 자동):**
```bash
# 자동: 작업 스케줄러 설정 완료 시
# 수동: 주 1회 실행
python tools/auto_export_desktop.py
```

**Pi (완전 자동):**
```
1. 새 ZIP 파일 감지 (1분마다 체크)
2. 다운로드 완료 확인 (파일 크기 안정화)
3. ZIP 파싱
4. 증분 필터링 (새 대화만)
5. DB 저장
6. 처리 완료 기록
```

**알림 (선택):**
```bash
# Pi에서 완료 후 이메일/슬랙 알림 (선택)
# monitor_claude_exports.py에 추가 가능
```

---

## 🛠️ 문제 해결

### Desktop

**Export 버튼을 찾을 수 없음**
- 스크린샷 확인: `temp/export_debug.png`
- Claude.ai UI 변경 가능 → 셀렉터 수정 필요
- 수동 Export 후 다운로드 폴더 모니터링으로 대체

**Cloudflare 차단**
- Desktop은 차단 안 됨 (실제 브라우저)
- 쿠키가 최신인지 확인

**NAS 접근 불가**
- Z: 드라이브 마운트 확인
- 쓰기 권한 확인
- `USE_NAS = False`로 변경

### Pi

**모니터링이 작동하지 않음**
```bash
# 프로세스 확인
ps aux | grep monitor_claude_exports

# 로그 확인
tail -f logs/export_monitor.log

# 수동 실행으로 디버깅
python tools/monitor_claude_exports.py
```

**파싱 에러**
- ZIP 파일 손상 확인
- parse/claude_parse.py 에러 로그 확인

**DB 연결 실패**
- PostgreSQL 실행 확인: `systemctl status postgresql`
- 연결 정보 확인: `config/settings.py`

---

## 📊 모니터링

### 로그 확인

**Desktop:**
```bash
# 표준 출력으로 확인
python tools/auto_export_desktop.py
```

**Pi:**
```bash
# 로그 파일 확인
tail -f logs/export_monitor.log

# 처리 완료 목록
cat temp/processed_exports.txt
```

### DB 확인

```sql
-- 최근 저장된 Claude 대화
SELECT
    id,
    conversation_uuid,
    conversation_name,
    message_count,
    created_at
FROM learning.claude_conversations
ORDER BY created_at DESC
LIMIT 10;

-- 오늘 저장된 대화 수
SELECT COUNT(*)
FROM learning.learning_artifacts
WHERE source_type = 'claude'
  AND DATE(artifact_date) = CURRENT_DATE;
```

---

## ⚙️ 고급 설정

### Export 주기 조정

**작업 스케줄러:**
- 매일: 매일 오후 11시
- 주 1회: 매주 일요일 오후 11시
- 수동: 작업 스케줄러 사용 안 함

### 증분 백업 비활성화

전체 대화를 매번 저장하려면:
```python
# tools/monitor_claude_exports.py
def filter_new_conversations(conversations):
    # 필터링 안 함
    return conversations
```

### 알림 추가

```python
# tools/monitor_claude_exports.py
def send_notification(message):
    """Slack/Email/Discord 알림"""
    # 구현 추가

# process_export_file() 끝에서 호출
send_notification(f"Claude Export 완료: {len(artifact_ids)}개")
```

---

## 📈 성능

- **Export 시간**: 2-5분 (대화 수에 따라)
- **파싱 시간**: 1-3분 (ZIP 크기에 따라)
- **증분 필터링**: 수 초 (DB 쿼리)
- **전체 처리**: 5-10분

---

## 🔐 보안

- **쿠키 보관**: `temp/claude_cookies.json` (gitignore)
- **NAS 권한**: 적절한 파일 권한 설정
- **DB 인증**: PostgreSQL 비밀번호 보호

---

## ✅ 체크리스트

### 최초 설정

- [ ] Desktop에 Playwright 설치
- [ ] 쿠키 추출 완료
- [ ] NAS 또는 로컬 디렉토리 설정
- [ ] Export 테스트 성공
- [ ] Pi 모니터링 실행 확인
- [ ] 전체 Export → 파싱 → DB 저장 확인

### 일상 운영

- [ ] Desktop 작업 스케줄러 등록 (또는 수동 실행 계획)
- [ ] Pi 모니터링 서비스 등록
- [ ] 로그 주기적 확인
- [ ] DB 백업 설정
