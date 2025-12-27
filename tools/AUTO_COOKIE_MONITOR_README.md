# Claude.ai 쿠키 자동 모니터링

Claude.ai 접속을 자동으로 감지하여 쿠키를 추출하고 Raspberry Pi로 전송하는 백그라운드 서비스입니다.

## 🎯 핵심 아이디어

**"Claude.ai를 사용할 때마다 자동으로 쿠키를 감지하고 Pi로 전송"**

데스크톱/노트북을 항상 켜둘 필요 없이, Claude를 사용하는 시점에 자동으로 쿠키가 업데이트됩니다.

## 🚀 동작 방식

```
1. 백그라운드 모니터 실행 (Windows 시작 시 자동)
   ↓
2. Chrome/Edge 프로세스 모니터링 (1분마다)
   ↓
3. claude.ai 접속 감지
   ↓
4. 쿠키 자동 추출 (Playwright)
   ↓
5. Raspberry Pi로 전송 (SCP)
   ↓
6. 1시간 대기 (중복 추출 방지)
```

## 📦 설치

### 1. 필요한 라이브러리 설치

```bash
pip install playwright psutil winshell pywin32
playwright install chromium
```

### 2. 시작프로그램 등록

```bash
python tools/setup_startup.py
```

등록 완료! Windows 부팅 시 자동으로 백그라운드에서 실행됩니다.

## ✅ 장점

- ✅ **완전 자동화** - 아무것도 할 필요 없음
- ✅ **백그라운드 실행** - 콘솔 창 없음
- ✅ **중복 방지** - 1시간에 한 번만 추출
- ✅ **리소스 효율적** - 1분마다 가벼운 프로세스 체크만
- ✅ **데스크톱 ON/OFF 무관** - 켜져있을 때만 작동
- ✅ **즉시 반영** - Claude 사용하면 바로 쿠키 업데이트

## 📊 모니터링

### 로그 확인

```bash
cat temp/cookie_monitor.log
```

또는

```
notepad temp\cookie_monitor.log
```

### 로그 예시

```
[2025-12-27 10:03:54] Claude.ai 쿠키 자동 모니터링 시작
[2025-12-27 10:03:54] 체크 간격: 60초
[2025-12-27 10:03:54] 추출 간격: 3600초 (1시간)
[2025-12-27 10:05:12] 🌐 Claude.ai 접속 감지!
[2025-12-27 10:05:15] 🍪 쿠키 추출 시작...
[2025-12-27 10:05:18] ✅ 쿠키 추출 및 업로드 성공!
```

### 마지막 추출 시간 확인

```bash
cat temp/last_extract.txt
```

## ⚙️ 설정 변경

`tools/auto_cookie_monitor.py` 파일에서:

```python
CHECK_INTERVAL = 60      # 체크 간격 (초)
EXTRACT_COOLDOWN = 3600  # 추출 간격 (초) - 1시간
```

## 🛠️ 문제 해결

### 모니터가 작동하지 않는 경우

1. **프로세스 확인**
   ```bash
   # Windows 작업 관리자
   pythonw.exe 프로세스 확인
   ```

2. **수동 실행 (디버깅)**
   ```bash
   python tools/auto_cookie_monitor.py
   ```

3. **로그 확인**
   ```bash
   cat temp/cookie_monitor.log
   ```

### Claude 접속이 감지되지 않는 경우

Chrome 프로세스 명령줄에 'claude.ai'가 포함되어야 합니다.
일반적으로 탭이 열려있으면 자동으로 감지됩니다.

## 🔄 재설치

기존 모니터 제거 후 재등록:

```bash
python tools/setup_startup.py --remove
python tools/setup_startup.py
```

## 🆚 vs 단순 추출 모드

| 기능 | 모니터링 모드 | 단순 추출 모드 |
|------|--------------|---------------|
| **실행 시점** | Claude 접속 시 | 부팅 시 1회 |
| **백그라운드** | ✅ 계속 실행 | ✅ 1회 실행 |
| **자동 감지** | ✅ | ❌ |
| **리소스 사용** | 매우 낮음 | 낮음 |
| **추천** | ✅ **추천** | 수동 제어 선호 시 |

## 📝 참고

- 모니터는 `pythonw.exe`로 실행되어 콘솔 창이 보이지 않습니다
- Windows 부팅 시 자동으로 시작됩니다
- 시스템 트레이 아이콘은 없습니다 (완전 백그라운드)
- 작업 관리자에서 pythonw.exe 프로세스로 확인 가능

## ❓ FAQ

**Q: 항상 실행되나요?**
A: 네, Windows가 켜져있는 동안 백그라운드에서 계속 실행됩니다.

**Q: 리소스를 많이 사용하나요?**
A: 아니요, 1분마다 프로세스 목록만 체크하므로 CPU 사용량이 거의 없습니다.

**Q: 데스크톱을 꺼도 Pi는 작동하나요?**
A: 네, Pi는 마지막으로 받은 쿠키로 계속 작동합니다.

**Q: 쿠키가 매번 추출되나요?**
A: 아니요, 1시간에 한 번만 추출됩니다 (중복 방지).
