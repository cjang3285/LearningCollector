# Claude 수동 Export 가이드

## 현재 상태

✅ **다운로드 폴더 감시 프로그램 실행 중**

다음 파일을 자동으로 감지하여 NAS로 이동합니다:
- `conversations_*.zip`
- `claude_*.zip`
- `data-YYYY-MM-DD-*.zip` (Claude 공식 Export 형식)

---

## 수동 Export 방법

### 1단계: Claude.ai 접속

브라우저에서 https://claude.ai 접속 및 로그인

### 2단계: Settings 이동

**방법 A:** 단축키
```
Ctrl + ,
```

**방법 B:** 수동 클릭
1. 우측 상단 프로필 아이콘 클릭
2. "Settings" 클릭

### 3단계: Privacy → Export

1. 왼쪽 메뉴에서 **"Privacy"** 탭 클릭
2. **"Export data"** 버튼 클릭
3. 다운로드 시작 (몇 분 소요)

### 4단계: 자동 처리

✅ **자동으로 처리됩니다!**

다운로드가 완료되면:
1. 감시 프로그램이 자동 감지
2. NAS(`Z:\learning-etl\claude-exports`)로 이동
3. Pi가 자동으로 파싱 및 DB 저장

---

## 진행 상황 확인

### 다운로드 감시 로그

```bash
# Windows (Git Bash)
tail -f logs/download_watcher.log

# PowerShell
Get-Content logs/download_watcher.log -Wait -Tail 20
```

### Pi 파싱 로그

```bash
# SSH로 Pi 접속 후
tail -f ~/learning-etl/logs/export_monitor.log
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
```

---

## 문제 해결

### 다운로드 감시가 작동하지 않음

**확인:**
```bash
# 프로세스 확인 (Git Bash)
ps aux | grep watch_downloads

# 재시작
pythonw tools/watch_downloads.py
```

### NAS 접근 불가

**확인:**
```bash
# Z: 드라이브 마운트 확인
dir Z:\

# NAS 재마운트 (필요 시)
net use Z: \\nas-ip\share /user:username password
```

### Export 파일이 이동되지 않음

**수동 이동:**
```bash
# 파일 확인
dir ~/Downloads/conversations_*.zip

# 수동 이동
move "C:\Users\{USER}\Downloads\conversations_*.zip" "Z:\learning-etl\claude-exports\"
```

---

## 자동화 설정 (선택)

### Windows 시작 시 자동 실행

**방법 A: 작업 스케줄러**
1. 작업 스케줄러 열기
2. 기본 작업 만들기
3. 트리거: 로그온 시
4. 작업: `pythonw Z:\LearningConvertedToLog\tools\watch_downloads.py`

**방법 B: 시작 프로그램 폴더**
1. `Win+R` → `shell:startup`
2. 바로가기 생성:
   - 대상: `pythonw.exe Z:\LearningConvertedToLog\tools\watch_downloads.py`
   - 시작 위치: `Z:\LearningConvertedToLog`

---

## 주기

권장: **주 1회 Export**
- 매주 일요일 오후
- 또는 새로운 대화가 많을 때

---

## 체크리스트

### 최초 설정
- [x] 다운로드 감시 프로그램 설치 (`watchdog`)
- [x] 백그라운드 실행 확인
- [ ] 수동 Export 테스트
- [ ] NAS 이동 확인
- [ ] Pi 파싱 확인

### 일상 운영
- [ ] 주 1회 수동 Export
- [ ] 로그 주기적 확인
- [ ] DB 백업 확인
