# LearningETL 레포지토리 구조

**최종 정리일**: 2025-12-30
**핵심**: NAS 기반 아키텍처 설계 완료, HTTP 방식 아카이브, 코어 ETL 파이프라인 작동 중

---

## 📂 전체 디렉토리 구조

```
LearningETL/
├── 📁 archive/                      # 아카이브된 코드와 문서
│   └── http-architecture/           # HTTP 기반 Client-Server 아키텍처 (사용 안 함)
│       ├── server/                  # FastAPI 업로드 서버 (아카이브)
│       ├── client/                  # HTTP 클라이언트 에이전트 (아카이브)
│       ├── docs/                    # HTTP 방식 가이드 문서
│       ├── create-launchers.sh      # HTTP 기반 실행 파일 생성 스크립트
│       └── README.md                # 아카이브 이유 및 대체 방법
│
├── 📁 collectors/                   # ✅ 통합 수집 오케스트레이터 (핵심)
│   ├── __init__.py
│   ├── github_collector.py          # GitHub: Export → Parse → Storage
│   ├── baekjoon_collector.py        # Baekjoon: Export → Parse → Storage
│   └── ai_chat_collector.py         # AI Chat: Parse → Storage
│
├── 📁 config/                       # 설정 파일
│   └── config.py                    # 중앙 설정 관리
│
├── 📁 docker/                       # 🐳 Docker Compose 전체 스택 (미래 구현)
│   ├── docker-compose.yml           # (placeholder)
│   ├── Dockerfile.processor         # 서버 컨테이너 (NAS Processor)
│   ├── Dockerfile.agent             # 클라이언트 컨테이너 (NAS Agent)
│   └── README.md                    # Docker Compose 완전 설계서
│
├── 📁 docs/                         # 📚 문서
│   ├── README.md                    # 문서 인덱스
│   ├── ARCHITECTURE.md              # 시스템 아키텍처 개요
│   ├── standalone-guide.md          # ✅ 현재 사용: Standalone 모드 가이드
│   ├── NAS_ARCHITECTURE.md          # 🎯 향후 구현: NAS 기반 아키텍처 설계
│   ├── AI_CHAT_INTEGRATION.md       # AI Chat 통합 가이드
│   ├── AI_CHAT_STORAGE_DETAIL.md    # AI Chat 저장 상세 설명
│   ├── DATABASE_GUIDE.md            # 데이터베이스 설정 가이드
│   ├── MIGRATION_GUIDE.md           # 기존 DB 마이그레이션 가이드
│   ├── RASPBERRY_PI_TEST_GUIDE.md   # 라즈베리파이 전체 테스트 가이드
│   ├── codebase-structure.md        # 코드베이스 구조 설명
│   ├── systemd-examples/            # systemd 서비스 템플릿
│   └── cron-examples/               # cron 자동화 예시
│
├── 📁 export/                       # ✅ 데이터 수집 모듈 (핵심)
│   ├── __init__.py
│   ├── github_export.py             # GitHub API로 커밋 수집
│   ├── baekjoon_export.py           # Baekjoon 백준허브 레포 커밋 수집
│   └── ai_chat_export.py            # AI Chat 파일 감시 (Downloads 폴더)
│
├── 📁 learning_artifacts/           # 📦 저장된 학습 아티팩트 (JSON 파일)
│   └── YYYY/MM/DD/                  # 날짜별 폴더 구조
│       ├── github/                  # GitHub 커밋 데이터
│       ├── baekjoon/                # Baekjoon 풀이 데이터
│       └── ai_chat_claude/          # AI Chat 대화 데이터
│
├── 📁 logs/                         # 📝 로그 파일
│   ├── .gitkeep
│   ├── main.log
│   ├── github_collector.log
│   ├── baekjoon_collector.log
│   └── ai_chat_collector.log
│
├── 📁 migration/                    # 🔄 첫 마이그레이션 전용
│   ├── __init__.py
│   ├── claude_collector.py          # Claude ZIP → 마크다운 변환 + 저장
│   └── claude_parse.py              # Claude ZIP 파서 (어댑터)
│
├── 📁 parse/                        # ✅ 데이터 파싱 모듈 (핵심)
│   ├── __init__.py
│   ├── github_parse.py              # GitHub 커밋 구조화, Co-Author 추출
│   ├── baekjoon_parse.py            # Baekjoon README.md 파싱
│   └── ai_chat_parse.py             # AI Chat 마크다운 파싱
│
├── 📁 scripts/                      # 🔧 운영 스크립트
│   ├── create-schema.sql            # PostgreSQL 스키마 생성
│   ├── clean-migrate-db.sql         # 기존 데이터 정리 및 마이그레이션
│   ├── setup-database.sh            # DB 초기 설정 스크립트
│   ├── install.sh                   # 원스텝 설치 스크립트
│   ├── backup.sh                    # DB 백업 스크립트
│   ├── healthcheck.py               # 헬스 체크 및 알림
│   └── test-installation.sh         # 설치 테스트
│
├── 📁 storage/                      # ✅ 데이터 저장 모듈 (핵심)
│   ├── __init__.py
│   ├── base_saver.py                # PostgreSQL 베이스 클래스
│   ├── artifact_saver.py            # 통합 아티팩트 저장
│   ├── github_saver.py              # GitHub 커밋 → DB
│   ├── baekjoon_saver.py            # Baekjoon 풀이 → DB
│   └── ai_chat_saver.py             # AI Chat → DB (마크다운 + ZIP)
│
├── 📁 temp/                         # 임시 파일
│   └── downloads/                   # 테스트용 다운로드 파일
│
├── 📁 tests/                        # ✅ 테스트 코드
│   ├── __init__.py
│   ├── README.md                    # 테스트 가이드
│   ├── conftest.py                  # pytest 설정
│   ├── test_github_export.py        # GitHub Export 테스트
│   ├── test_github_parse.py         # GitHub Parse 테스트
│   ├── test_baekjoon_export.py      # Baekjoon Export 테스트
│   ├── test_baekjoon_parse.py       # Baekjoon Parse 테스트
│   ├── test_ai_chat_parse.py        # AI Chat Parse 테스트
│   ├── test_github_collector.py     # GitHub Collector 통합 테스트
│   ├── test_storage.py              # Storage 모듈 테스트
│   └── fixtures/                    # 테스트 픽스처 데이터
│
├── 📄 main.py                       # ✅ 메인 실행 파일 (Standalone 모드)
├── 📄 cli.py                        # ✅ CLI 쿼리 도구
├── 📄 .env                          # 환경 변수 (gitignore)
├── 📄 .env.example                  # 환경 변수 예시
├── 📄 requirements.txt              # Python 의존성
├── 📄 requirements-server.txt       # (아카이브됨, 사용 안 함)
├── 📄 requirements-client.txt       # (아카이브됨, 사용 안 함)
├── 📄 .gitignore                    # Git 제외 파일
├── 📄 README.md                     # 프로젝트 README
└── 📄 REPOSITORY_STRUCTURE.md       # 🎯 이 문서 (레포 구조 가이드)
```

