# Learning Artifacts ETL Pipeline - 아키텍처

## 📋 프로젝트 개요

모든 학습 활동(GitHub 커밋, Claude 대화, 백준 문제풀이)을 자동으로 수집하여 PostgreSQL DB에 저장하고, 향후 블로그 포스팅으로 변환하는 ETL 파이프라인입니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                           데이터 수집 (Export)                         │
├─────────────────────────────────────────────────────────────────────┤
│  export/                                                             │
│  ├── github_export.py       → GitHub API로 커밋 수집                  │
│  ├── claude_export.py       → [삭제됨] 수동 다운로드 방식으로 변경      │
│  └── baekjoon_export.py     → solved.ac API + Selenium 크롤링        │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                           데이터 파싱 (Parse)                          │
├─────────────────────────────────────────────────────────────────────┤
│  parse/                                                              │
│  ├── github_parse.py        → 커밋 구조화, 언어 감지, 주석 추출        │
│  ├── claude_parse.py        → 대화 파싱, 코드 블록 추출               │
│  └── baekjoon_parse.py      → 문제 데이터 구조화, 코드 분석           │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          통합 수집 (Collectors)                        │
├─────────────────────────────────────────────────────────────────────┤
│  collectors/                                                         │
│  ├── github_collector.py    → Export + Parse + Storage 통합          │
│  ├── claude_collector.py    → Parse + Storage (수동 ZIP 입력)        │
│  └── baekjoon_collector.py  → Export + Parse + Storage 통합          │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                           데이터 저장 (Storage)                        │
├─────────────────────────────────────────────────────────────────────┤
│  storage/                                                            │
│  ├── base_saver.py          → PostgreSQL 연결 베이스                  │
│  ├── github_saver.py        → GitHub 커밋 → DB                       │
│  ├── claude_saver.py        → Claude 대화 → DB                       │
│  ├── baekjoon_saver.py      → 백준 문제풀이 → DB                      │
│  └── artifact_saver.py      → 파일 시스템 저장 (미래)                 │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                           PostgreSQL 데이터베이스                      │
├─────────────────────────────────────────────────────────────────────┤
│  learning_artifacts/                                                 │
│  ├── learning_artifacts     → 모든 학습 활동 메타데이터                │
│  ├── github_commits         → GitHub 커밋                            │
│  ├── claude_conversations   → Claude 대화                            │
│  └── baekjoon_solutions     → 백준 문제풀이                           │
└─────────────────────────────────────────────────────────────────────┘
```

## 📁 프로젝트 구조

```
LearningETL/
├── main.py                     # 메인 진입점 (ETL 파이프라인 실행)
│
├── config/                     # 설정 관리
│   ├── __init__.py
│   └── settings.py            # 환경변수, DB 설정, 디렉토리 경로
│
├── export/                     # 데이터 수집 모듈
│   ├── github_export.py       # GitHub REST API
│   └── baekjoon_export.py     # solved.ac API + Selenium
│
├── parse/                      # 데이터 파싱 모듈
│   ├── github_parse.py        # 커밋 데이터 구조화
│   ├── claude_parse.py        # 대화 ZIP 파싱
│   └── baekjoon_parse.py      # 문제 데이터 구조화
│
├── collectors/                 # 통합 수집기 (Export + Parse + Storage)
│   ├── __init__.py
│   ├── github_collector.py
│   ├── claude_collector.py
│   └── baekjoon_collector.py
│
├── storage/                    # 데이터 저장 모듈
│   ├── __init__.py
│   ├── base_saver.py          # PostgreSQL 베이스 클래스
│   ├── github_saver.py        # GitHub DB 저장
│   ├── claude_saver.py        # Claude DB 저장
│   ├── baekjoon_saver.py      # 백준 DB 저장
│   └── artifact_saver.py      # 파일 시스템 저장 (미래)
│
├── tests/                      # 테스트 코드
│   ├── test_github.py
│   └── test_db_save.py
│
├── docs/                       # 문서
│   └── ARCHITECTURE.md        # 구 아키텍처 문서 (참고용)
│
└── temp/                       # 임시 파일 (gitignore)
    └── claude_downloads/      # Claude 수동 다운로드 ZIP 저장 위치
```

## 🔄 데이터 흐름

### 1. GitHub 수집 흐름

```python
# main.py
etl = LearningETL()
results = etl.run(target_date='2025-12-27')

# collectors/github_collector.py
collector = GitHubCollector()
result = collector.collect(target_date)

    # 1) Export
    exporter = GitHubExporter()
    commits = exporter.export_today(target_date)

    # 2) Parse
    parser = GitHubParser()
    parsed_commits = parser.parse_commits(commits)

    # 3) Storage
    saver = GitHubSaver()
    artifact_ids = saver.save_all(parsed_commits, target_date)
```

### 2. Claude 수집 흐름 (수동 다운로드 방식)

```python
# main.py
etl = LearningETL()
results = etl.run(
    target_date='2025-12-27',
    claude_zip_path='/path/to/conversations.zip'  # 수동 다운로드한 ZIP
)

# collectors/claude_collector.py
collector = ClaudeCollector()
result = collector.collect(zip_path, target_date)

    # 1) Parse (Export는 수동)
    parser = ClaudeParser()
    conversations = parser.parse_zip(zip_path)
    filtered = parser.filter_by_date(conversations, target_date)

    # 2) Storage
    saver = ClaudeSaver()
    artifact_ids = saver.save_all(filtered, target_date)
```

### 3. 백준 수집 흐름

```python
# collectors/baekjoon_collector.py
collector = BaekjoonCollector()
result = collector.collect(target_date)

    # 1) Export
    exporter = BaekjoonExporter()
    problems = exporter.export_today(target_date)

    # 2) Parse
    parser = BaekjoonParser()
    parsed_problems = parser.parse_problems(problems)

    # 3) Storage
    saver = BaekjoonSaver()
    artifact_ids = saver.save_all(parsed_problems, target_date)
