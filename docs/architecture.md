# LearningETL 아키텍처 문서

## 📚 코드베이스 구조

### 1️⃣ 클래스별 기능 요약

#### 📁 main.py
| 클래스/함수 | 역할 |
|------------|------|
| `LearningETL.__init__()` | 4개 Collector 초기화 (GitHub, ClaudeMigration, Baekjoon, AIChat) |
| `LearningETL.run()` | 전체 ETL 파이프라인 실행 (각 Collector 순차 호출) |
| `main()` | CLI 인자 파싱 (`--claude-zip`, `--ai-chat`, `--ai-chat-scan`, `--date`) |

---

#### 📁 collectors/ (수집 오케스트레이터)
각 Collector는 **Exporter → Parser → Saver** 3단계를 오케스트레이션

| 클래스 | 역할 | 주요 메서드 |
|-------|------|-----------|
| `GitHubCollector` | GitHub 커밋 수집 통합 | `collect(target_date)` → Exporter/Parser/Saver 순차 호출 |
| `BaekjoonCollector` | 백준 풀이 수집 통합 | `collect(target_date)` → Exporter/Parser/Saver 순차 호출 |
| `AIChatCollector` | AI 채팅 마크다운 수집 | `collect_from_files()`, `collect_from_downloads()`, `start_watcher()` |
| `ClaudeMigrationCollector` | Claude ZIP 1회 마이그레이션 | `collect(zip_path, target_date, all_dates)` |

---

#### 📁 export/ (외부 데이터 수집)
| 클래스 | 역할 | 주요 메서드 |
|-------|------|-----------|
| `GitHubExporter` | GitHub REST API 호출 | `export_today()`: 당일 커밋 수집<br>`get_user_repos()`: 사용자 레포 목록<br>`get_commits_for_repo()`: 레포별 커밋 조회 |
| `BaekjoonExporter` | 백준허브 연동 레포에서 문제 수집 | `export_today(target_date)`: 당일 푸시된 백준 문제 폴더 검색 |
| `AIExportWatcher` | 다운로드 폴더 AI 채팅 파일 감시 | `scan_existing()`: 기존 파일 스캔<br>`start(callback)`: 실시간 감시 시작 |

---

#### 📁 parse/ (데이터 파싱 & 구조화)
| 클래스 | 역할 | 주요 메서드 |
|-------|------|-----------|
| `GitHubParser` | 커밋 데이터 파싱 | `parse_commits(commits)`: List[Dict] → List[CommitData]<br>`parse_file_change()`: diff 파싱 |
| `BaekjoonParser` | 백준 README/코드 파싱 | `parse_problems()`: 문제 메타데이터 추출<br>`parse_readme()`: README.md 파싱 |
| `AIMarkdownParser` | AI 채팅 마크다운 파싱 | `parse_file()`: Claude/ChatGPT/Gemini 형식 감지<br>`parse_claude()`, `parse_chatgpt()`, `parse_gemini()` |

**Dataclass 구조:**
```python
@dataclass
class FileChange:      # GitHub 파일 변경 정보
    filename, status, additions, deletions, patch, content, language

@dataclass
class CommitData:      # GitHub 커밋
    repo, sha, message, date, url, files: List[FileChange], stats

@dataclass
class BaekjoonProblemData:  # 백준 문제
    problem_number, title, tier, category, tags, language, code, ...

@dataclass
class ConversationData:     # AI 채팅
    provider, title, date, messages: List[Message], ...
```

---

#### 📁 storage/ (DB & 파일 저장)
| 클래스 | 역할 | 주요 메서드 |
|-------|------|-----------|
| `BaseSaver` | 공통 저장 로직 (부모 클래스) | `save_artifact()`: learning_artifacts 테이블 삽입<br>`_save_file()`: JSON 파일 저장<br>`_get_db_connection()`: PostgreSQL 연결 |
| `GitHubSaver` | GitHub 커밋 DB 저장 | `save_all(commits, target_date)`<br>`save_commit()`: github_commits 테이블 삽입 |
| `BaekjoonSaver` | 백준 풀이 DB 저장 | `save_all(problems, target_date)`<br>`save_problem()`: baekjoon_solutions 테이블 삽입 |
| `AIChatSaver` | AI 채팅 DB 저장 | `save_all(conversations, target_date)`<br>`save_conversation()`: ai_conversations 테이블 삽입 |
| `ArtifactSaver` | 제네릭 아티팩트 저장 | `save()`: artifact_type 자동 감지 후 저장 |

