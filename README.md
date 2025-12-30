# Learning Artifacts ETL Pipeline

모든 학습 활동(GitHub 커밋, AI 채팅, 백준 문제풀이)을 자동으로 수집하여 PostgreSQL DB에 저장하는 ETL 파이프라인입니다.

## 🎯 주요 기능

- **GitHub 커밋 수집**: REST API로 커밋 메타데이터 및 diff 수집 (Co-Author 추적 포함)
- **AI 채팅 수집**: Claude, ChatGPT, Gemini 마크다운 자동 파싱
- **백준 풀이 수집**: 백준허브 연동 레포에서 자동 푸시된 문제 풀이 수집
- **PostgreSQL 저장**: 모든 데이터를 구조화하여 DB 저장 (JSONB 활용)

---

## 🏗️ 현재 상태

### ✅ **사용 중: Standalone Mode**

한 대의 머신(라즈베리파이)에서 모든 ETL 작업 수행

```
┌────────────────────────────────┐
│  라즈베리파이                   │
│                                 │
│  main.py (cron 매일 실행)      │
│  ├─ GitHub 커밋 수집           │
│  ├─ Baekjoon 풀이 수집         │
│  └─ AI Chat 수집               │
│                                 │
│  PostgreSQL (learning 스키마)   │
└────────────────────────────────┘
```

**시작하기:** [📖 Standalone 가이드](docs/standalone-guide.md)

---

### 🎯 **설계 완료: NAS-Based Architecture (향후 구현)**

WireGuard VPN + NAS 파일 공유 기반 자동화

```
노트북 (Downloads)  →  NAS (inbox/)  →  라즈베리파이 (파싱/DB)
```

**상세 설계:** [📖 NAS 아키텍처](docs/NAS_ARCHITECTURE.md)

---

### 📦 **아카이브됨: HTTP Client-Server**

FastAPI 기반 HTTP 업로드 방식 (복잡도 문제로 NAS 방식으로 변경)

**위치:** `archive/client-server-architecture/`

---

## 🚀 빠른 시작

```bash
# 1. 클론
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
nano .env  # GITHUB_TOKEN, DB 정보 입력

# 4. DB 스키마 생성
psql -h localhost -U postgres -d my_blog -f scripts/create-schema.sql

# 5. 실행
python main.py                    # GitHub + Baekjoon 수집
python main.py --ai-chat-scan     # AI Chat 포함

# 6. DB 조회
python -m cli stats               # 통계
python -m cli list ai-chat        # AI Chat 목록
```

---

## 📁 프로젝트 구조

```
LearningETL/
├── main.py                     # ✅ 메인 실행 파일
├── cli/                        # ✅ CLI 쿼리 도구
│
├── collectors/                 # ETL 오케스트레이터
│   ├── github_collector.py     # Export → Parse → Save
│   ├── baekjoon_collector.py
│   └── ai_chat_collector.py
│
├── export/                     # 데이터 수집
│   ├── github_export.py        # GitHub API (Co-Author 필터링)
│   ├── baekjoon_export.py      # 백준허브 레포
│   └── ai_chat_export.py       # 파일 감시 (watchdog)
│
├── parse/                      # 데이터 파싱
│   ├── github_parse.py         # Co-Authored-By 추출
│   ├── baekjoon_parse.py       # README.md 파싱
│   └── ai_chat_parse.py        # 마크다운 파싱
│
├── storage/                    # 데이터 저장
│   ├── artifact_saver.py       # learning_artifacts 테이블
│   ├── github_saver.py         # github_commits 테이블
│   ├── baekjoon_saver.py       # baekjoon_solutions 테이블
│   └── ai_chat_saver.py        # ai_chat_conversations 테이블
│
├── scripts/                    # 운영 스크립트
│   ├── create-schema.sql       # DB 스키마 생성
│   ├── backup.sh               # DB 백업
│   └── healthcheck.py          # 헬스 체크
│
├── docs/                       # 문서
│   ├── standalone-guide.md     # ✅ 현재 사용법
│   ├── NAS_ARCHITECTURE.md     # 🎯 향후 설계
│   └── DATABASE_GUIDE.md       # DB 설정
│
├── docker/                     # 🐳 Docker Compose (미래 구현)
└── archive/                    # 📦 아카이브
    └── client-server-architecture/  # HTTP 방식 (사용 안 함)
```

---

## 💾 데이터베이스 스키마

### learning 스키마

```sql
learning.learning_artifacts          -- 모든 학습 활동 메타데이터
learning.github_commits              -- GitHub 커밋 상세
learning.baekjoon_solutions          -- 백준 문제풀이
learning.ai_chat_conversations       -- AI Chat (Claude/ChatGPT/Gemini)
```

**상세:** [📖 DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md)

---

## 🔧 사용 예시

### 기본 사용

```bash
# GitHub + Baekjoon 수집
python main.py

# AI Chat 포함 (Downloads 폴더 스캔)
python main.py --ai-chat-scan

# 특정 날짜
python main.py --date 2025-12-25

# 특정 AI Chat 파일 지정
python main.py --ai-chat ~/Downloads/Claude-Export.md
```

### CLI 조회

```bash
# 통계
python -m cli stats

# AI Chat 목록
python -m cli list ai-chat

# 특정 대화 보기
python -m cli show ai-chat 1

# GitHub 커밋 목록
python -m cli list github
```

