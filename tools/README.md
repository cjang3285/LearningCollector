# Claude Cookie Auto-Extractor

로컬 Chrome/Edge 브라우저에서 Claude.ai 쿠키를 자동으로 추출하여 Raspberry Pi로 업로드하는 도구입니다.

## 사전 요구사항

### Windows
```bash
pip install pywin32 pycryptodome
```

### macOS
```bash
pip install keyring pycryptodome
```

### Linux
```bash
pip install pycryptodome
```

## 사용법

### 1. 로컬에서 쿠키만 추출
```bash
python tools/extract_claude_cookies.py
```

출력 파일: `temp/claude_cookies.json`

### 2. 추출 후 자동으로 Raspberry Pi에 업로드
```bash
python tools/extract_claude_cookies.py --upload
```

### 3. 커스텀 설정
```bash
python tools/extract_claude_cookies.py \
    --upload \
    --output temp/my_cookies.json \
    --pi-user jcw \
    --pi-host 183.101.163.146
```

## 동작 원리

1. **브라우저 쿠키 DB 찾기**
   - Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies`
   - macOS: `~/Library/Application Support/Google/Chrome/Default/Cookies`
   - Linux: `~/.config/google-chrome/Default/Cookies`

2. **쿠키 복호화**
   - Windows: DPAPI (Data Protection API)
   - macOS: Keychain + AES
   - Linux: 암호화 없음

3. **JSON 저장**
   - Playwright 호환 형식으로 저장

4. **SCP 업로드** (선택사항)
   - Raspberry Pi의 `~/learning-etl/temp/claude_cookies.json` 경로로 업로드

## 자동화 (선택사항)

### Windows Task Scheduler
매일 자동 실행하도록 설정:

```powershell
# 스크립트 생성: auto_extract_cookies.bat
@echo off
cd Z:\LearningConvertedToLog
python tools\extract_claude_cookies.py --upload
```

작업 스케줄러에서 매일 실행하도록 등록

### macOS/Linux cron
```bash
# crontab -e
0 9 * * * cd ~/LearningConvertedToLog && python tools/extract_claude_cookies.py --upload
```

## 주의사항

- Chrome/Edge가 실행 중이면 쿠키 DB가 잠겨 있을 수 있습니다 (자동 임시 복사 처리됨)
- 쿠키는 민감 정보이므로 안전하게 관리하세요
- SCP 업로드 시 SSH 키 인증이 설정되어 있어야 합니다

## 문제 해결

### "Chrome/Edge 쿠키 DB를 찾을 수 없습니다"
- Chrome 또는 Edge가 설치되어 있는지 확인
- 프로필 경로가 기본값이 아닌 경우 수동으로 지정 필요

### "scp 명령어를 찾을 수 없습니다"
- Windows: OpenSSH 클라이언트 설치 필요
- Git Bash 또는 WSL 사용 권장

### "쿠키를 찾을 수 없습니다"
- Chrome/Edge에서 claude.ai에 로그인되어 있는지 확인
- 시크릿 모드가 아닌 일반 모드로 로그인했는지 확인