---

## 🎯 핵심 파일 기능 설명

### ✅ 현재 작동 중인 코드

#### 1. **main.py** - 메인 실행 파일 (Standalone 모드)
```bash
# GitHub + Baekjoon 수집
python main.py

# AI Chat 파일 수집
python main.py --ai-chat ~/Downloads/Claude-Export.md

# AI Chat 다운로드 폴더 스캔
python main.py --ai-chat-scan
```
**기능**: 모든 ETL 작업 오케스트레이션, 날짜별 수집, 로깅

#### 2. **cli.py** - CLI 쿼리 도구
```bash
# 통계 확인
python cli.py stats

# AI Chat 목록
python cli.py list ai-chat

# 특정 대화 보기
python cli.py show ai-chat 1
```
**기능**: PostgreSQL 데이터 조회, 통계, 검색

#### 3. **collectors/** - 통합 수집 오케스트레이터
- `github_collector.py`: GitHub 커밋 수집 (Export → Parse → Storage)
- `baekjoon_collector.py`: Baekjoon 풀이 수집 (백준허브 레포 기반)
- `ai_chat_collector.py`: AI Chat 대화 수집 (마크다운 파일 기반)

**특징**: Co-Author 파싱 (Claude 커밋 추적), 재시도 로직, 에러 핸들링

