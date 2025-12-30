# Docker Compose 완전 구현 설계
## VPN + NAS + LearningETL 전체 스택

---

## 🎯 구현 가능성: **100% 가능!** ✅

---

## 🏗️ 전체 아키텍처

```
┌────────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                         │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  WireGuard   │  │  PostgreSQL  │  │  NAS Processor     │   │
│  │  VPN Server  │  │  Database    │  │  (Server)          │   │
│  │              │  │              │  │                    │   │
│  │  wg0:        │  │  Port: 5432  │  │  /mnt/nas/inbox    │   │
│  │  10.8.0.1/24 │  │              │  │  watchdog 감시     │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│         │                  │                    │               │
│         │                  │                    │               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  NAS Share   │  │  CLI Tools   │  │  NAS Agent         │   │
│  │  (SMB/NFS)   │  │  (Query)     │  │  (Client)          │   │
│  │              │  │              │  │                    │   │
│  │  /volume1/   │  │  python cli  │  │  Downloads 감시    │   │
│  │  learningetl │  │              │  │  NAS 업로드        │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## 📦 Docker Compose 구성

### docker-compose.yml

```yaml
version: '3.8'

services:
  # ========================================
  # 1. WireGuard VPN Server
  # ========================================
  wireguard:
    image: linuxserver/wireguard:latest
    container_name: learningetl-wireguard
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Asia/Seoul
      - SERVERURL=your-public-ip  # 공인 IP
      - SERVERPORT=51820
      - PEERS=notebook,raspberry-pi  # 클라이언트들
      - PEERDNS=auto
      - INTERNAL_SUBNET=10.8.0.0/24
    volumes:
      - ./config/wireguard:/config
      - /lib/modules:/lib/modules
    ports:
      - "51820:51820/udp"
    sysctls:
      - net.ipv4.conf.all.src_valid_mark=1
    restart: unless-stopped
    networks:
      learningetl_net:
        ipv4_address: 10.8.0.1

  # ========================================
  # 2. PostgreSQL Database
  # ========================================
  postgres:
    image: postgres:16-alpine
    container_name: learningetl-postgres
    environment:
      - POSTGRES_DB=learning
      - POSTGRES_USER=learning_user
      - POSTGRES_PASSWORD=secure_password
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/create-schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U learning_user -d learning"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - learningetl_net

  # ========================================
  # 3. NAS Share (Samba Server)
  # ========================================
  nas:
    image: dperson/samba:latest
    container_name: learningetl-nas
    environment:
      - TZ=Asia/Seoul
      - USER=learningetl;password
      - SHARE=learningetl;/share;yes;no;no;all;none
    volumes:
      - nas_data:/share
    ports:
      - "139:139"
      - "445:445"
    restart: unless-stopped
    networks:
      - learningetl_net

  # ========================================
  # 4. NAS Processor (Server)
  # ========================================
  processor:
    build:
      context: .
      dockerfile: Dockerfile.processor
    container_name: learningetl-processor
    environment:
      - NAS_MOUNT_POINT=/mnt/nas
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=learning
      - DB_USER=learning_user
      - DB_PASSWORD=secure_password
    volumes:
      - nas_data:/mnt/nas
      - ./learning_artifacts:/app/learning_artifacts
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      nas:
        condition: service_started
    restart: unless-stopped
    networks:
      - learningetl_net

  # ========================================
  # 5. NAS Agent (Client) - 노트북에서 실행
  # ========================================
  agent:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: learningetl-agent
    environment:
      - NAS_MOUNT_POINT=/mnt/nas
      - DOWNLOAD_DIR=/downloads
    volumes:
      - nas_data:/mnt/nas
      - ~/Downloads:/downloads  # 호스트 Downloads 폴더
      - ./logs:/app/logs
    depends_on:
      - nas
    restart: unless-stopped
    networks:
      - learningetl_net
    # 노트북에서만 실행 (프로파일 사용)
    profiles:
      - client

  # ========================================
  # 6. CLI Tools
  # ========================================
  cli:
    build:
      context: .
      dockerfile: Dockerfile.processor
    container_name: learningetl-cli
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=learning
      - DB_USER=learning_user
      - DB_PASSWORD=secure_password
    volumes:
      - ./learning_artifacts:/app/learning_artifacts
    depends_on:
      - postgres
    networks:
      - learningetl_net
    # 명령 실행 시만 사용
    profiles:
      - tools

# ========================================
# Networks
# ========================================
networks:
  learningetl_net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.8.0.0/24

# ========================================
# Volumes
# ========================================
volumes:
  postgres_data:
    driver: local
  nas_data:
    driver: local
```

---

## 🐳 Dockerfiles

### Dockerfile.processor (Server)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    cifs-utils \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# 프로젝트 파일
COPY . .

# 실행
CMD ["python", "server/nas_processor.py"]
```

### Dockerfile.agent (Client)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    cifs-utils \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements-client.txt .
RUN pip install --no-cache-dir -r requirements-client.txt

