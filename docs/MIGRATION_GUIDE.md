# 기존 DB 마이그레이션 가이드

## 📋 현재 상황

### 라즈베리파이 (PostgreSQL 서버)
```
Database: my_blog
├── public schema (블로그 테이블)
│   ├── posts
│   └── projects
│
└── learning schema (학습 데이터)
    ├── learning_artifacts (1,454개: github 63 + claude 1,114 + baekjoon 277)
    ├── github_commits
    ├── baekjoon_solutions
    └── claude_conversations (아마 존재?)
```

### 목표 구조
```
Database: my_blog (이름 그대로 유지)
├── blog schema (블로그 테이블 - public에서 이동)
│   ├── posts
│   └── projects
│
└── learning schema (학습 데이터 - 업데이트)
    ├── learning_artifacts
    ├── github_commits
    ├── baekjoon_solutions
    ├── claude_conversations (기존 유지)
    └── ai_chat_conversations (새로 추가 - ChatGPT, Gemini용)
```

## 🚀 마이그레이션 실행

### 1. 라즈베리파이에서 실행

```bash
# SSH로 라즈베리파이 접속
ssh user@raspberry-pi-ip

# 프로젝트 디렉토리로 이동
cd /path/to/LearningETL

# 최신 브랜치 pull
git pull origin claude/review-code-tests-alignment-DtRbe

# 마이그레이션 스크립트 실행 권한
chmod +x scripts/migrate-existing-db.sh

# 마이그레이션 실행
bash scripts/migrate-existing-db.sh
```

### 2. 입력할 정보
- PostgreSQL 비밀번호 (postgres 사용자)

### 3. 마이그레이션 내용

스크립트가 자동으로:
1. ✅ `public.posts` → `blog.posts` 이동
2. ✅ `public.projects` → `blog.projects` 이동
3. ✅ `learning.ai_chat_conversations` 테이블 생성
4. ✅ 기존 데이터 보존 (변경 없음)
5. ✅ 인덱스 자동 생성

## 🔍 마이그레이션 확인

```bash
# PostgreSQL 접속
psql -d my_blog

# 스키마 확인
\dn

# 테이블 확인
\dt blog.*;
\dt learning.*;

# 데이터 개수 확인
SELECT source_type, COUNT(*) FROM learning.learning_artifacts GROUP BY source_type;
```

**기대 결과**:
```
 source_type | count
-------------+-------
 github      |    63
 claude      |  1114
 baekjoon    |   277
```

## ⚙️ .env 파일 설정

```bash
# .env 파일 생성
cp .env.example .env
nano .env
```

**중요 설정**:
```bash
# PostgreSQL (블로그와 공유)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=my_blog          # 기존 블로그 DB 사용
DB_USER=postgres
DB_PASSWORD=your_password

# GitHub
GITHUB_TOKEN=ghp_xxxxx
GITHUB_USERNAME=your_username
COLLECT_GITHUB=true

# Baekjoon
BAEKJOON_HANDLE=your_handle
COLLECT_BAEKJOON=true

# AI Chat (새로운 기능)
COLLECT_AI_CHAT=true
```

## 🧪 테스트

### 1. 기존 데이터 확인
```bash
python cli.py stats
```

**기대 출력**:
```
=== 학습 통계 ===
총 학습 활동: 1,454개
- GitHub 커밋: 63개
- Baekjoon 풀이: 277개
- Claude 대화: 1,114개
```

### 2. 새로운 데이터 수집
```bash
# 오늘 데이터 수집
python main.py
```

### 3. 수집 결과 확인
```bash
python cli.py list github --date 2025-12-30
python cli.py list baekjoon --date 2025-12-30
```

## ⚠️ 주의사항

### 블로그와의 독립성
- ✅ **스키마 분리**: `blog.*` vs `learning.*` → 충돌 없음
- ✅ **권한 공유**: `postgres` 사용자가 양쪽 접근 가능
- ✅ **백업 독립**: 스키마별 백업 가능

```bash
# blog만 백업
pg_dump -n blog -d my_blog > blog_backup.sql

# learning만 백업
pg_dump -n learning -d my_blog > learning_backup.sql

# 전체 백업
pg_dump my_blog > full_backup.sql
```

### AI Chat 데이터

현재 `claude` 타입으로 1,114개 저장됨:
```sql
SELECT * FROM learning.learning_artifacts WHERE source_type = 'claude' LIMIT 1;
```

새 코드는:
- ✅ 기존 `claude` 데이터 유지
- ✅ `claude_conversations` 테이블 계속 사용 (있다면)
- ✅ 새로운 ChatGPT/Gemini는 `ai_chat_conversations`에 저장

## 🔄 롤백 (필요시)

만약 문제가 생기면:

```bash
# 백업에서 복구
psql -d my_blog < backup_before_migration.sql
```

또는 수동으로:

```sql
-- blog → public으로 되돌리기
ALTER TABLE blog.posts SET SCHEMA public;
ALTER TABLE blog.projects SET SCHEMA public;

-- ai_chat_conversations 삭제 (비었다면)
DROP TABLE IF EXISTS learning.ai_chat_conversations;
```

## 📊 스키마 비교

### 기존 (현재)
```
my_blog
├── public (posts, projects)
└── learning (learning_artifacts, github_commits, baekjoon_solutions)
```

### 마이그레이션 후
```
my_blog
├── blog (posts, projects)              ← 이름만 변경
└── learning (+ ai_chat_conversations)  ← 테이블 추가
```

**데이터 변경 없음! 구조만 정리!**

## 🎯 다음 단계

마이그레이션 완료 후:

1. **실사용 시작**
   ```bash
   # Cron 설정
   bash scripts/setup-cron.sh
   ```

2. **대시보드 추가** (선택)
   - Web UI로 학습 통계 시각화
   - 블로그와 학습 데이터 통합 대시보드

3. **백업 자동화**
   ```bash
   # 매일 자동 백업
   bash scripts/backup.sh
   ```

## ❓ FAQ

**Q: 블로그에 영향 없나요?**
A: 없습니다. `public` → `blog` 스키마명만 바뀌고, 데이터와 테이블 구조는 그대로입니다.

**Q: 기존 claude 데이터는 어떻게 되나요?**
A: 그대로 유지됩니다. `claude_conversations` 테이블이 있다면 계속 사용합니다.

**Q: 새 ChatGPT 데이터는?**
A: `ai_chat_conversations` 테이블에 저장됩니다. Claude와 분리됩니다.

**Q: 롤백 가능한가요?**
A: 네! 백업만 있으면 언제든 복구 가능합니다.

**Q: 데이터베이스명을 my_db로 바꿔야 하나요?**
A: **필요 없습니다!** `my_blog` 그대로 사용해도 됩니다. 중요한 건 스키마 분리입니다.