#### 4. **export/** - 데이터 수집
- `github_export.py`: GitHub API로 커밋 가져오기 (Co-Author 필터링 포함)
- `baekjoon_export.py`: 백준허브 연동 레포에서 커밋 가져오기
- `ai_chat_export.py`: Downloads 폴더 파일 감시 (watchdog)

#### 5. **parse/** - 데이터 파싱
- `github_parse.py`: 커밋 구조화, Co-Authored-By 추출
- `baekjoon_parse.py`: README.md에서 메타데이터 추출 (티어, 태그, 성능)
- `ai_chat_parse.py`: 마크다운에서 대화 파싱, 코드 블록 추출

#### 6. **storage/** - 데이터 저장
- `base_saver.py`: PostgreSQL 연결 베이스
- `artifact_saver.py`: learning_artifacts 테이블 저장
- `github_saver.py`: github_commits 테이블 저장
- `baekjoon_saver.py`: baekjoon_solutions 테이블 저장
- `ai_chat_saver.py`: ai_chat_conversations 테이블 저장

**특징**: JSONB 활용, 파일 저장 (learning_artifacts/), 트랜잭션 관리

#### 7. **scripts/** - 운영 도구
- `create-schema.sql`: PostgreSQL 스키마 생성 (정확한 컬럼 구조)
- `clean-migrate-db.sql`: 기존 claude 데이터 삭제 및 마이그레이션
- `setup-database.sh`: DB 초기 설정
- `install.sh`: 원스텝 설치
- `backup.sh`: DB 백업 (pg_dump)
- `healthcheck.py`: 헬스 체크 및 Slack/Email 알림

---

## 🗄️ 데이터베이스 스키마

### PostgreSQL Schemas

```
learning (스키마)
├── learning_artifacts          # 모든 학습 활동 메타데이터
├── github_commits              # GitHub 커밋 상세
├── baekjoon_solutions          # 백준 문제풀이
├── ai_chat_conversations       # AI Chat (Claude/ChatGPT/Gemini)
└── claude_conversations        # Claude ZIP (레거시, 마이그레이션 완료 후 삭제 예정)

blog (스키마) - 기존 블로그 데이터
├── posts
└── projects
```

### 주요 테이블 구조

#### learning_artifacts (통합 메타데이터)
```sql
- id: SERIAL PRIMARY KEY
- artifact_date: DATE              # 활동 날짜
- source_type: VARCHAR(100)        # 'github', 'ai_chat_claude', 'baekjoon'
- title: TEXT                      # 제목
- summary: TEXT                    # 요약
- tags: TEXT[]                     # 태그 배열
- storage_path: TEXT               # JSON 파일 경로
- metadata: JSONB                  # 추가 메타데이터
- created_at: TIMESTAMP
```

#### ai_chat_conversations (AI 채팅)
```sql
- id: SERIAL PRIMARY KEY
- artifact_id: INTEGER (FK)
- provider: VARCHAR(50)            # 'claude', 'chatgpt', 'gemini'
- title: TEXT
- link: TEXT                       # 대화 URL
- user_messages: INTEGER           # 사용자 메시지 수
- assistant_messages: INTEGER      # AI 메시지 수
- has_code: BOOLEAN                # 코드 포함 여부
- conversation_path: TEXT          # JSON 파일 경로
- code_languages: TEXT[]           # 사용된 언어들
- code_blocks_count: INTEGER       # 코드 블록 수
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

---

## 🏗️ 아키텍처 구분

### ✅ 현재 사용 중: **Standalone Mode**

**위치**: 프로젝트 루트 (main.py)
**문서**: docs/standalone-guide.md

**특징**:
- 한 대의 머신 (라즈베리파이)에서 모든 작업 수행
- GitHub + Baekjoon 자동 수집 (cron)
- AI Chat 수동 복사 or Downloads 폴더 스캔
- 간단한 설정, 안정적인 운영

**실행**:
```bash
# 수동 실행
python main.py

