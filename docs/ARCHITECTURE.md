# Learning Artifacts ETL Pipeline - 아키텍처

## 📋 프로젝트 개요

모든 학습 활동(GitHub 커밋, AI 채팅, 백준 문제풀이)을 자동으로 수집하여 PostgreSQL DB에 저장하는 ETL 파이프라인입니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                           데이터 소스                                  │
├─────────────────────────────────────────────────────────────────────┤
│  1. GitHub REST API          → 커밋 메타데이터 + Diff                │
│  2. TIL 레포 (GitHub API)    → 백준 README.md + 코드                │
│  3. AI Chat 마크다운         → Claude/ChatGPT/Gemini 내보내기        │
│  4. Claude ZIP (선택)        → 첫 마이그레이션용                     │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                           데이터 수집 (Export)                         │
├─────────────────────────────────────────────────────────────────────┤
│  export/                                                             │
│  ├── github_export.py        → GitHub API (커밋)                     │
│  ├── baekjoon_export.py      → GitHub API (TIL 레포)                │
│  └── ai_chat_export.py       → 파일 감시 (Downloads 폴더)           │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                           데이터 파싱 (Parse)                          │
├─────────────────────────────────────────────────────────────────────┤
│  parse/                                                              │
│  ├── github_parse.py              → 커밋 구조화, 주석 추출           │
│  ├── baekjoon_parse.py            → README.md 파싱, 코드 추출       │
│  ├── ai_chat_parse.py             → 마크다운 파싱                   │
│  └── claude_migration_parse.py    → ZIP 파싱 (첫 마이그레이션)      │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          통합 수집 (Collectors)                        │
├─────────────────────────────────────────────────────────────────────┤
│  collectors/                                                         │
│  ├── github_collector.py          → Export + Parse + Storage        │
│  ├── baekjoon_collector.py        → Export + Parse + Storage        │
│  ├── ai_chat_collector.py         → Parse + Storage (마크다운)       │
│  └── claude_migration_collector.py → Parse + Storage (ZIP)          │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                           데이터 저장 (Storage)                        │
├─────────────────────────────────────────────────────────────────────┤
│  storage/                                                            │
│  ├── base_saver.py                → PostgreSQL 연결 베이스           │
│  ├── github_saver.py              → GitHub 커밋 → DB                │
│  ├── baekjoon_saver.py            → 백준 문제풀이 → DB              │
│  ├── ai_chat_saver.py             → AI 채팅 → DB                   │
│  └── claude_migration_saver.py    → Claude ZIP → DB                │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                           PostgreSQL 데이터베이스                      │
├─────────────────────────────────────────────────────────────────────┤
│  learning 스키마/                                                    │
│  ├── learning_artifacts          → 모든 학습 활동 메타데이터          │
│  ├── github_commits              → GitHub 커밋                       │
│  ├── baekjoon_solutions          → 백준 문제풀이                     │
│  ├── ai_chat_conversations       → AI 채팅 (Claude/ChatGPT/Gemini) │
│  └── claude_conversations        → Claude ZIP (레거시)              │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 데이터 흐름

### 1. GitHub 수집 흐름

```python
# main.py
etl = LearningETL()
results = etl.run(target_date='2025-12-29')

# collectors/github_collector.py
collector = GitHubCollector()
result = collector.collect(target_date)

    # 1) Export - GitHub API로 커밋 수집
    exporter = GitHubExporter()
    commits = exporter.export_today(target_date)

    # 2) Parse - 커밋 구조화
    parser = GitHubParser()
    parsed_commits = parser.parse_commits(commits)

    # 3) Storage - DB 저장
    saver = GitHubSaver()
    artifact_ids = saver.save_all(parsed_commits, target_date)
```

### 2. AI 채팅 수집 흐름 (마크다운)

```python
# main.py --ai-chat-scan
etl = LearningETL()
results = etl.run(ai_chat_scan=True)

# collectors/ai_chat_collector.py
collector = AIChatCollector()
result = collector.collect_from_downloads()

    # 1) Export - 다운로드 폴더 스캔
    watcher = AIExportWatcher()
    ai_files = watcher.scan_existing()

    # 2) Parse - 마크다운 파싱
    parser = AIMarkdownParser()
    conversations = parser.parse_multiple(ai_files)

    # 3) Storage - DB 저장
    saver = AIChatSaver()
    artifact_ids = saver.save_all(conversations, target_date)
```

### 3. 백준 수집 흐름 (TIL 레포)

