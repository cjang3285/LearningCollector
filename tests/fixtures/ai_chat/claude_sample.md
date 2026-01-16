# 파이 나스 서버 와이어가드 연결 설정

**Created:** 12/17/2025 10:41:06
**Updated:** 12/17/2025 16:21:20
**Exported:** 12/29/2025 20:03:34
**Link:** [https://claude.ai/chat/7cb600ba-fb9e-447c-883d-6ee1f0f83864](https://claude.ai/chat/7cb600ba-fb9e-447c-883d-6ee1f0f83864)

**Human:** 지금부터 나스 서버 연결을 시작합니다. 파이에서 나스 smb가 돌고 있고 현재 와이어가드를 사용해 노트북을 파이랑 내부, 외부 네트웍에서 접속이 가능하게 만드는 것이 목표입니다. 이전 대화 중 나스 서버를 다룬 대화를 참고하여 현 인프라 상태, 공개키, 프라이빗키, 컨피그 현황 등을 파악하고 노트북에서 파이의 나스 서버에 내부서나 외부서나 연결 가능하도록 합시다

**Assistant:** 이전 대화에서 NAS 서버 관련 내용을 찾아보겠습니다.

과거 대화에서 **172.30.x.x** 대역을 쓰셨네요.

KT 공유기가 172.30.1.254이고, 라즈베리파이는 **172.30.1.95**였습니다.

**현재 인프라 상태:**

```
인터넷
  ↓
공인 IP: 183.101.163.146 (KT 공유기)
  ↓
사설 네트워크: 172.30.1.0/24
  ├─ 공유기: 172.30.1.254
  └─ 라즈베리파이: 172.30.1.95
```

**이미 구축된 서비스:**

1. SMB/Samba NAS 서버
   - 서비스: smbd (포트 445)
   - 사용자: jcw
   - 공유 폴더: /home/jcw/shared
   - 접근: smb://172.30.1.95 (내부), smb://10.0.0.1 (VPN)

2. WireGuard VPN 서버
   - 인터페이스: wg0
   - 서버 내부 IP: 10.0.0.1/24
   - 외부 포트: 51820 (UDP)
   - 포트포워딩: 183.101.163.146:51820 → 172.30.1.95:51820

**기존 키 정보:**

서버 (라즈베리파이) 키:
- Private: eMTzMuT2gvwfszqxqR7zqOWlkuKMeS3mfoz5Ar2edm4=
- Public: 0Kn+cTS0TM7xB7ORwPYbW2hCAfziT6/O9ymObJeaHxs=

iPad 클라이언트 키:
- Private: qEMFym395twiCrbfJtk+NBiopK/VpOnIDLHNa2PS/U8=
- Public: hmwQ3NRNvdkOrJZQaV60Cp1JfzmtXyOGS+2J1w2Bu18=

이제 할 일: 노트북 클라이언트 설정

노트북 OS가 뭔가요? (Windows/Mac/Linux)

**Human:** 윈도우

**Assistant:** 좋습니다! Windows 노트북에서 WireGuard 클라이언트를 설정하겠습니다.

## Step 1: 노트북 클라이언트 키 생성

먼저 라즈베리파이에서 노트북용 키를 생성합니다.

```bash
# 라즈베리파이에 SSH 접속
ssh jcw@172.30.1.95

# 노트북용 키 생성
cd /etc/wireguard
sudo sh -c 'wg genkey | tee laptop_private.key | wg pubkey > laptop_public.key'

# 생성된 키 확인
echo "=== 노트북 Private Key ==="
sudo cat laptop_private.key

echo "=== 노트북 Public Key ==="
sudo cat laptop_public.key
```

생성된 키를 메모해두세요!

## Step 2: 서버 설정 업데이트

```bash
sudo nano /etc/wireguard/wg0.conf
```

파일 맨 아래에 노트북 Peer 추가:

```ini
[Peer]
PublicKey = <방금 생성한 laptop_public.key 내용>
AllowedIPs = 10.0.0.3/32
```

저장 후 WireGuard 재시작:

```bash
sudo systemctl restart wg-quick@wg0
```

## Step 3: Windows에 WireGuard 설치

노트북에서:

1. https://www.wireguard.com/install/ 접속
2. Windows Installer 다운로드
3. 설치 실행

## Step 4: Windows 클라이언트 설정

WireGuard 앱 실행 후:

1. 좌측 하단 "Add Tunnel" → "Add empty tunnel..." 클릭
2. 자동 생성된 Public Key는 무시하고 아래 내용으로 전체 교체:

```ini
[Interface]
PrivateKey = <laptop_private.key 내용>
Address = 10.0.0.3/24
DNS = 8.8.8.8

[Peer]
PublicKey = 0Kn+cTS0TM7xB7ORwPYbW2hCAfziT6/O9ymObJeaHxs=
Endpoint = 183.101.163.146:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

3. Name: Home-VPN (원하는 이름)
4. Save 클릭

**Human:** 이거 줄바꿈해서 다시 줘

**Assistant:** ```ini
[Interface]
PrivateKey = yO7OxDpFXcPN7bN3mI4X5PTuFUQi4I201gBogI1NCVQ=
Address = 10.0.0.3/24
DNS = 8.8.8.8

[Peer]
PublicKey = 0Kn+cTS0TM7xB7ORwPYbW2hCAfziT6/O9ymObJeaHxs=
Endpoint = 183.101.163.146:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

이걸 WireGuard 앱에 붙여넣으시면 됩니다!

그리고 노트북의 **Public Key**를 확인해야 합니다. WireGuard 앱에서:

1. 저장한 터널 클릭
2. Edit 클릭
3. [Interface] 섹션 아래에 Public key: 라고 자동 표시되는 값

그 Public Key를 복사해서 알려주시면 서버 설정을 완료해드릴게요!

**Human:** 노트북에서 10.0.0.1 로 해서 성공했어

**Assistant:** 🎉 완벽합니다!

노트북이 VPN을 통해 NAS에 성공적으로 연결되었네요!

---

## 최종 확인

현재 상태:
- **노트북**: 10.0.0.3 (VPN 내부 IP)
- **iPad**: 10.0.0.2 (VPN 내부 IP)
- **라즈베리파이**: 10.0.0.1 (VPN 서버)

**접속 방법:**

내부 네트워크 (같은 WiFi):
```
\\172.30.1.95\shared
```

외부 네트워크 (VPN 연결 시):
```
\\10.0.0.1\shared
```

---

한 가지 확인

혹시 노트북의 Public Key를 서버에 등록했나요?

```bash
ssh jcw@172.30.1.95
sudo wg show
```

여기서 **peer 3개**가 보여야 합니다:
1. iPad (hmwQ3N...)
2. 노트북 (새로 추가한 키)
3. (혹시 다른 클라이언트가 있다면)

만약 노트북 peer가 안 보이는데도 연결되었다면, 서버 설정에 추가해두면 더 안정적입니다!

결과 확인:
- sudo wg show 출력 결과 보여주시겠어요?
- handshake가 성공했는지 확인하고 싶습니다!

**Human:** jcw@jcw:~$ sudo wg show
interface: wg0
  public key: 0Kn+cTS0TM7xB7ORwPYbW2hCAfziT6/O9ymObJeaHxs=
  private key: (hidden)
  listening port: 51820
peer: r4+22bC7BV9RNJmO32ZdtlxoxyZW+Ul56dsTTpu3Y2Y=
  endpoint: 172.30.1.254:53658
  allowed ips: 10.0.0.3/32
  latest handshake: 1 minute, 53 seconds ago
  transfer: 7.39 MiB received, 254.88 MiB sent
peer: hmwQ3NRNvdkOrJZQaV60Cp1JfzmtXyOGS+2J1w2Bu18=
  endpoint: 172.30.1.254:51947
  allowed ips: 10.0.0.2/32
  latest handshake: 2 minutes, 36 seconds ago
  transfer: 605.13 KiB received, 2.13 MiB sent

**Assistant:** 완벽합니다! 🎉

## 현재 연결 상태

**서버 정보:**
- Interface: wg0
- Public Key: 0Kn+cTS0TM7xB7ORwPYbW2hCAfziT6/O9ymObJeaHxs=
- Listening Port: 51820

**연결된 클라이언트:**

### 1. 노트북 (Windows)
```
Public Key: r4+22bC7BV9RNJmO32ZdtlxoxyZW+Ul56dsTTpu3Y2Y=
VPN IP: 10.0.0.3
Latest handshake: 1분 53초 전 ✅
Transfer: 7.39 MiB 받음, 254.88 MiB 보냄
```

### 2. iPad
```
Public Key: hmwQ3NRNvdkOrJZQaV60Cp1JfzmtXyOGS+2J1w2Bu18=
VPN IP: 10.0.0.2
Latest handshake: 2분 36초 전 ✅
Transfer: 605.13 KiB 받음, 2.13 MiB 보냄
```

---

## 성공! 완료된 시스템

```
                    인터넷
                      ↓
          공인 IP: 183.101.163.146
                      ↓
            ┌─────────┴─────────┐
            │   KT 공유기        │
            │ (172.30.1.254)    │
            │                   │
            │ 포트포워딩:        │
            │ 51820→172.30.1.95 │
            └─────────┬─────────┘
                      ↓
            ┌─────────┴─────────┐
            │  라즈베리파이      │
            │  (172.30.1.95)    │
            │                   │
            │ WireGuard 서버:   │
            │ - 10.0.0.1        │
            │                   │
            │ NAS 서버:         │
            │ - smb://10.0.0.1  │
            └───────────────────┘
                      ↑
              ┌───────┴───────┐
              │               │
          VPN 터널         VPN 터널
              │               │
          ┌───┴───┐       ┌───┴───┐
          │ 노트북 │       │ iPad  │
          │10.0.0.3│      │10.0.0.2│
          └────────┘       └───────┘
```

---

## 사용 방법 정리

**내부 네트워크 (집 WiFi)**
- VPN 끄기
- 노트북: \\172.30.1.95\shared
- iPad: smb://172.30.1.95

**외부 네트워크 (학교, 카페 등)**
1. WireGuard 켜기
2. 노트북: \\10.0.0.1\shared
3. iPad: smb://10.0.0.1

**네트워크 드라이브로 매핑 (선택)**

```cmd
net use Z: \\10.0.0.1\shared /user:jcw /persistent:yes
```

---

## 주요 성과

✅ Samba NAS 서버 - 파일 공유
✅ WireGuard VPN - 안전한 원격 접속
✅ 포트포워딩 - 외부에서 접근 가능
✅ 멀티 클라이언트 - iPad + 노트북 동시 연결

**축하합니다! 완전한 원격 NAS 시스템을 구축했습니다!** 🎊

**Human:** vpn 서버가 이해가 어려운데 노트북이랑 패드 입장에선 어디로 접근한거지 와이어가드 중앙서버를 통한거야 아니면 내 공유기로?

**Assistant:** 좋은 질문입니다! 핵심을 정확히 짚으셨네요.

## 답: 당신의 공유기로 직접 접근합니다

**WireGuard는 중앙 서버가 없습니다.** P2P (Peer-to-Peer) 방식이에요.

---

## 실제 연결 경로

**노트북/iPad가 외부에서 VPN 연결할 때:**

```
노트북 (카페 WiFi)
  ↓
  ↓ UDP 패킷 전송
  ↓ 목적지: 183.101.163.146:51820
  ↓
인터넷 (여러 라우터 거침)
  ↓
당신 집 공유기 (183.101.163.146)
  ↓ 포트포워딩 규칙 확인
  ↓ "51820 포트 → 172.30.1.95로 보내라"
  ↓
라즈베리파이 (172.30.1.95:51820)
  ↓ WireGuard 서버가 받음
  ↓ 공개키 확인 (인증)
  ↓ 암호화 터널 수립
  ✅ 연결 완료
```

---

## WireGuard의 동작 방식

**중앙 서버 없음**
- Anthropic 서버 ❌
- WireGuard 회사 서버 ❌
- 당신 집 라즈베리파이 = 서버 ✅

**실제 데이터 흐름**

```
노트북에서 파일 요청:
  ↓
노트북 WireGuard 클라이언트
  ↓ 암호화
  ↓ UDP 패킷으로 포장
  ↓ 목적지: 183.101.163.146:51820
  ↓
인터넷 직접 전송
  ↓
집 공유기
  ↓ NAT + 포트포워딩
  ↓
라즈베리파이 WireGuard
  ↓ 복호화
  ↓ 내부 IP로 변환 (10.0.0.3 → 172.30.1.95)
  ↓
Samba 서버
  ↓ 파일 읽기
  ↓
역방향으로 암호화해서 전송
  ↓
노트북 수신
```

---

## 중요한 점

**Endpoint 설정 보셨죠?**

```ini
[Peer]
Endpoint = 183.101.163.146:51820
```

이게 **"어디로 연결할지"**를 지정하는 겁니다.

- 183.101.163.146 = 당신 집 공인 IP (KT에서 할당)
- :51820 = WireGuard 포트

**공유기 포트포워딩이 필수인 이유**

```
외부 → 183.101.163.146:51820
      ↓
      공유기가 받음
      ↓
      "이 패킷 어디로 보내지?"
      ↓
      포트포워딩 규칙: 51820 → 172.30.1.95
      ↓
      라즈베리파이로 전달
```

포트포워딩 없으면:
- 공유기가 패킷을 받기는 함
- 근데 어느 내부 기기로 보낼지 몰라서 버림 ❌

---

## 비교: 다른 VPN 서비스

**상용 VPN (NordVPN, ExpressVPN 등)**

```
당신 PC
  ↓
NordVPN 중앙 서버 (미국, 일본 등)
  ↓
목적지 웹사이트
```

- 중앙 서버 존재 ✅
- 트래픽이 VPN 회사 서버 경유
- 당신 IP 숨기기용

**당신의 WireGuard**

```
노트북/iPad
  ↓
당신 집 라즈베리파이 (직접 연결)
  ↓
집 네트워크/인터넷
```

- 중앙 서버 없음 ❌
- 집으로 "터널" 뚫어서 직접 연결
- 집 네트워크 자원(NAS) 접근용

---

## 왜 이렇게 설계했나?

**장점:**
1. 속도 빠름 - 중간 서버 없이 직접 연결
2. 프라이버시 - 제3자 서버 안 거침
3. 비용 없음 - 상용 VPN 구독료 불필요
4. 완전 통제 - 당신 서버, 당신 규칙

**단점:**
1. 집 IP 노출 - 당신 공인 IP로 직접 연결
2. 집 인터넷 의존 - 집 인터넷 끊기면 접속 불가
3. 속도 제한 - 집 인터넷 업로드 속도에 제한

---

## 정리하면

**질문: "어디로 접근한 거지?"**

**답:**
- ❌ WireGuard 중앙 서버
- ✅ **당신 집 공유기 (183.101.163.146) → 라즈베리파이 (172.30.1.95)**

**WireGuard는:**
- 그냥 암호화 터널 프로토콜
- 클라이언트와 서버를 직접 연결
- 중간에 아무도 안 거침

**마치:**
- 집과 카페 사이에 암호화된 비밀 파이프를 만든 거예요
- 그 파이프를 통해 집 네트워크에 들어가는 거죠

이해되셨나요? 🤔

**Human:** 왜 둘 중 하나만 근데 접근이 되는거지 VPN 키면 10001로만 끄면 로컬 주소로만 들어가지도 다른 건 안되네

**Assistant:** 아하! 정확한 관찰입니다. 이게 **정상 동작**이에요.

---

## 왜 이런 현상이 생기나?

### VPN 켰을 때: \\172.30.1.95 안 됨

**원인: AllowedIPs = 0.0.0.0/0**

WireGuard 설정 기억나시죠?

```ini
[Peer]
AllowedIPs = 0.0.0.0/0
```

이 설정의 의미:
- **"모든 트래픽을 VPN 터널로 보내라"**
- 172.30.1.95로 가는 패킷도 VPN 터널로 들어감
- 근데 172.30.1.95는 VPN 내부에선 10.0.0.1로 매핑됨
- 결과: 172.30.1.95는 접근 안 됨

**동작 원리:**

```
노트북에서 \\172.30.1.95 시도
  ↓
Windows: "172.30.1.95로 패킷 보내야지"
  ↓
WireGuard: "AllowedIPs에 0.0.0.0/0 있으니 내가 처리!"
  ↓
패킷을 VPN 터널로 보냄
  ↓
라즈베리파이 WireGuard: "172.30.1.95? 그게 나네"
  ↓
루프백 또는 잘못된 라우팅
  ↓
❌ 연결 실패
```

---

### VPN 껐을 때: \\10.0.0.1 안 됨

**원인: VPN 터널이 없음**

```
노트북에서 \\10.0.0.1 시도
  ↓
Windows: "10.0.0.1로 패킷 보내야지"
  ↓
라우팅 테이블 확인: "10.0.0.x는 wg0 인터페이스"
  ↓
근데 VPN 꺼져있음 (wg0 인터페이스 없음)
  ↓
❌ "네트워크에 연결할 수 없습니다"
```

---

## 해결 방법 2가지

### 방법 1: Split Tunneling (분할 터널링) - 추천

VPN 켰을 때도 로컬 네트워크 직접 접근 가능하게 만들기

**WireGuard 설정 수정:**

```ini
[Interface]
PrivateKey = yO7OxDpFXcPN7bN3mI4X5PTuFUQi4I201gBogI1NCVQ=
Address = 10.0.0.3/24
DNS = 8.8.8.8

[Peer]
PublicKey = 0Kn+cTS0TM7xB7ORwPYbW2hCAfziT6/O9ymObJeaHxs=
Endpoint = 183.101.163.146:51820
AllowedIPs = 10.0.0.0/24, 172.30.1.0/24
PersistentKeepalive = 25
```

**변경 사항:**
- ~~AllowedIPs = 0.0.0.0/0~~ (모든 트래픽)
- ✅ AllowedIPs = 10.0.0.0/24, 172.30.1.0/24 (VPN + 집 네트워크만)

**장점:**
- VPN 켜도 \\172.30.1.95 접근 가능
- 일반 인터넷은 VPN 안 거침 (빠름)
- 집 네트워크 자원만 VPN 사용

**단점:**
- 외부에서는 172.30.1.95 접근 여전히 안 됨 (당연함)

---

### 방법 2: 현재 상태 유지 - 간단함

**규칙:**
- VPN ON → Z: (\\10.0.0.1) 사용
- VPN OFF → Y: (\\172.30.1.95) 사용

**장점:**
- 설정 변경 없음
- 명확한 구분

**단점:**
- 두 개 드라이브 관리

---

## 추천: Split Tunneling

집 WiFi에서 VPN 켜면:
- \\10.0.0.1 ✅
- \\172.30.1.95 ✅ (둘 다 작동)

외부에서 VPN 켜면:
- \\10.0.0.1 ✅ (VPN 터널 통해)
- \\172.30.1.95 ❌ (외부 네트워크라 당연히 안 됨)

---

## Split Tunneling 적용하시겠어요?

**Windows WireGuard 앱에서:**

1. 터널 Edit 클릭
2. AllowedIPs 줄 수정:
   ```
   AllowedIPs = 10.0.0.0/24, 172.30.1.0/24
   ```
3. Save
4. VPN 다시 켜기

**테스트:**
- VPN 켠 상태에서
- \\172.30.1.95\shared 접속해보기

어떻게 하시겠어요?