---

#### 📁 config/
| 모듈 | 역할 |
|-----|------|
| `settings.py` | 환경변수 로드 (.env), DB 설정, 로그 파일 경로 관리 |

---

### 2️⃣ main.py 실행 시 제어 흐름

```
┌──────────────────────────────────────────────────────────────┐
│                      python main.py                           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  main() 함수   │
              │  - argparse    │
              └────────┬───────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │  LearningETL.__init__() │
         │  ┌───────────────────┐  │
         │  │ GitHubCollector   │  │ ← Exporter/Parser/Saver 초기화
         │  │ ClaudeMigration   │  │
         │  │ BaekjoonCollector │  │
         │  │ AIChatCollector   │  │
         │  └───────────────────┘  │
         └─────────┬───────────────┘
                   │
                   ▼
       ┌───────────────────────────┐
       │  LearningETL.run()        │
       │  target_date = 오늘       │
       └───────┬───────────────────┘
               │
               │ ┌──────── 순차 실행 ────────┐
               │ │                            │
               ▼ ▼                            │
    ┏━━━━━━━━━━━━━━━━━━━━━━━━┓              │
    ┃  1. GitHub 수집         ┃              │
    ┗━━━━━━━━━┳━━━━━━━━━━━━━┛              │
              ▼                               │
     ┌──────────────────────┐                │
     │ GitHubCollector.     │                │
     │   collect(date)      │                │
     └──────┬───────────────┘                │
            │                                 │
            ├─▶ [1/3] GitHubExporter         │
            │         .export_today()         │
            │    ┌─────────────────┐          │
            │    │ GitHub REST API │          │
            │    │ - /user/repos   │          │
            │    │ - /commits      │          │
            │    │ - /commits/{sha}│          │
            │    └─────────────────┘          │
            │         ↓                        │
            │    [ List[Dict] 커밋 ]          │
            │                                  │
            ├─▶ [2/3] GitHubParser            │
            │         .parse_commits()         │
            │    ┌──────────────────┐          │
            │    │ Dict → CommitData│          │
            │    │ files → FileChange│         │
            │    └──────────────────┘          │
            │         ↓                        │
            │    [ List[CommitData] ]          │
            │                                  │
            └─▶ [3/3] GitHubSaver              │
                    .save_all()                │
               ┌─────────────────────┐         │
               │ BaseSaver 상속      │         │
               │ 1. JSON 파일 저장   │         │
               │ 2. learning_        │         │
               │    artifacts 삽입   │         │
               │ 3. github_commits   │         │
               │    삽입 (ON CONFLICT)         │
               └─────────────────────┘         │
                    ↓                          │
               [ artifact_ids ]                │
                                               │
    ┏━━━━━━━━━━━━━━━━━━━━━━━━┓              │
    ┃  2. Claude Migration    ┃              │
    ┃     (ZIP 파일 있으면)   ┃              │
    ┗━━━━━━━━━┳━━━━━━━━━━━━━┛              │
              ▼                               │
       claude_zip_path가 None이면 SKIP       │
                                               │
    ┏━━━━━━━━━━━━━━━━━━━━━━━━┓              │
    ┃  3. AI Chat 수집        ┃              │
    ┗━━━━━━━━━┳━━━━━━━━━━━━━┛              │
              ▼                               │
     ┌──────────────────────┐                │
     │ AIChatCollector.     │                │
     │   collect_from_*()   │                │
     └──────┬───────────────┘                │
            │                                 │
            ├─▶ AIExportWatcher               │
            │    .scan_existing()             │
            │    ┌─────────────────┐          │
            │    │ ~/Downloads 스캔│          │
            │    │ Claude-Export.md│          │
            │    │ ChatGPT-Export.md│         │
            │    │ Gemini-Chat.md  │          │
            │    └─────────────────┘          │
            │         ↓                        │
            │    [ List[Path] ]                │
            │                                  │
            ├─▶ AIMarkdownParser              │
            │    .parse_multiple()             │
            │    ┌──────────────────┐          │
            │    │ provider 자동감지│          │
            │    │ - Claude: ##     │          │
            │    │ - ChatGPT: **User:**│       │
            │    │ - Gemini: pattern│          │
            │    └──────────────────┘          │
            │         ↓                        │
            │    [ List[ConversationData] ]    │
            │                                  │
            └─▶ AIChatSaver.save_all()         │
               ┌─────────────────────┐         │
               │ 1. JSON 파일 저장   │         │
               │ 2. learning_        │         │
               │    artifacts 삽입   │         │
               │ 3. ai_conversations │         │
               │    삽입             │         │
               └─────────────────────┘         │
                    ↓                          │
               [ artifact_ids ]                │
                                               │
    ┏━━━━━━━━━━━━━━━━━━━━━━━━┓              │
    ┃  4. Baekjoon 수집       ┃              │
    ┗━━━━━━━━━┳━━━━━━━━━━━━━┛              │
              ▼                               │
     ┌──────────────────────┐                │
     │ BaekjoonCollector.   │                │
     │   collect(date)      │                │
     └──────┬───────────────┘                │
            │                                 │
            ├─▶ [1/3] BaekjoonExporter        │
            │         .export_today(date)     │
            │    ┌─────────────────┐          │
            │    │ GitHub API 호출 │          │
            │    │ 백준허브 레포    │          │
            │    │ /백준/문제번호/ │          │
            │    │ 커밋 타임스탬프  │          │
            │    └─────────────────┘          │
            │         ↓                        │
            │    [ List[Dict] 문제 폴더 ]     │
            │                                  │
            ├─▶ [2/3] BaekjoonParser          │
            │         .parse_problems()        │
            │    ┌──────────────────┐          │
            │    │ README.md 파싱   │          │
            │    │ - 문제번호/제목  │          │
            │    │ - 티어/태그      │          │
            │    │ 코드 파일 읽기   │          │
            │    └──────────────────┘          │
            │         ↓                        │
            │    [ List[BaekjoonProblemData] ]│
            │                                  │
            └─▶ [3/3] BaekjoonSaver            │
                    .save_all()                │
               ┌─────────────────────┐         │
               │ 1. JSON 파일 저장   │         │
               │ 2. learning_        │         │
               │    artifacts 삽입   │         │
               │ 3. baekjoon_        │         │
               │    solutions 삽입   │         │
               └─────────────────────┘         │
                    ↓                          │
               [ artifact_ids ]                │
                                               │
               └────────────────────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │  5. 결과 집계 & 출력     │
                    │  ┌────────────────────┐  │
                    │  │ total_artifacts    │  │
                    │  │ github_commits     │  │
                    │  │ claude_conversations│ │
                    │  │ ai_chat_conversations│ │
                    │  │ baekjoon_solutions │  │
                    │  └────────────────────┘  │
                    └────────┬─────────────────┘
                             │
                             ▼
                  ┌────────────────────────┐
                  │  6. JSON 파일로 저장   │
                  │  logs/etl_result_      │
                  │  2025-12-29.json       │
                  └────────────────────────┘
```

