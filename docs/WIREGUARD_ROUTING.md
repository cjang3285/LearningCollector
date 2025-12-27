# WireGuard를 통한 트래픽 라우팅

Pi에서 Claude.ai 접근 시 데스크톱 IP를 사용하도록 설정

## 현재 상황

- 데스크톱 Public IP: `222.112.226.63`
- Pi Public IP: `183.101.163.146`
- WireGuard VPN으로 연결됨

Cloudflare가 데스크톱에서 생성된 쿠키를 Pi IP에서 사용하는 것을 차단

## 해결 방법

### 옵션 1: 데스크톱을 Pi의 게이트웨이로 설정

Pi에서 Claude.ai로 가는 트래픽만 데스크톱을 통해 라우팅:

#### 1. Pi의 WireGuard 설정 수정

```bash
sudo nano /etc/wireguard/wg0.conf
```

`[Peer]` 섹션에 데스크톱 설정이 있다면:

```ini
[Peer]
# 데스크톱 피어
PublicKey = <데스크톱_공개키>
AllowedIPs = 10.0.0.x/32, 0.0.0.0/0  # 모든 트래픽을 데스크톱 통과
Endpoint = <데스크톱_IP>:51820
PersistentKeepalive = 25
```

**주의:** `AllowedIPs = 0.0.0.0/0`로 하면 **모든** 트래픽이 데스크톱을 거칩니다.

#### 2. 특정 도메인만 라우팅 (권장)

Claude.ai만 데스크톱을 거치도록:

```bash
# Claude.ai IP 확인
nslookup claude.ai

# 라우팅 추가 (일시적)
sudo ip route add <claude.ai_IP>/32 via <데스크톱_WG_IP> dev wg0

# 영구 설정: /etc/wireguard/wg0.conf의 PostUp에 추가
PostUp = ip route add <claude.ai_IP>/32 via <데스크톱_WG_IP> dev wg0
PostDown = ip route del <claude.ai_IP>/32 via <데스크톱_WG_IP> dev wg0
```

### 옵션 2: SOCKS 프록시 (간단함)

데스크톱에서 SSH SOCKS 프록시 실행:

#### 데스크톱에서:

이미 SSH로 Pi 접속 가능하니 역방향으로:

```bash
# Pi에서 데스크톱으로 SSH 터널
ssh -D 1080 -N desktop_user@desktop_ip
```

#### Pi의 Playwright 설정:

```python
self.context = self.browser.new_context(
    proxy={
        "server": "socks5://localhost:1080"
    }
)
```

### 옵션 3: 데스크톱에서만 Export (가장 간단)

```bash
python tools/export_from_desktop.py
```

- 데스크톱에서 Export 실행 (Cloudflare 통과)
- ZIP 파일만 Pi로 SCP 전송
- Pi는 DB 저장만 처리

## 추천

**옵션 3 (데스크톱에서 Export)**이 가장 간단하고 안전합니다:

1. Cloudflare 우회 필요 없음
2. WireGuard 설정 변경 불필요
3. 이미 SCP/SSH로 연결되어 있음
4. 쿠키는 계속 자동 업데이트됨

스케줄러에서:
- 데스크톱: `export_from_desktop.py` 실행 → ZIP 생성 및 Pi 전송
- Pi: ZIP 압축 해제 → DB 저장

## 현재 Export 스크립트 수정 필요

데스크톱에서 실행 시 `headless=False`, Pi에서는 `headless=True` 자동 감지