```

## 💾 데이터베이스 스키마

### learning_artifacts (통합 메타데이터)

```sql
CREATE TABLE learning_artifacts (
    id SERIAL PRIMARY KEY,
    artifact_date DATE NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'github', 'claude', 'baekjoon'
    title TEXT,
    summary TEXT,
    tags TEXT[],
    storage_path TEXT,                 -- 파일 경로 (미래)
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### github_commits

```sql
CREATE TABLE github_commits (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning_artifacts(id),
    repo VARCHAR(255) NOT NULL,
    sha VARCHAR(40) NOT NULL,
    message TEXT,
    commit_date TIMESTAMP,
    files_changed INTEGER,
    additions INTEGER,
    deletions INTEGER,
    commit_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### claude_conversations

```sql
CREATE TABLE claude_conversations (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning_artifacts(id),
    uuid VARCHAR(255) UNIQUE NOT NULL,
    name TEXT,
    summary TEXT,
    user_messages INTEGER,
    assistant_messages INTEGER,
    has_code BOOLEAN,
    conversation_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### baekjoon_solutions

```sql
CREATE TABLE baekjoon_solutions (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning_artifacts(id),
    problem_id INTEGER NOT NULL,
    title TEXT,
    tier VARCHAR(50),
    tags TEXT[],
    language VARCHAR(50),
    code TEXT,
    memory VARCHAR(50),
    time VARCHAR(50),
    solution_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🔧 주요 설계 결정사항

### 1. Claude Export 자동화 제거 (2025-12-27)

**변경 전:**
- `export/claude_export.py`: Selenium으로 자동 로그인 + Export 클릭
- 쿠키 저장 방식 (`CLAUDE_COOKIES_PATH`)

**변경 후:**
- Export 자동화 삭제
- 사용자가 수동으로 ZIP 다운로드
- `collectors/claude_collector.py`가 ZIP 경로를 매개변수로 받음

**이유:**
- 쿠키 기반 자동화는 유지보수 어려움
- Claude UI 변경 시 코드 수정 필요
- 수동 다운로드가 더 안정적

### 2. db_savers → storage 통합

**변경사항:**
- `db_savers/` 폴더 → `storage/`로 이동
- 모든 import 경로 업데이트

**이유:**
- `storage`가 더 포괄적인 이름 (DB + 파일 저장)
- 향후 `artifact_saver.py`와 통합 용이

### 3. 테스트 파일 분리

**변경사항:**
- `test_*.py` → `tests/` 폴더로 이동

**이유:**
- 루트 디렉토리 정리
- 테스트 코드와 프로덕션 코드 분리

## 🚀 향후 확장 계획

### 1. 파일 시스템 저장 (`artifact_saver.py`)

```python
# storage/artifact_saver.py
class ArtifactSaver:
    def save_to_file(self, data, source_type, date):
        # learning_artifacts/2025/12/27/github/commit_abc123.json
        path = self.get_file_path(source_type, date)
        with open(path, 'w') as f:
            json.dump(data, f)
        return path
```

### 2. AI 분석 모듈

```python
# analysis/claude_analyzer.py
class ClaudeAnalyzer:
    def analyze_activity(self, artifact_id):
        # Claude API로 학습 주제 추출
        # 핵심 포인트 요약
        # 블로그 포스트 초안 생성
        pass
```

### 3. 블로그 포스팅 자동화

```python
# blog/post_generator.py
class PostGenerator:
    def generate_dev_log(self, commits):
        # GitHub 커밋 → Dev Log 포스트
        pass

    def generate_algorithm_post(self, problems):
        # 백준 문제 → Algorithm 포스트
        pass
```

## 📊 성능 최적화

### PostgreSQL 인덱스

```sql
-- 날짜별 조회 (가장 빈번)
CREATE INDEX idx_artifacts_date ON learning_artifacts(artifact_date);

-- 소스별 필터링
CREATE INDEX idx_artifacts_source ON learning_artifacts(source_type);

-- 태그 검색 (GIN 인덱스)
CREATE INDEX idx_artifacts_tags ON learning_artifacts USING GIN(tags);

-- JSONB 메타데이터 검색
CREATE INDEX idx_artifacts_metadata ON learning_artifacts USING GIN(metadata);
```

## 🔐 보안 고려사항

### 환경변수 관리

```bash
# .env 파일 (gitignore)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_USERNAME=cjang3285
BAEKJOON_HANDLE=andy1692

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
.pytest_cache/
```

## 📝 사용법

### 1. GitHub + 백준 자동 수집

```bash
python main.py
```

### 2. Claude 포함 전체 수집

```bash
# 1. claude.ai에서 수동으로 Export → ZIP 다운로드
# 2. ZIP 경로와 함께 실행
python main.py --claude-zip ~/Downloads/conversations.zip
```

### 3. 특정 날짜 수집

```bash
python main.py --date 2025-12-26 --claude-zip conversations.zip
```

## 🛠️ 개발 가이드

### 새로운 소스 추가 예시 (Notion)

1. **Export 모듈**: `export/notion_export.py`
2. **Parse 모듈**: `parse/notion_parse.py`
3. **Collector**: `collectors/notion_collector.py`
4. **Storage**: `storage/notion_saver.py`
5. **DB 테이블**: `notion_notes` 추가
6. **Config**: `settings.py`에 Notion API 키 추가

## 📚 참고 문서

- [이전 아키텍처 문서](docs/ARCHITECTURE.md)
- [README](README.md)