---

### 3️⃣ ETL 3단계 패턴 (모든 Collector 공통)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   EXPORT    │ ──▶ │    PARSE    │ ──▶ │    SAVE     │
│  외부 데이터 │     │  구조화     │     │  DB 저장    │
│    수집     │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
     │                   │                   │
     │                   │                   │
     ▼                   ▼                   ▼

 GitHub API          Dict → Dataclass    BaseSaver 상속
 파일 시스템         타입 안전성         ┌──────────────┐
 다운로드 폴더       유효성 검사         │ 1. JSON 파일 │
                                        │ 2. artifacts │
                                        │ 3. 전용 테이블│
                                        └──────────────┘
```

---

### 4️⃣ DB 스키마 구조

```
learning_artifacts (부모 테이블)
├── id (PK, SERIAL)
├── artifact_type (github/ai_chat/baekjoon)
├── artifact_date
├── file_path (JSON 파일 경로)
└── created_at

github_commits (자식 테이블)
├── id (PK)
├── artifact_id (FK → learning_artifacts)
├── sha (UNIQUE)  ← 중복 방지
├── repo, message, commit_date...

ai_conversations (자식 테이블)
├── id (PK)
├── artifact_id (FK → learning_artifacts)
├── provider (claude/chatgpt/gemini)
├── messages (JSONB)

baekjoon_solutions (자식 테이블)
├── id (PK)
├── artifact_id (FK → learning_artifacts)
├── problem_number, title, tier...
```

---

### 5️⃣ 현재 실행 방식

```bash
# 라즈베리파이에서 매일 실행 (cron)
python main.py

# GitHub, Baekjoon 자동 수집
# AI Chat은 --ai-chat-scan 옵션 필요
python main.py --ai-chat-scan
```
