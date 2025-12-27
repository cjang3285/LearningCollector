# Claude Export Cloudflare 문제 분석 및 해결책

## 문제 요약

Desktop/Laptop에서 Playwright를 사용하여 Claude.ai Export를 자동화하려 할 때, **Cloudflare Turnstile 챌린지**가 발생하여 자동화가 차단됨.

## 근본 원인 분석

### 1. Cloudflare가 Playwright를 Bot으로 감지

**감지 요인:**
- `--enable-automation` 플래그
- `navigator.webdriver = true` 속성
- Chrome DevTools Protocol (CDP) 사용 패턴
- 비정상적인 브라우저 헤더 및 동작 패턴

**증거:**
```
Browser logs:
--enable-automation --disable-infobars --disable-search-engine-choice-screen
--disable-sync --no-sandbox --profile-directory=Profile 1
```

### 2. 쿠키만으로는 불충분

- ✅ 쿠키 추출 성공 (8개 쿠키)
- ✅ 홈페이지(claude.ai) 접속 성공
- ❌ Settings 페이지 이동 시 Cloudflare 챌린지 발생
- ❌ 자동 해결 시도 90초 타임아웃

**페이지 텍스트:**
```
사람인지 확인하는 중입니다. 이 작업은 몇 초 정도 소요될 수 있습니다.
계속하기 전에 claude.ai에서 연결의 보안을 검토해야 합니다.
Ray ID: 9b458949683429e5
```

### 3. Chrome Profile 사용 시도 실패

**시도:**
```python
context = p.chromium.launch_persistent_context(
    user_data_dir=str(chrome_user_data),
    profile_directory='Profile 1'
)
```

**결과:**
```
TargetClosedError: Target page, context or browser has been closed
exitCode=21
```

**원인:** Chrome이 이미 실행 중일 때 같은 프로필을 사용하려 하면 충돌 발생

## 시도한 해결책 및 실패 이유

### ❌ 시도 1: Cloudflare 자동 대기

**코드:**
```python
page.wait_for_function(
    "() => !document.querySelector('iframe[src*=\"challenges.cloudflare.com\"]')",
    timeout=30000
)
```

**결과:** 타임아웃 (수동 체크박스 클릭 필요)

---

### ❌ 시도 2: Chrome 프로필 재사용

**코드:**
```python
launch_persistent_context(
    user_data_dir=chrome_user_data,
    profile_directory='Profile 1'
)
```

**결과:** exitCode=21 (프로필 충돌)

---

### ❌ 시도 3: 증분 재시도 (3번)

**코드:**
```python
for attempt in range(3):
    # Cloudflare 감지 및 대기
    page.wait_for_function(...)
```

**결과:** 3번 모두 타임아웃 (90초 소비)

---

### ❌ 시도 4: 수동 개입 허용

**코드:**
```python
print("브라우저 창에서 '사람인지 확인' 체크박스를 클릭하세요.")
page.wait_for_function(..., timeout=300000)  # 5분
```

**결과:** `TargetClosedError` - 브라우저가 강제로 닫힘

## 작동하는 해결책

### ✅ 옵션 A: API 직접 호출 (권장)

**장점:**
- Cloudflare 우회 (브라우저 없음)
- 빠른 속도
- 안정적

**단점:**
- sessionKey 필요 (수동 추출)
- 비공식 API (변경 가능성)

**구현:**
```bash
# 1회 설정: sessionKey 수동 추출
# Chrome DevTools → Application → Cookies → sessionKey 복사

# 자동 Export
python export/claude_api_direct.py
```

**파일:** `export/claude_api_direct.py`

---

### ✅ 옵션 B: 다운로드 폴더 모니터링 (가장 단순)

**개념:**
1. 사용자가 수동으로 Settings → Privacy → Export 클릭
2. 스크립트가 Downloads 폴더를 감시
3. `conversations_*.zip` 파일 감지 시 자동으로 NAS로 이동

**장점:**
- Cloudflare 문제 없음 (수동 Export)
- 100% 안정적
- 간단한 구현

