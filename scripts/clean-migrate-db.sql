-- ========================================
-- LearningETL 깔끔한 마이그레이션
-- 기존 claude 데이터 삭제 & 새로운 구조로 시작
-- ========================================
--
-- ⚠️  경고: 이 스크립트는 기존 claude 데이터를 모두 삭제합니다!
--
-- 삭제 대상:
-- - learning.claude_conversations 테이블 (있다면)
-- - learning.learning_artifacts에서 source_type = 'claude'인 데이터
--
-- 실행 방법:
-- psql -h localhost -U postgres -d my_blog -f clean-migrate-db.sql
-- ========================================

\echo '';
\echo '========================================';
\echo '⚠️  경고: 기존 Claude 데이터 삭제';
\echo '========================================';
\echo '';
\echo '다음 데이터가 삭제됩니다:';

-- 삭제될 데이터 확인
SELECT
    'claude_conversations 테이블 레코드' as 항목,
    COALESCE((SELECT COUNT(*) FROM learning.claude_conversations), 0) as 개수
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'learning' AND table_name = 'claude_conversations'
)
UNION ALL
SELECT
    'learning_artifacts (source_type=claude)',
    COUNT(*)
FROM learning.learning_artifacts
WHERE source_type = 'claude';

\echo '';
\echo '5초 후 삭제를 진행합니다...';
\echo '취소하려면 Ctrl+C를 누르세요!';

SELECT pg_sleep(5);

\echo '';
\echo '========================================';
\echo '1. 기존 Claude 데이터 삭제';
\echo '========================================';

-- claude_conversations 테이블 삭제 (있다면)
DROP TABLE IF EXISTS learning.claude_conversations CASCADE;
\echo '✓ claude_conversations 테이블 삭제 (있었다면)';

-- learning_artifacts에서 claude 데이터 삭제
DELETE FROM learning.learning_artifacts
WHERE source_type = 'claude';

\echo '✓ claude 타입 artifacts 삭제';

\echo '';
\echo '========================================';
\echo '2. blog 스키마로 마이그레이션';
\echo '========================================';

-- blog 스키마 생성
CREATE SCHEMA IF NOT EXISTS blog;
\echo '✓ blog 스키마 생성';

-- public.posts → blog.posts 이동
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'posts') THEN
        ALTER TABLE public.posts SET SCHEMA blog;
        RAISE NOTICE '✓ public.posts → blog.posts 이동';
    ELSE
        RAISE NOTICE '  (public.posts 없음, 건너뜀)';
    END IF;
END $$;

-- public.projects → blog.projects 이동
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'projects') THEN
        ALTER TABLE public.projects SET SCHEMA blog;
        RAISE NOTICE '✓ public.projects → blog.projects 이동';
    ELSE
        RAISE NOTICE '  (public.projects 없음, 건너뜀)';
    END IF;
END $$;

-- public 스키마의 다른 테이블도 모두 blog로 이동
DO $$
DECLARE
    tbl RECORD;
    moved_count INTEGER := 0;
BEGIN
    FOR tbl IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename NOT IN ('posts', 'projects')
    LOOP
        EXECUTE format('ALTER TABLE public.%I SET SCHEMA blog', tbl.tablename);
        moved_count := moved_count + 1;
        RAISE NOTICE '✓ public.% → blog.% 이동', tbl.tablename, tbl.tablename;
    END LOOP;

    IF moved_count = 0 THEN
        RAISE NOTICE '  (다른 public 테이블 없음)';
    END IF;
END $$;

\echo '';
\echo '========================================';
\echo '3. ai_chat_conversations 테이블 생성';
\echo '========================================';

-- ai_chat_conversations 테이블 생성
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

\echo '✓ ai_chat_conversations 테이블 생성';

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_ai_chat_provider
    ON learning.ai_chat_conversations(provider);
CREATE INDEX IF NOT EXISTS idx_ai_chat_created
    ON learning.ai_chat_conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_chat_artifact
    ON learning.ai_chat_conversations(artifact_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_languages
    ON learning.ai_chat_conversations USING GIN(code_languages);

\echo '✓ 인덱스 생성';

-- learning_artifacts에 updated_at 컬럼 추가 (없다면)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'learning'
        AND table_name = 'learning_artifacts'
        AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE learning.learning_artifacts
        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE '✓ learning_artifacts.updated_at 컬럼 추가';
    ELSE
        RAISE NOTICE '  (updated_at 이미 존재)';
    END IF;
END $$;

-- source_type에 ai_chat 타입 추가 (CHECK constraint 업데이트)
DO $$
BEGIN
    -- 기존 constraint 삭제
    ALTER TABLE learning.learning_artifacts
    DROP CONSTRAINT IF EXISTS check_source_type;

    -- 새 constraint 생성
    ALTER TABLE learning.learning_artifacts
    ADD CONSTRAINT check_source_type
    CHECK (source_type IN (
        'github',
        'baekjoon',
        'ai_chat_claude',
        'ai_chat_chatgpt',
        'ai_chat_gemini',
        'goodnotes',
        'notion',
        'other'
    ));

    RAISE NOTICE '✓ source_type constraint 업데이트 (ai_chat_* 추가)';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  (constraint 업데이트 건너뜀: %)', SQLERRM;
END $$;

\echo '';
\echo '========================================';
\echo '4. 마이그레이션 완료 - 최종 상태';
\echo '========================================';

-- 스키마 목록
\echo '';
\echo '--- 스키마 ---';
\dn

-- blog 스키마 테이블
\echo '';
\echo '--- blog 스키마 테이블 ---';
SELECT
    schemaname,
    tablename
FROM pg_tables
WHERE schemaname = 'blog'
ORDER BY tablename;

-- learning 스키마 테이블
\echo '';
\echo '--- learning 스키마 테이블 ---';
SELECT
    schemaname,
    tablename
FROM pg_tables
WHERE schemaname = 'learning'
ORDER BY tablename;

\echo '';
\echo '========================================';
\echo '✓ 깔끔한 마이그레이션 완료!';
\echo '========================================';
\echo '';
\echo '현재 데이터:';

SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM blog.posts) THEN 'blog.posts'
        ELSE NULL
    END as 테이블,
    CASE
        WHEN EXISTS (SELECT 1 FROM blog.posts) THEN (SELECT COUNT(*) FROM blog.posts)
        ELSE NULL
    END as 개수
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'blog' AND table_name = 'posts')
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM blog.projects) THEN 'blog.projects'
        ELSE NULL
    END,
    CASE
        WHEN EXISTS (SELECT 1 FROM blog.projects) THEN (SELECT COUNT(*) FROM blog.projects)
        ELSE NULL
    END
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'blog' AND table_name = 'projects')
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
FROM learning.baekjoon_solutions
UNION ALL
SELECT
    'learning.ai_chat_conversations',
    COUNT(*)
FROM learning.ai_chat_conversations;

\echo '';
\echo 'source_type별 통계:';
SELECT source_type, COUNT(*) as count
FROM learning.learning_artifacts
GROUP BY source_type
ORDER BY count DESC;

\echo '';
\echo '========================================';
\echo '다음 단계:';
\echo '1. .env 파일 설정';
\echo '2. python main.py 실행';
\echo '3. AI Chat 파일 수집 시작';
\echo '========================================';
