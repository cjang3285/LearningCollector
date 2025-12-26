# Claude.ai 쿠키 수동 설정 가이드

Cloudflare Turnstile 우회를 위해 일반 브라우저에서 로그인 후 쿠키를 추출하여 사용합니다.

## 방법 1: 브라우저 개발자 도구 사용

### 1. Chrome/Edge에서 쿠키 추출

1. **Chrome/Edge 브라우저로 claude.ai 접속 및 로그인**
2. **F12** 키를 눌러 개발자 도구 열기
3. **Application** 탭 → **Storage** → **Cookies** → `https://claude.ai` 클릭
4. 모든 쿠키를 복사 (특히 중요한 것들):
   - `__cf_bm`
   - `__Secure-` 로 시작하는 쿠키들
   - `sessionKey` 또는 세션 관련 쿠키

### 2. 콘솔에서 자동 추출

개발자 도구 **Console** 탭에서 아래 코드 실행:

```javascript
copy(JSON.stringify(
  document.cookie.split(';').map(c => {
    const [name, ...value] = c.trim().split('=');
    return {
      name: name,
      value: value.join('='),
      domain: '.claude.ai',
      path: '/',
      secure: true,
      httpOnly: false,
      sameSite: 'Lax'
    };
  })
));
```

클립보드에 JSON 형태로 복사됩니다.

### 3. Raspberry Pi에 쿠키 파일 생성

```bash
cd ~/learning-etl
nano temp/claude_cookies.json
```

복사한 JSON을 붙여넣고 저장 (Ctrl+X, Y, Enter)

## 방법 2: EditThisCookie 확장 프로그램 사용

1. **Chrome에 EditThisCookie 설치**
   - https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg

2. **claude.ai 로그인**

3. **EditThisCookie 아이콘 클릭** → **Export** 버튼 클릭

4. **클립보드에 JSON 복사됨**

5. **Raspberry Pi에 붙여넣기** (위와 동일)

## 쿠키 파일 형식

`temp/claude_cookies.json` 파일은 다음 형식이어야 합니다:

```json
[
  {
    "name": "__cf_bm",
    "value": "xxxxx...",
    "domain": ".claude.ai",
    "path": "/",
    "secure": true,
    "httpOnly": true,
    "sameSite": "None"
  },
  {
    "name": "session_key",
    "value": "xxxxx...",
    "domain": ".claude.ai",
    "path": "/",
    "secure": true,
    "httpOnly": true,
    "sameSite": "Lax"
  }
]
```

## 테스트

```bash
cd ~/learning-etl
source venv/bin/activate
python -m export.claude_export
```

쿠키가 유효하면 Cloudflare 우회 없이 바로 로그인됩니다!

## 주의사항

- 쿠키는 일정 시간 후 만료됩니다 (보통 1-7일)
- 만료되면 다시 추출해야 합니다
- `temp/claude_cookies.json`은 민감 정보이므로 공유하지 마세요 (이미 .gitignore 처리됨)
