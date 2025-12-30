# LearningETL 데이터베이스 가이드

## 📊 스키마 설계

### 왜 PostgreSQL + JSONB?

**NoSQL 필요 없습니다!** PostgreSQL의 JSONB로 충분합니다:

- ✅ **구조화된 데이터**: 검색/집계에 최적 (날짜, 타입, 태그)
- ✅ **비구조화 데이터**: JSONB로 유연하게 저장 (마크다운 전체 내용, 메시지 배열)
- ✅ **강력한 쿼리**: SQL + JSON 연산자 조합
- ✅ **인덱싱**: GIN 인덱스로 JSONB 내부도 빠르게 검색
- ✅ **트랜잭션**: ACID 보장
- ✅ **관계형 + 문서형**: 하나의 DB로 양쪽 장점

### 테이블 구조

```
learning.learning_artifacts (메인 메타데이터)
├── id (PK)
├── artifact_date          # 학습 날짜
├── source_type           # github, ai_chat_claude, baekjoon
├── title                 # 제목
├── summary              # 요약
├── tags[]               # 태그 배열 (검색용)
├── storage_path         # JSON 파일 경로
└── metadata (JSONB)     # 확장 가능한 메타데이터

learning.github_commits
├── id (PK)
├── artifact_id (FK)
├── repo, sha, message
├── commit_date
├── additions, deletions, files_changed
└── files (JSONB)        # 변경된 파일 상세

learning.ai_chat_conversations
├── id (PK)
├── artifact_id (FK)
├── provider             # Claude, ChatGPT, Gemini
├── title, link
├── user_messages, assistant_messages
├── has_code, code_languages[], code_blocks_count
└── conversation_path    # 전체 마크다운 파일 경로

learning.baekjoon_solutions
├── id (PK)
├── artifact_id (FK)
├── problem_number, title
├── tier, tags[]
├── code (TEXT)          # 소스코드 전체
└── solved_date
```

## 🏗️ 블로그와 공존 전략

### Option 1: 다른 데이터베이스 (추천)

```
PostgreSQL 서버 (localhost:5432)
├── blog (기존 블로그 DB)
└── learning (LearningETL 전용 DB)
```

**장점**:
- 완전 분리, 충돌 없음
- 독립적인 백업/복구
- 권한 관리 단순

**설정**:
```bash
# .env 파일
DB_HOST=localhost
DB_NAME=learning          # 블로그와 다른 DB
DB_USER=learning_user
DB_PASSWORD=secure_password
```

### Option 2: 같은 DB, 다른 스키마

```
PostgreSQL 서버 → my_database
├── public (블로그 테이블)
│   ├── posts
│   └── users
└── learning (LearningETL 테이블)
    ├── learning_artifacts
    └── github_commits
```

**장점**:
- 하나의 연결로 블로그 + 학습 데이터 조인 가능
- "오늘 쓴 블로그 글과 커밋 수" 같은 통합 쿼리

**설정**:
```bash
# .env 파일
DB_HOST=localhost
DB_NAME=blog              # 기존 블로그 DB 사용
DB_USER=blog_user
DB_PASSWORD=blog_password
```

**스키마 분리로 충돌 방지**:
```sql
-- 블로그: public.posts, public.users
-- LearningETL: learning.learning_artifacts, learning.github_commits
```

## 🔍 실제 데이터 예시

### learning_artifacts

| id | artifact_date | source_type | title | tags | storage_path |
|----|--------------|-------------|-------|------|--------------|
| 1 | 2025-12-29 | github | feat: Add authentication | `{github,python,auth}` | learning_artifacts/2025/12/29/github/commit_abc.json |
| 2 | 2025-12-29 | ai_chat_claude | React 최적화 방법 | `{Claude,ai_chat,javascript}` | learning_artifacts/2025/12/29/ai_chat_claude/conv_123.json |
| 3 | 2025-12-28 | baekjoon | 1234번: 다이나믹 프로그래밍 | `{baekjoon,dp,gold}` | learning_artifacts/2025/12/28/baekjoon/1234.json |

### github_commits

| id | artifact_id | repo | sha | message | additions | deletions |
|----|-------------|------|-----|---------|-----------|-----------|
| 1 | 1 | my-app | abc123 | feat: Add authentication | 150 | 20 |

### ai_chat_conversations

| id | artifact_id | provider | title | user_messages | has_code | code_languages |
|----|-------------|----------|-------|---------------|----------|----------------|
| 1 | 2 | Claude | React 최적화 방법 | 5 | true | `{javascript,typescript}` |