# cron 자동화
0 6 * * * cd /home/jcw/LearningETL && python main.py >> logs/cron.log 2>&1
```

---

### 🎯 향후 구현: **NAS-Based Architecture**

**위치**: docs/NAS_ARCHITECTURE.md, docker/
**상태**: 설계 완료, 구현 예정

**특징**:
- WireGuard VPN으로 노트북-라즈베리파이 연결
- NAS 파일 공유로 자동 전송 (SMB/CIFS)
- Client (노트북): Downloads 감시 → NAS inbox/ 복사
- Server (라즈베리파이): NAS inbox/ 감시 → 파싱 → DB 저장
- Docker Compose로 전체 스택 관리 (WireGuard, PostgreSQL, NAS, Processor, Agent)

**장점**:
- HTTP 서버 불필요 (FastAPI 제거)
- 네트워크 에러 처리 간단
- 기존 인프라 활용 (WireGuard + NAS)
- 파일 영구 보존 (NAS 스토리지)

**미래 실행**:
```bash
# 라즈베리파이 (서버 스택)
docker-compose up -d wireguard postgres nas processor

# 노트북 (클라이언트)
docker-compose --profile client up -d agent
```

---

### 📦 아카이브됨: **HTTP-Based Client-Server**

**위치**: archive/http-architecture/
**상태**: 사용 안 함, 참고용 보관

**이유**:
- FastAPI 서버 필요 (복잡도 증가)
- 네트워크 에러 처리 복잡
- MD5 계산 및 검증 오버헤드
- NAS 파일 복사 방식이 훨씬 간단

**대체**: NAS 기반 아키텍처로 변경

---

## 🔄 데이터 흐름

### GitHub 수집 흐름
```
GitHub API
    ↓
export/github_export.py (커밋 수집, Co-Author 필터링)
    ↓
parse/github_parse.py (구조화, Co-Authored-By 추출)
    ↓
storage/github_saver.py (DB 저장)
    ↓
PostgreSQL (learning.github_commits)
```

### AI Chat 수집 흐름
```
~/Downloads/Claude-Export.md
    ↓
export/ai_chat_export.py (파일 감시, watchdog)
    ↓
parse/ai_chat_parse.py (마크다운 파싱, 코드 추출)
    ↓
storage/ai_chat_saver.py (DB + JSON 파일 저장)
    ↓
PostgreSQL (learning.ai_chat_conversations)
learning_artifacts/YYYY/MM/DD/ai_chat_claude/xxx.json
```

### Baekjoon 수집 흐름
```
Baekjoon Hub Chrome Extension
    ↓
GitHub Repo (자동 푸시)
    ↓
export/baekjoon_export.py (GitHub API로 커밋 읽기)
    ↓
parse/baekjoon_parse.py (README.md 파싱)
    ↓
storage/baekjoon_saver.py (DB 저장)
    ↓
PostgreSQL (learning.baekjoon_solutions)
```

---

## 🚀 빠른 시작

### 1. 설치
```bash
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
nano .env
```

### 2. 데이터베이스 설정
```bash
# 스키마 생성
psql -h localhost -U postgres -d my_blog -f scripts/create-schema.sql

# 또는 자동 설정
bash scripts/setup-database.sh
```

### 3. 실행
```bash
# 수동 실행 (테스트)
python main.py

# AI Chat 수집
python main.py --ai-chat-scan

# 통계 확인
python cli.py stats
```

### 4. 자동화 (Cron)
```bash
crontab -e

