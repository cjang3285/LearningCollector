-- LearningETL 정확한 DB 스키마
-- 실제 코드가 기대하는 스키마 정의

-- learning 스키마 생성
CREATE SCHEMA IF NOT EXISTS learning;

-- 1. learning_artifacts (메인 메타데이터 테이블)
CREATE TABLE IF NOT EXISTS learning.learning_artifacts (
    id SERIAL PRIMARY KEY,
    artifact_date DATE NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    title TEXT,
    summary TEXT,
    tags TEXT[],
    storage_path TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artifacts_date ON learning.learning_artifacts(artifact_date);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON learning.learning_artifacts(source_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_tags ON learning.learning_artifacts USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_artifacts_created ON learning.learning_artifacts(created_at);

-- 2. github_commits (GitHub 커밋)
CREATE TABLE IF NOT EXISTS learning.github_commits (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning.learning_artifacts(id) ON DELETE CASCADE,
    repo VARCHAR(255) NOT NULL,
    repo_owner VARCHAR(255),
    sha VARCHAR(40) UNIQUE NOT NULL,
    message TEXT,
    commit_date TIMESTAMP,
    url TEXT,
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    files JSONB,
    diff_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_commits_sha ON learning.github_commits(sha);
CREATE INDEX IF NOT EXISTS idx_commits_repo ON learning.github_commits(repo);
CREATE INDEX IF NOT EXISTS idx_commits_date ON learning.github_commits(commit_date);
CREATE INDEX IF NOT EXISTS idx_commits_artifact ON learning.github_commits(artifact_id);

-- 3. ai_chat_conversations (AI 채팅)
CREATE TABLE IF NOT EXISTS learning.ai_chat_conversations (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning.learning_artifacts(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_ai_chat_provider ON learning.ai_chat_conversations(provider);
CREATE INDEX IF NOT EXISTS idx_ai_chat_created ON learning.ai_chat_conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_chat_artifact ON learning.ai_chat_conversations(artifact_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_languages ON learning.ai_chat_conversations USING GIN(code_languages);

-- 4. baekjoon_solutions (백준 문제 풀이)
CREATE TABLE IF NOT EXISTS learning.baekjoon_solutions (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning.learning_artifacts(id) ON DELETE CASCADE,
    problem_number INTEGER NOT NULL,
    title VARCHAR(255),
    tier VARCHAR(50),
    category VARCHAR(100),
    tags TEXT[],
    language VARCHAR(50),
    code TEXT,
    memory_kb INTEGER,
    time_ms INTEGER,
    solved_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_baekjoon_number ON learning.baekjoon_solutions(problem_number);
CREATE INDEX IF NOT EXISTS idx_baekjoon_tier ON learning.baekjoon_solutions(tier);
CREATE INDEX IF NOT EXISTS idx_baekjoon_date ON learning.baekjoon_solutions(solved_date);
CREATE INDEX IF NOT EXISTS idx_baekjoon_artifact ON learning.baekjoon_solutions(artifact_id);
CREATE INDEX IF NOT EXISTS idx_baekjoon_tags ON learning.baekjoon_solutions USING GIN(tags);

-- 권한 부여 (DB 설정 후 실행)
-- GRANT ALL ON SCHEMA learning TO learning_user;
-- GRANT ALL ON ALL TABLES IN SCHEMA learning TO learning_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA learning TO learning_user;
