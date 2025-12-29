# Learning Artifacts ETL Pipeline

모든 학습 활동(GitHub 커밋, AI 채팅, 백준 문제풀이)을 자동으로 수집하여 PostgreSQL DB에 저장하는 ETL 파이프라인입니다.

## 🎯 주요 기능

- **GitHub 커밋 수집**: REST API로 커밋 메타데이터 및 diff 수집
- **AI 채팅 수집**: Claude, ChatGPT, Gemini 마크다운 자동 파싱
- **백준 풀이 수집**: 백준허브 연동 레포에서 자동 푸시된 문제 풀이 수집
- **PostgreSQL 저장**: 모든 데이터를 구조화하여 DB 저장
- **2가지 실행 모드**: Standalone (단독) / Client-Server (분산)

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

## 🏗️ 실행 모드

### Mode 1: Standalone (단독 실행)

**한 대의 머신**에서 모든 작업 수행

```
┌────────────────────────────────┐
│  라즈베리파이 (또는 서버)       │
│                                 │
│  main.py (cron 매일 실행)      │
│  ├─ GitHub 커밋 수집           │
│  ├─ Baekjoon 풀이 수집         │
│  └─ AI Chat 수집 (선택)        │
│                                 │
│  PostgreSQL                     │
└────────────────────────────────┘
```

**적합한 경우:**
- 라즈베리파이에서 모든 작업 수행
- AI 채팅을 수동으로 복사
- 간단한 설정 원함

**시작하기:** [📖 Standalone 가이드](docs/standalone-guide.md)

---

### Mode 2: Client-Server (클라이언트-서버)

**노트북/데스크탑**과 **라즈베리파이**를 분리하여 자동화 극대화

```
┌──────────────────────┐          ┌──────────────────────┐
│  노트북/데스크탑      │          │  라즈베리파이 (서버)  │
│  (Client)            │          │  (Server)            │
│                      │          │                      │
│  Client Agent        │  HTTP    │  FastAPI Server      │
│  - Downloads 감시    │  ──────▶ │  - 파일 수신/파싱    │
│  - 파일 전송         │  POST    │  - DB 저장           │
│  - 로컬 큐잉         │          │                      │
│                      │          │  main.py (cron)      │
│                      │          │  - GitHub/Baekjoon   │
│                      │          │                      │
│                      │          │  PostgreSQL          │
└──────────────────────┘          └──────────────────────┘
```

**적합한 경우:**
- 노트북에서 AI 채팅 다운로드 자주 함
- 수동 파일 복사 귀찮음
- 자동화 극대화 원함
- 오프라인 대응 필요 (외부에서 작업 시)

**시작하기:** [📖 Client-Server 가이드](docs/client-server-guide.md)

---

## 🚀 빠른 시작

### 옵션 1: Standalone Mode

```bash
# 1. 클론
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 4. 실행
python main.py
```

### 옵션 2: Client-Server Mode

**Server (라즈베리파이):**
```bash
# 1. 클론
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 2. 의존성 설치
pip install -r requirements-server.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 4. FastAPI 서버 실행
python server/api.py

# 5. cron 설정 (GitHub/Baekjoon 수집)
crontab -e
# 0 6 * * * cd /path/to/LearningETL && python main.py
```

**Client (노트북/데스크탑):**
```bash
# 1. 클론
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 2. 의존성 설치
pip install -r requirements-client.txt

# 3. Client Agent 실행
python client/agent.py --server http://raspberrypi.local:8000
```

---

## 📁 프로젝트 구조