### 쿼리 예시

```sql
-- 오늘 학습한 모든 활동
SELECT source_type, COUNT(*)
FROM learning.learning_artifacts
WHERE artifact_date = CURRENT_DATE
GROUP BY source_type;

-- Python 관련 커밋
SELECT a.title, g.sha, g.additions
FROM learning.learning_artifacts a
JOIN learning.github_commits g ON a.id = g.artifact_id
WHERE 'python' = ANY(a.tags)
ORDER BY a.artifact_date DESC;

-- 코드가 포함된 Claude 대화
SELECT a.title, c.code_languages, c.code_blocks_count
FROM learning.learning_artifacts a
JOIN learning.ai_chat_conversations c ON a.id = c.artifact_id
WHERE c.provider = 'Claude' AND c.has_code = true
ORDER BY a.created_at DESC;

-- 월별 커밋 통계
SELECT
    DATE_TRUNC('month', artifact_date) as month,
    COUNT(*) as commits,
    SUM(additions) as total_additions
FROM learning.learning_artifacts a
JOIN learning.github_commits g ON a.id = g.artifact_id
GROUP BY month
ORDER BY month DESC;

-- JSONB 쿼리: 특정 파일 변경한 커밋
SELECT repo, sha, message
FROM learning.github_commits
WHERE files @> '[{"filename": "main.py"}]'::jsonb;
```

## 📦 파일 + DB 하이브리드 저장

### 왜 둘 다?

1. **JSON 파일** (`learning_artifacts/`):
   - ✅ 원본 데이터 보존
   - ✅ 파싱 로직 변경 시 재처리 가능
   - ✅ 백업 간단 (디렉토리 복사)
   - ✅ Git으로 버전 관리 가능

2. **PostgreSQL**:
   - ✅ 빠른 검색/집계
   - ✅ 관계형 쿼리 (JOIN)
   - ✅ 인덱싱으로 성능 최적화
   - ✅ CLI/Dashboard에서 즉시 조회

### 데이터 흐름

```
GitHub API
    ↓
[Collector] 수집
    ↓
[Parser] 파싱
    ↓
    ├─→ JSON 파일 저장 (learning_artifacts/2025/12/29/github/commit_abc.json)
    │
    └─→ DB 저장
        ├─→ learning_artifacts (메타데이터)
        └─→ github_commits (상세 데이터)
```

## 🚀 빠른 시작

### 1. DB 생성 (깨끗한 상태)

```bash
# .env 파일 생성
cp .env.example .env
nano .env  # DB 설정 입력

# DB 자동 생성 (learning 데이터베이스 + 테이블)
bash scripts/setup-database.sh
```

### 2. 데이터 수집

```bash
# 첫 실행
python main.py

# CLI로 확인
python cli.py stats
```

### 3. 직접 쿼리

```bash
# DB 접속
psql -h localhost -U learning_user -d learning

# 테이블 확인
\dt learning.*

# 데이터 확인
SELECT * FROM learning.learning_artifacts ORDER BY created_at DESC LIMIT 5;
```

## 🔧 마이그레이션 (기존 데이터가 있다면)

만약 이전에 다른 스키마로 데이터를 넣었다면:

```bash
# 1. 기존 데이터 백업
pg_dump -U postgres -d learning > backup_old.sql

# 2. 스키마 재생성
psql -U postgres -d learning -c "DROP SCHEMA learning CASCADE;"
bash scripts/setup-database.sh

# 3. 데이터 재수집 (JSON 파일이 있다면 재처리 가능)
```

## 💡 FAQ

**Q: 마크다운 파일 전체를 DB에 넣어야 하나요?**
A: 선택사항입니다. 현재는 파일 경로만 저장하고, 필요시 파일을 읽습니다. 검색이 자주 필요하면 JSONB 컬럼에 추가할 수 있습니다.

**Q: NoSQL이 더 낫지 않나요?**
A: PostgreSQL JSONB가 NoSQL의 유연성 + SQL의 강력함을 모두 제공합니다. 학습 데이터는 관계형 쿼리가 많아서 PostgreSQL이 유리합니다.

**Q: 블로그 DB와 같이 써도 안전한가요?**
A: 네! `learning` 스키마를 사용하므로 블로그의 `public` 스키마와 충돌하지 않습니다.

**Q: 스키마를 나중에 바꿀 수 있나요?**
A: 네! `ALTER TABLE` 또는 JSON 파일 재파싱으로 가능합니다.