**단점:**
- Export 버튼 클릭은 수동
- 완전 자동화 아님

**구현:**
```python
# tools/watch_downloads.py
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DownloadHandler(FileSystemEventHandler):
    def on_created(self, event):
        if 'conversations_' in event.src_path and event.src_path.endswith('.zip'):
            # NAS로 이동
            move_to_nas(event.src_path)

# 실행
observer = Observer()
observer.schedule(DownloadHandler(), str(DOWNLOADS_DIR))
observer.start()
```

---

### ✅ 옵션 C: undetected-chromedriver (우회 가능)

**개념:** Cloudflare 감지를 우회하는 패치된 ChromeDriver 사용

**장점:**
- Playwright 대신 Selenium 사용
- 일부 Bot 감지 우회

**단점:**
- 유지보수 필요 (Cloudflare 업데이트 대응)
- 100% 성공 보장 없음

**구현:**
```bash
pip install undetected-chromedriver
```

```python
import undetected_chromedriver as uc

driver = uc.Chrome()
driver.get('https://claude.ai/settings')
# Privacy → Export 클릭
```

---

## 권장 솔루션 조합

### 일상 사용: 옵션 B (다운로드 감시)

**워크플로우:**
1. Windows 시작 시 `watch_downloads.py` 백그라운드 실행
2. 주 1회: 수동으로 Claude.ai → Settings → Privacy → Export 클릭
3. 스크립트가 자동으로 다운로드 감지 → NAS 이동
4. Pi가 자동으로 파싱 및 DB 저장

**장점:**
- 버튼 클릭 1회만 수동
- 안정적 (Cloudflare 영향 없음)
- 설정 후 잊어도 됨

---

### 고급 사용: 옵션 A (API)

**워크플로우:**
1. 최초 1회: Chrome DevTools로 sessionKey 복사
2. 자동 실행: `python export/claude_api_direct.py`
3. Pi로 자동 전송 및 파싱

**장점:**
- 완전 자동화
- 빠른 속도

**단점:**
- sessionKey 주기적 갱신 필요 (3-6개월?)
- 비공식 API (변경 가능성)

---

## 구현 파일 정리

### 작동하는 파일:
- ✅ `export/claude_api_direct.py` - API 직접 호출
- ✅ `tools/extract_cookies_playwright.py` - 쿠키 추출
- ✅ `tools/monitor_claude_exports.py` - Pi 모니터링

### 작동하지 않는 파일 (Cloudflare):
- ❌ `tools/auto_export_desktop.py` - Playwright 자동화
- ❌ `tools/auto_export_with_profile.py` - Chrome 프로필 사용
- ❌ `tools/auto_export_manual.py` - 수동 개입 허용

---

## 다음 단계

### 옵션 B 구현 (권장)

1. **다운로드 폴더 감시 스크립트 작성**
   ```bash
   python tools/create_download_watcher.py
   ```

2. **Windows 시작 프로그램 등록**
   ```bash
   python tools/setup_startup.py --watch-downloads
   ```

3. **테스트**
   - 수동으로 Claude.ai Export 클릭
   - 다운로드 → NAS 이동 확인
   - Pi 파싱 확인

### 옵션 A 시도 (선택)

1. **sessionKey 추출**
   - Chrome에서 claude.ai 로그인
   - F12 → Application → Cookies
   - `sessionKey` 값 복사 (sk-ant-sid01...로 시작)

2. **API Export 테스트**
   ```bash
   python export/claude_api_direct.py
   ```

3. **성공 시 cron/스케줄러 등록**

---

## 결론

**Playwright 자동화는 현재 Cloudflare로 인해 불가능**합니다.

**권장 솔루션:**
- **단기:** 옵션 B (다운로드 감시) - 안정적이고 간단
- **장기:** 옵션 A (API) - 완전 자동화 가능

**구현 우선순위:**
1. 옵션 B 구현 (1시간)
2. 테스트 및 문서화
3. 옵션 A는 필요 시 추가