```python
# collectors/baekjoon_collector.py
collector = BaekjoonCollector()
result = collector.collect(target_date)

    # 1) Export - TIL 레포에서 커밋 가져오기
    exporter = BaekjoonExporter()
    problems = exporter.export_today(target_date)

    # 2) Parse - README.md + 코드 파일 파싱
    parser = BaekjoonParser()
    parsed = parser.parse_problems(problems, exporter)

    # 3) Storage - DB 저장
    saver = BaekjoonSaver()
    artifact_ids = saver.save_all(parsed, target_date)
```

### 4. Claude 마이그레이션 (첫 이용 시)

```python
# main.py --claude-zip conversations.zip --all
etl = LearningETL()
results = etl.run(
    claude_zip_path='~/Downloads/conversations.zip',
    all_dates=True
)

# collectors/claude_migration_collector.py
collector = ClaudeMigrationCollector()
result = collector.collect(zip_path, all_dates=True)

    # 1) Parse - ZIP 파일 파싱
    parser = ClaudeMigrationParser()
    conversations = parser.parse_zip(zip_path)

    # 2) Storage - DB 저장
    saver = ClaudeMigrationSaver()
    artifact_ids = saver.save_all(conversations, target_date)
```

## 💾 데이터베이스 스키마

### learning_artifacts (통합 메타데이터)

모든 학습 활동의 중앙 테이블

```sql
CREATE TABLE learning.learning_artifacts (
    id SERIAL PRIMARY KEY,
    artifact_date DATE NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'github', 'ai_chat_claude', 'baekjoon' 등
    title TEXT,
    summary TEXT,
    tags TEXT[],
    storage_path TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_artifacts_date ON learning.learning_artifacts(artifact_date);
CREATE INDEX idx_artifacts_source ON learning.learning_artifacts(source_type);
CREATE INDEX idx_artifacts_tags ON learning.learning_artifacts USING GIN(tags);
```

### github_commits

```sql
CREATE TABLE learning.github_commits (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning.learning_artifacts(id),
    repo VARCHAR(255) NOT NULL,
    sha VARCHAR(40) UNIQUE NOT NULL,
    message TEXT,
    commit_date TIMESTAMP,
    files_changed INTEGER,
    additions INTEGER,
    deletions INTEGER,
    commit_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_github_repo ON learning.github_commits(repo);
CREATE INDEX idx_github_sha ON learning.github_commits(sha);
```

### ai_chat_conversations (마크다운)

```sql
CREATE TABLE learning.ai_chat_conversations (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning.learning_artifacts(id),
    provider VARCHAR(50) NOT NULL,  -- 'claude', 'chatgpt', 'gemini'
    title TEXT NOT NULL,
    link TEXT,
    user_messages INTEGER DEFAULT 0,
    assistant_messages INTEGER DEFAULT 0,
    has_code BOOLEAN DEFAULT FALSE,
    conversation_path TEXT,
    code_languages TEXT[],
    code_blocks_count INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_chat_provider ON learning.ai_chat_conversations(provider);
CREATE INDEX idx_ai_chat_has_code ON learning.ai_chat_conversations(has_code);
```

### baekjoon_solutions

```sql
CREATE TABLE learning.baekjoon_solutions (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning.learning_artifacts(id),
    problem_id INTEGER NOT NULL,
    title TEXT,
    tier VARCHAR(50),        -- "Silver III", "Bronze V" 등
    memory VARCHAR(50),      -- "3336 KB"
    time VARCHAR(50),        -- "36 ms"
    tags TEXT[],
    language VARCHAR(50),
    code TEXT,
    description TEXT,
    commit_sha VARCHAR(40),
    submitted_at TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_baekjoon_problem ON learning.baekjoon_solutions(problem_id);
CREATE INDEX idx_baekjoon_tier ON learning.baekjoon_solutions(tier);
```

### claude_conversations (레거시, ZIP 전용)

```sql
CREATE TABLE learning.claude_conversations (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning.learning_artifacts(id),
    uuid VARCHAR(255) UNIQUE NOT NULL,
    name TEXT,
    summary TEXT,
    user_messages INTEGER,
    assistant_messages INTEGER,
    has_code BOOLEAN,
    duration_minutes FLOAT,
    conversation_path TEXT,
    code_languages TEXT[],
    code_blocks_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_claude_uuid ON learning.claude_conversations(uuid);
```

## 🔧 주요 설계 결정사항

### 1. 백준: Selenium → TIL 레포 기반

**변경 전 (Selenium)**:
- solved.ac API로 문제 목록 조회
- Selenium으로 백준 로그인 후 코드 크롤링
- 쿠키 관리 필요, 불안정