# 프로젝트 파일
COPY client/ ./client/
COPY config/ ./config/

# 실행
CMD ["python", "client/nas_agent.py"]
```

---

## 🚀 사용법

### 1. 라즈베리파이 (서버 스택)

```bash
# 전체 서버 스택 시작
docker-compose up -d wireguard postgres nas processor

# 확인
docker-compose ps

# 로그
docker-compose logs -f processor
```

### 2. 노트북 (클라이언트)

```bash
# 클라이언트만 시작
docker-compose --profile client up -d agent

# 확인
docker-compose ps

# 로그
docker-compose logs -f agent
```

### 3. CLI 사용

```bash
# 통계 확인
docker-compose --profile tools run --rm cli python cli.py stats

# AI Chat 목록
docker-compose --profile tools run --rm cli python cli.py list ai-chat

# 특정 대화 보기
docker-compose --profile tools run --rm cli python cli.py show ai-chat 1
```

---

## 🔧 환경별 실행

### Production (라즈베리파이)

```bash
# .env 파일
cat > .env << EOF
POSTGRES_PASSWORD=super_secure_password
WIREGUARD_SERVERURL=your-public-ip
EOF

# 서버 스택 시작
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Development (로컬)

```bash
# 전체 스택 로컬 테스트
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## 🌐 WireGuard 설정

### 1. WireGuard 컨테이너 시작
```bash
docker-compose up -d wireguard
```

### 2. 클라이언트 설정 파일 생성됨
```bash
# peer_notebook.conf
cat config/wireguard/peer_notebook/peer_notebook.conf

# QR 코드
cat config/wireguard/peer_notebook/peer_notebook.png
```

### 3. 노트북에서 연결
```bash
# macOS/Linux
sudo wg-quick up ./peer_notebook.conf

# Windows
# WireGuard 앱에서 설정 파일 import
```

### 4. 연결 확인
```bash
# 라즈베리파이 ping
ping 10.8.0.1

# NAS 접근 확인
ping 10.8.0.2
```

---

## 📊 모니터링

### Docker Compose 대시보드

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
```

```bash
# 모니터링 스택 시작
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Grafana 접속
open http://localhost:3000
```

---

## 🔒 보안

### 1. Secrets 관리

```yaml
# docker-compose.yml
secrets:
  db_password:
    file: ./secrets/db_password.txt
  wireguard_private_key:
    file: ./secrets/wg_private_key.txt

services:
  postgres:
    secrets:
      - db_password
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
```

### 2. 네트워크 격리

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 외부 접근 차단

services:
  postgres:
    networks:
      - backend  # 백엔드만 접근 가능
```

---

## 🎯 장점

### ✅ 완전 자동화
```bash
# 한 명령으로 전체 스택 시작
docker-compose up -d

# 한 명령으로 전체 스택 종료
docker-compose down
```

### ✅ 재현 가능
```
- 모든 설정이 코드로 관리
- Git으로 버전 관리
- 어디서든 동일한 환경 구축
```

### ✅ 확장 가능
```yaml
# 서버 복제 (수평 확장)
docker-compose up -d --scale processor=3

# 로드 밸런서 추가
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
```

### ✅ 격리
```
- 각 서비스가 독립적인 컨테이너
- 의존성 충돌 없음
- 서비스별 리소스 제한 가능
```

---

## 📝 실제 사용 시나리오

### 초기 설정 (1회만)

**라즈베리파이:**
```bash
# 1. 프로젝트 클론
git clone https://github.com/your-username/LearningETL.git
cd LearningETL

# 2. 환경 변수 설정
cp .env.example .env
nano .env

# 3. Docker Compose 시작
docker-compose up -d

# 완료! 🎉
```

**노트북:**
```bash
# 1. WireGuard 설정
sudo wg-quick up ./peer_notebook.conf

# 2. Docker Compose 시작
docker-compose --profile client up -d

# 완료! 🎉
```

### 일상 사용

```
1. Claude에서 코딩
   ↓
2. Extension으로 다운로드
   ~/Downloads/Claude-xxx.md
   ↓
3. Docker Agent 자동 감지
   ↓
4. NAS 업로드
   ↓
5. Docker Processor 자동 처리
   ↓
6. PostgreSQL 저장
   ↓
7. 완료!
```

### 조회

```bash
# CLI로 확인
docker-compose --profile tools run --rm cli python cli.py stats

# 또는 SSH 접속
ssh pi@raspberry-pi
docker exec -it learningetl-processor python cli.py stats
```

---

## 🚀 결론

### **100% 구현 가능!**

✅ **VPN**: WireGuard 컨테이너
✅ **NAS**: Samba 컨테이너
✅ **Server**: NAS Processor 컨테이너
✅ **Client**: NAS Agent 컨테이너
✅ **Database**: PostgreSQL 컨테이너
✅ **Monitoring**: Prometheus + Grafana

### 한 줄로 전체 스택 시작:
```bash
docker-compose up -d
```

**완벽!** 🎉