### 자동화 설정

#### 1. 실시간 파일 감지 (Daemon)

AI 채팅 파일 자동 수집 (파일 감지 즉시 처리)

```bash
# 설치
bash scripts/install-daemon.sh

# 시작
sudo systemctl start learningetl

# 상태 확인
sudo systemctl status learningetl

# 로그 확인
tail -f ~/LearningETL/logs/daemon.log
```

#### 2. 매일 자정 전체 스캔

**방법 A: Cron (간단)**

```bash
# 설치
bash scripts/setup-daily-cron.sh

# 확인
crontab -l

# 로그 확인
tail -f ~/LearningETL/logs/daily-scan.log
```

**장점**: 간단, 익숙함
**단점**: 시스템 부팅 시 놓친 작업 미실행, 로그 관리 수동, 실행 실패 시 알림 없음

---

**방법 B: systemd timer (체계적 추천 ⭐)**

```bash
# 설치
bash scripts/setup-daily-timer.sh

# 상태 확인
systemctl list-timers learningetl-daily.timer

# 로그 확인
tail -f ~/LearningETL/logs/daily-scan.log
```

**장점**:
- ✅ **Persistent=true**: 시스템 재부팅 시 놓친 작업 자동 실행
- ✅ **journalctl 통합**: `journalctl -u learningetl-daily.service` 로그 관리
- ✅ **실행 상태 추적**: `systemctl status` 실패 여부 확인
- ✅ **의존성 관리**: `After=postgresql.service` DB 준비 후 실행
- ✅ **타이머 상태 확인**: 다음 실행 시각 확인 가능

**비교**:
| 기능 | Cron | systemd timer |
|------|------|---------------|
| 놓친 작업 실행 | ❌ | ✅ Persistent |
| 로그 관리 | 수동 | ✅ journalctl |
| 실패 알림 | ❌ | ✅ systemctl status |
| 서비스 의존성 | ❌ | ✅ After= |
| 다음 실행 확인 | ❌ | ✅ list-timers |

---

## 📋 전제조건

- Python 3.8+
- PostgreSQL 12+
- GitHub Personal Access Token
- **백준허브 연동 레포** (선택) - [BaekjoonHub](https://github.com/BaekjoonHub/BaekjoonHub) 크롬 확장
- **AI 채팅 브라우저 확장** (선택):
  - [Claude Exporter](https://chromewebstore.google.com/detail/claude-exporter/elhmfakncmnghlnabnolalcjkdpfjnin)
  - [ChatGPT Exporter](https://chromewebstore.google.com/detail/chatgpt-exporter/pldlpacbeonbjfhlongcdflcgfcnglkl)
  - [Gemini Chat Exporter](https://chromewebstore.google.com/detail/gemini-chat-exporter/bhmoomcflhcfhingnjjieheeadmdefkc)

---

## 📊 주요 설계 결정

### 1. Baekjoon: Selenium → 백준허브 연동 레포
- ❌ Selenium 크롤링 (불안정, 쿠키 관리)
- ✅ 백준허브 Chrome Extension → GitHub 자동 푸시 → GitHub API

### 2. Co-Author 추출
- GitHub API `author` 필터 제거 → 모든 커밋 가져오기
- `Co-Authored-By` 파싱으로 Claude 커밋 추적

### 3. PostgreSQL JSONB 활용
- NoSQL 불필요, JSONB로 유연한 메타데이터 저장
- GIN 인덱스로 빠른 검색

### 4. Client-Server → NAS 기반
- ❌ HTTP 업로드 (FastAPI, MD5 검증, 복잡한 에러 처리)
- ✅ NAS 파일 복사 (WireGuard VPN + SMB, 간단하고 안정적)

---

## 🐛 트러블슈팅

### GitHub API Rate Limit

```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

### AI 채팅 파일 감지 안 됨

1. 파일명 확인: `Claude-`, `ChatGPT-`, `Gemini-`로 시작하는지
2. 확장자 확인: `.md` 파일인지
3. 다운로드 폴더 확인: `~/Downloads` 또는 설정한 경로

### DB 연결 실패

```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# DB 접속 테스트
psql -h localhost -U postgres -d my_blog
```

---

## 📖 문서

- [📖 Standalone 가이드](docs/standalone-guide.md) - 현재 사용 중인 모드
- [📖 NAS 아키텍처](docs/NAS_ARCHITECTURE.md) - 향후 구현 설계
- [📖 데이터베이스 가이드](docs/DATABASE_GUIDE.md) - DB 설정 및 스키마

---

## 🤝 기여

Issues와 Pull Requests를 환영합니다!

## 📄 라이선스

MIT License

## 🔗 관련 프로젝트

- [BaekjoonHub](https://github.com/BaekjoonHub/BaekjoonHub) - 백준 문제 자동 커밋
- [Claude Exporter](https://github.com/jasonkneen/claude-exporter) - Claude 대화 내보내기
- [ChatGPT Exporter](https://github.com/pionxzh/chatgpt-exporter) - ChatGPT 대화 내보내기
- [Gemini Chat Exporter](https://github.com/jiajunhang/gemini-chat-exporter) - Gemini 대화 내보내기