```
LearningETL/
├── main.py                     # Standalone Mode 진입점
│
├── server/
│   └── api.py                  # FastAPI 서버 (Client-Server Mode)
│
├── client/
│   └── agent.py                # Client Agent (Client-Server Mode)
│
├── config/
│   └── settings.py             # 환경 설정
│
├── export/                     # 데이터 수집
│   ├── github_export.py        # GitHub API
│   ├── baekjoon_export.py      # 백준허브 레포
│   └── ai_chat_export.py       # 파일 감시
│
├── parse/                      # 데이터 파싱
│   ├── github_parse.py
│   ├── baekjoon_parse.py
│   └── ai_chat_parse.py
│
├── collectors/                 # ETL 오케스트레이터
│   ├── github_collector.py     # Export → Parse → Save
│   ├── baekjoon_collector.py
│   └── ai_chat_collector.py
│
├── storage/                    # 데이터 저장
│   ├── base_saver.py
│   ├── github_saver.py
│   ├── baekjoon_saver.py
│   └── ai_chat_saver.py
│
├── docs/
│   ├── codebase-structure.md        # 코드베이스 구조
│   ├── standalone-guide.md          # Standalone 가이드
│   └── client-server-guide.md       # Client-Server 가이드
│
├── requirements.txt                 # Standalone 의존성
├── requirements-server.txt          # Server 의존성
└── requirements-client.txt          # Client 의존성
```

---

## 📊 데이터 소스

### 1️⃣ GitHub 커밋

- **방식**: GitHub REST API
- **수집 내용**: 커밋 메타데이터, Diff, 변경 파일 목록
- **실행**: `python main.py` (자동) 또는 `--date` 옵션

### 2️⃣ AI 채팅 (Claude, ChatGPT, Gemini)

- **방식**: 브라우저 확장 → 마크다운 내보내기
- **수집 내용**: 대화 제목, 메시지, 코드 블록, 날짜
- **실행**:
  - Standalone: `python main.py --ai-chat-scan`
  - Client-Server: Client Agent가 자동 감지/전송

### 3️⃣ 백준 문제풀이

- **방식**: 백준허브 연동 레포 (GitHub API)
- **수집 내용**: 문제 번호, 제목, 티어, 제출 코드, 태그
- **실행**: `python main.py` (자동)

---

## 💾 데이터베이스 스키마

### learning_artifacts (통합 메타데이터)

```sql
- id: 고유 ID
- artifact_type: github / ai_chat / baekjoon
- artifact_date: 학습 날짜
- file_path: JSON 파일 저장 경로
- created_at: 수집 시각
```

### 소스별 상세 테이블

- `github_commits`: SHA, repo, message, diff 등
- `ai_conversations`: provider, title, messages (JSONB) 등
- `baekjoon_solutions`: problem_number, tier, code 등

---

## 🔧 사용 예시

### Standalone Mode

```bash
# GitHub + Baekjoon 수집
python main.py

# AI 채팅 포함
python main.py --ai-chat-scan

# 특정 날짜
python main.py --date 2025-12-25

# 수동으로 AI 채팅 파일 지정
python main.py --ai-chat ~/Downloads/Claude-Export.md
```

### Client-Server Mode

```bash
# Server (라즈베리파이)
python server/api.py              # FastAPI 서버
python main.py                    # cron으로 GitHub/Baekjoon 수집

# Client (노트북)
python client/agent.py --server http://raspberrypi.local:8000

# AI 채팅 다운로드하면 자동 전송 → 파싱 → DB 저장
```

---

## 📖 상세 문서

- [📐 코드베이스 구조](docs/codebase-structure.md) - 클래스/함수 설명, 제어 흐름
- [🔧 Standalone 가이드](docs/standalone-guide.md) - 단독 실행 상세 가이드
- [🌐 Client-Server 가이드](docs/client-server-guide.md) - 분산 시스템 상세 가이드

---

## 🐛 트러블슈팅

### GitHub API Rate Limit

```bash
# Rate limit 확인
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

### AI 채팅 파일 감지 안 됨 (Standalone)

1. 파일명 확인: `Claude-`, `ChatGPT-`, `Gemini-`로 시작하는지
2. 확장자 확인: `.md` 파일인지
3. 다운로드 폴더 확인: `~/Downloads`가 맞는지

### Server 연결 실패 (Client-Server)

```bash
# Server 상태 확인
curl http://raspberrypi.local:8000/health

# IP 주소로 직접 시도
python client/agent.py --server http://192.168.1.100:8000
```

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