# 매일 오전 6시 실행
0 6 * * * cd /home/jcw/LearningETL && python main.py >> logs/cron.log 2>&1
```

---

## 📊 주요 설계 결정

### 1. **Baekjoon: Selenium → 백준허브 연동 레포**
- ❌ Selenium 크롤링 (불안정, 쿠키 관리 필요)
- ✅ 백준허브 Chrome Extension → GitHub 자동 푸시 → GitHub API 읽기

### 2. **AI Chat: ZIP → 마크다운**
- 일상 사용: 브라우저 Extension → 마크다운 다운로드
- 첫 마이그레이션: claude.ai ZIP → 마크다운 변환 (migration/ 어댑터)

### 3. **Client-Server: HTTP → NAS 파일 공유**
- ❌ HTTP 업로드 (FastAPI, MD5 검증, 복잡한 에러 처리)
- ✅ NAS 파일 복사 (WireGuard VPN + SMB, 간단하고 안정적)

### 4. **Co-Author 추출**
- GitHub API `author` 필터 제거 → 모든 커밋 가져오기
- Co-Authored-By 파싱으로 Claude 커밋 추적

### 5. **PostgreSQL JSONB 활용**
- NoSQL 불필요, JSONB로 유연한 메타데이터 저장
- GIN 인덱스로 빠른 검색

---

## 🔍 문서 가이드

| 문서 | 용도 |
|------|------|
| **README.md** | 프로젝트 개요 및 빠른 시작 |
| **REPOSITORY_STRUCTURE.md** | 이 문서 (레포 구조 전체 파악) |
| **docs/standalone-guide.md** | ✅ 현재 사용: Standalone 모드 가이드 |
| **docs/NAS_ARCHITECTURE.md** | 🎯 향후 구현: NAS 기반 설계 |
| **docs/ARCHITECTURE.md** | 시스템 아키텍처 개요 |
| **docs/DATABASE_GUIDE.md** | 데이터베이스 설정 가이드 |
| **docs/MIGRATION_GUIDE.md** | 기존 DB 마이그레이션 |
| **docs/RASPBERRY_PI_TEST_GUIDE.md** | 라즈베리파이 전체 테스트 |
| **docker/README.md** | Docker Compose 전체 설계 |
| **archive/http-architecture/README.md** | HTTP 방식 아카이브 이유 |

---

## 🎯 다음 단계

### 단기 (현재 작동 중)
- [x] GitHub 커밋 수집 (Co-Author 포함)
- [x] Baekjoon 풀이 수집 (백준허브 레포)
- [x] AI Chat 수집 (마크다운)
- [x] PostgreSQL 저장 (JSONB)
- [x] CLI 쿼리 도구
- [x] Cron 자동화
- [x] 테스트 코드 작성

### 중기 (향후 구현)
- [ ] NAS 기반 아키텍처 구현
  - [ ] nas_agent.py (클라이언트: Downloads → NAS)
  - [ ] nas_processor.py (서버: NAS → 파싱 → DB)
- [ ] Docker Compose 구현
  - [ ] WireGuard 컨테이너
  - [ ] PostgreSQL 컨테이너
  - [ ] NAS (Samba) 컨테이너
  - [ ] Processor/Agent 컨테이너

### 장기 (확장)
- [ ] Grafana 대시보드 (학습 통계)
- [ ] Notion 통합
- [ ] Obsidian Vault 통합
- [ ] 웹 UI (검색, 필터링)

---

## 📝 변경 이력

- **2025-12-30**: 레포 구조 정리 완료
  - Docker 파일 docker/ 폴더로 이동
  - HTTP 아키텍처 archive/http-architecture/ 아카이브
  - 빈 client/, server/ 폴더 제거
  - NAS 기반 아키텍처 설계 완료 (미구현)
  - 최종 레포 구조 문서 생성 (이 문서)

- **2025-12-29**: 코어 기능 완료
  - Co-Author 파싱 추가 (Claude 커밋 추적)
  - 기존 DB 마이그레이션 스크립트
  - 라즈베리파이 테스트 가이드
  - CLI 쿼리 도구
  - 운영 스크립트 (backup, healthcheck)

- **2025-12-28**: 초기 구현
  - GitHub/Baekjoon/AI Chat 수집 파이프라인
  - PostgreSQL 스키마 설계
  - 테스트 코드 작성
  - HTTP Client-Server 아키텍처 (현재 아카이브됨)

---

**이 문서는 프로젝트의 최종 정리 상태를 반영합니다. 향후 NAS 아키텍처 구현 시 업데이트 예정.**