**변경 후 (TIL 레포)**:
- 크롬 확장 프로그램이 TIL 레포에 자동 푸시
- GitHub API로 커밋 및 파일 읽기
- README.md에 모든 메타데이터 포함
- 안정적이고 API rate limit만 관리

**장점**:
- Selenium 의존성 제거
- solved.ac API 불필요
- 크롤링 실패 위험 없음
- 모든 메타데이터 포함 (티어, 태그, 성능)

### 2. AI Chat: ZIP → 마크다운

**일상 사용**:
- 브라우저 확장 프로그램으로 마크다운 내보내기
- 다운로드 폴더 자동 감시
- 실시간 수집

**첫 마이그레이션**:
- claude.ai에서 전체 대화 ZIP 다운로드
- `--claude-zip` + `--all` 옵션
- 한 번만 실행

**이유**:
- ZIP은 Claude 전용, 다른 AI는 지원 안 함
- 마크다운은 3개 AI 모두 지원
- 일상적으로는 마크다운이 더 편리

### 3. 모듈화 아키텍처

**Export ↔ Parse ↔ Storage 분리**:
- Export: 데이터 수집만 담당
- Parse: 구조화 및 검증
- Storage: DB 저장 및 파일 관리
- Collector: 통합 orchestration

**장점**:
- 각 모듈 독립적 테스트 가능
- 새로운 소스 추가 쉬움
- 데이터 파이프라인 명확

## 📊 성능 최적화

### PostgreSQL 인덱스

```sql
-- 날짜별 조회 (가장 빈번)
CREATE INDEX idx_artifacts_date ON learning.learning_artifacts(artifact_date);

-- 소스별 필터링
CREATE INDEX idx_artifacts_source ON learning.learning_artifacts(source_type);

-- 태그 검색 (GIN 인덱스)
CREATE INDEX idx_artifacts_tags ON learning.learning_artifacts USING GIN(tags);

-- JSONB 메타데이터 검색
CREATE INDEX idx_artifacts_metadata ON learning.learning_artifacts USING GIN(metadata);
```

### GitHub API Rate Limit 관리

```python
# GitHub API: 5000 requests/hour (authenticated)
# 전략:
# 1. 커밋 상세는 필요한 것만
# 2. 파일 내용은 캐싱
# 3. 병렬 요청 최소화
```

## 🛠️ 개발 가이드

### 새로운 소스 추가 예시 (Notion)

1. **Export 모듈**: `export/notion_export.py`
2. **Parse 모듈**: `parse/notion_parse.py`
3. **Saver**: `storage/notion_saver.py`
4. **Collector**: `collectors/notion_collector.py`
5. **DB 테이블**: `notion_notes` 추가
6. **Config**: `COLLECT_NOTION` 설정 추가
7. **Main.py**: `notion_collector` 통합

### 테스트 방법

```bash
# 개별 모듈 테스트
python export/github_export.py
python parse/ai_chat_parse.py test.md
python collectors/github_collector.py

# 전체 파이프라인 테스트
python main.py --date 2025-12-28
```

## 🔐 보안 고려사항

### 환경변수 관리

```bash
# .env 파일 (gitignore)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_USERNAME=cjang3285
BAEKJOON_HANDLE=andy1692
BAEKJOON_TIL_REPO=Baekjoon_solutions

DB_HOST=localhost
DB_PORT=5432
DB_NAME=my_blog
DB_USER=postgres
DB_PASSWORD=xxxxx
```

### Gitignore 필수 항목

```gitignore
# 민감 정보
.env
*.pkl
temp/
logs/
learning_artifacts/

# Python
__pycache__/
*.pyc

# 출력 데이터
output/
outputs/
```

## 📝 사용법

### 1. GitHub + 백준 자동 수집

```bash
python main.py
```

### 2. AI Chat 일상 사용

```bash
# 다운로드 폴더 자동 스캔
python main.py --ai-chat-scan

# 특정 파일 지정
python main.py --ai-chat ~/Downloads/Claude-*.md
```

### 3. 첫 Claude 마이그레이션

```bash
# claude.ai에서 Export → ZIP 다운로드
# 전체 대화 수집
python main.py --claude-zip ~/Downloads/conversations.zip --all
```

### 4. 특정 날짜 수집

```bash
python main.py --date 2025-12-26
```

### 5. Cron 자동화

```bash
# crontab -e
0 23 * * * cd /path/to/LearningETL && python main.py --ai-chat-scan
```

## 📚 참고 문서

- [README](../README.md)
- [AI Chat 통합 가이드](AI_CHAT_INTEGRATION.md)
