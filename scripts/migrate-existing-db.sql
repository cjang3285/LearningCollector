-- ========================================
-- LearningETL 기존 DB 마이그레이션
-- ========================================
--
-- 목적:
-- 1. public 스키마의 블로그 테이블 → blog 스키마로 이동
-- 2. learning 스키마는 그대로 유지
-- 3. ai_chat_conversations 테이블 추가 (claude_conversations가 있다면 호환성 유지)
--
-- 실행 방법:
-- psql -h localhost -U postgres -d my_blog -f migrate-existing-db.sql
-- ========================================

\echo '========================================';
\echo '1. 현재 상태 확인';
\echo '========================================';

-- 기존 스키마 확인
\dn

-- 기존 테이블 확인
\dt public.*;
\dt learning.*;

\echo '';
\echo '========================================';
\echo '2. blog 스키마 생성 및 테이블 이동';
\echo '========================================';

-- blog 스키마 생성
CREATE SCHEMA IF NOT EXISTS blog;

-- public.posts → blog.posts 이동
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'posts') THEN
        ALTER TABLE public.posts SET SCHEMA blog;
        RAISE NOTICE 'public.posts → blog.posts 이동 완료';
    END IF;
END $$;

-- public.projects → blog.projects 이동
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'projects') THEN
        ALTER TABLE public.projects SET SCHEMA blog;
        RAISE NOTICE 'public.projects → blog.projects 이동 완료';
    END IF;
END $$;

-- public 스키마의 다른 모든 테이블도 이동 (있다면)
DO $$
DECLARE
    tbl RECORD;
BEGIN
    FOR tbl IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename NOT IN ('posts', 'projects')
    LOOP
        EXECUTE format('ALTER TABLE public.%I SET SCHEMA blog', tbl.tablename);
        RAISE NOTICE 'public.% → blog.% 이동 완료', tbl.tablename, tbl.tablename;
    END LOOP;
END $$;

\echo '';
\echo '========================================';
\echo '3. learning 스키마 테이블 확인 및 추가';
\echo '========================================';

-- claude_conversations 테이블이 있는지 확인
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'learning'
                    AND table_name = 'claude_conversations')
        THEN '✓ learning.claude_conversations 존재'
        ELSE '✗ learning.claude_conversations 없음'
    END as claude_table_status;

-- ai_chat_conversations 테이블이 있는지 확인
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'learning'
                    AND table_name = 'ai_chat_conversations')
        THEN '✓ learning.ai_chat_conversations 존재'
        ELSE '✗ learning.ai_chat_conversations 없음 - 생성 필요'
    END as ai_chat_table_status;

-- ai_chat_conversations 테이블 생성 (없다면)
CREATE TABLE IF NOT EXISTS learning.ai_chat_conversations (
    id BIGSERIAL PRIMARY KEY,
    artifact_id BIGINT REFERENCES learning.learning_artifacts(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    title TEXT,
    link TEXT,
    user_messages INTEGER DEFAULT 0,
    assistant_messages INTEGER DEFAULT 0,
    has_code BOOLEAN DEFAULT FALSE,
    conversation_path TEXT,
    code_languages TEXT[],
    code_blocks_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_ai_chat_provider ON learning.ai_chat_conversations(provider);
CREATE INDEX IF NOT EXISTS idx_ai_chat_created ON learning.ai_chat_conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_chat_artifact ON learning.ai_chat_conversations(artifact_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_languages ON learning.ai_chat_conversations USING GIN(code_languages);

\echo 'ai_chat_conversations 테이블 준비 완료';

-- learning_artifacts 테이블에 필요한 컬럼 확인 및 추가
DO $$
BEGIN
    -- updated_at 컬럼이 있는지 확인
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'learning'
        AND table_name = 'learning_artifacts'
        AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE learning.learning_artifacts
        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'learning_artifacts에 updated_at 컬럼 추가';
    END IF;
END $$;

\echo '';
\echo '========================================';
\echo '4. 마이그레이션 완료 - 최종 상태';
\echo '========================================';

-- 스키마별 테이블 목록
\echo '';
\echo '--- blog 스키마 ---';
\dt blog.*;

\echo '';
\echo '--- learning 스키마 ---';
\dt learning.*;

\echo '';
\echo '========================================';
\echo '✓ 마이그레이션 완료!';
\echo '========================================';
\echo '';
\echo '데이터 확인:';
SELECT
    'blog.posts' as table_name,
    COUNT(*) as count
FROM blog.posts
UNION ALL
SELECT
    'blog.projects',
    COUNT(*)
FROM blog.projects
UNION ALL
SELECT
    'learning.learning_artifacts',
    COUNT(*)
FROM learning.learning_artifacts
UNION ALL
SELECT
    'learning.github_commits',
    COUNT(*)
FROM learning.github_commits
UNION ALL
SELECT
    'learning.baekjoon_solutions',
    COUNT(*)
FROM learning.baekjoon_solutions;

\echo '';
\echo 'source_type별 통계:';
SELECT source_type, COUNT(*) as count
FROM learning.learning_artifacts
GROUP BY source_type
ORDER BY count DESC;
