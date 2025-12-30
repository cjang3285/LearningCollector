# AI Chat 저장 방식 상세 설명

## 📝 실제 코드 동작 흐름

### 1단계: 파일 감지 (export/ai_chat_export.py)
```python
# Downloads 폴더에서 감시
/Users/you/Downloads/
└── Claude-React_Optimization-2025-12-30.md  ← 감지!

# 처리 과정
AIMarkdownHandler.on_created()
    → is_ai_chat_file() 체크
    → process_file()
    → temp/ 폴더로 복사
    → callback 실행 (파싱)
```

### 2단계: 파싱 (parse/ai_chat_parse.py)
```python
# 마크다운 파일 분석
AIMarkdownParser.parse_file()
    ↓
# 추출 정보:
{
    "provider": "claude",                    # 파일명/내용으로 감지
    "title": "React 최적화 방법",           # 첫 번째 # 헤더
    "created_at": "2025-12-30T10:30:00Z",
    "updated_at": "2025-12-30T11:45:00Z",
    "link": "https://claude.ai/chat/abc123",
    "total_messages": 12,                   # Prompt/Response 쌍 개수
    "user_messages": 6,                     # ## Prompt: 개수
    "assistant_messages": 6,                # ## Response: 개수
    "has_code": true,                       # ``` 코드블록 존재 여부
    "code_blocks": [                        # 모든 코드블록 추출
        {
            "language": "javascript",
            "code": "const Component = React.memo(() => {...});",
            "lines": 15
        },
        {
            "language": "python",
            "code": "def optimize()...",
            "lines": 8
        }
    ],
    "messages": [                           # 전체 대화 내용
        {
            "role": "user",
            "content": "React에서 렌더링 최적화 어떻게 하나요?"
        },
        {
            "role": "assistant",
            "content": "React 렌더링 최적화는 여러 방법이 있습니다..."
        },
        ...
    ]
}
```

### 3단계: 파일 저장 (storage/ai_chat_saver.py)
```python
# 1. JSON 파일로 저장
learning_artifacts/
└── 2025/
    └── 12/
        └── 30/
            └── ai_chat_claude/
                └── claude_React_최적화_방법_20251230.json  ← 전체 대화 내용

# 내용:
{
    "provider": "claude",
    "title": "React 최적화 방법",
    "messages": [...전체 대화...],
    "code_blocks": [...모든 코드...],
    ...
}
```

### 4단계: DB 저장 (storage/ai_chat_saver.py)

#### 4-1. learning_artifacts 테이블
```sql
INSERT INTO learning.learning_artifacts (
    artifact_date,      -- '2025-12-30'
    source_type,        -- 'ai_chat_claude'
    title,              -- 'React 최적화 방법'
    summary,            -- 'Claude 대화: 12개 메시지'
    tags,               -- ['claude', 'ai_chat', 'javascript', 'python']
    storage_path,       -- 'learning_artifacts/2025/12/30/ai_chat_claude/...'
    metadata            -- JSONB: {"provider": "claude", "has_code": true, ...}
) RETURNING id;  -- artifact_id = 1455
```

#### 4-2. ai_chat_conversations 테이블
```sql
INSERT INTO learning.ai_chat_conversations (
    artifact_id,            -- 1455 (위에서 받은 ID)
    provider,               -- 'claude'
    title,                  -- 'React 최적화 방법'
    link,                   -- 'https://claude.ai/chat/abc123'
    user_messages,          -- 6
    assistant_messages,     -- 6
    has_code,               -- true
    conversation_path,      -- 'learning_artifacts/2025/12/30/...'
    code_languages,         -- ['javascript', 'python']  (배열!)
    code_blocks_count,      -- 2
    created_at,             -- '2025-12-30 10:30:00'
    updated_at              -- '2025-12-30 11:45:00'
);
```

## 💾 DB에 저장된 실제 데이터 예시

### learning.learning_artifacts
| id | artifact_date | source_type | title | tags | storage_path |
|----|--------------|-------------|-------|------|--------------|
| 1455 | 2025-12-30 | ai_chat_claude | React 최적화 방법 | {claude,ai_chat,javascript,python} | learning_artifacts/.../claude_React_최적화_방법_20251230.json |
| 1456 | 2025-12-30 | ai_chat_chatgpt | Python 비동기 프로그래밍 | {chatgpt,ai_chat,python} | learning_artifacts/.../chatgpt_Python_비동기_프로그래밍_20251230.json |
| 1457 | 2025-12-30 | ai_chat_gemini | 머신러닝 기초 | {gemini,ai_chat,python,tensorflow} | learning_artifacts/.../gemini_머신러닝_기초_20251230.json |

### learning.ai_chat_conversations
| id | artifact_id | provider | title | user_messages | assistant_messages | has_code | code_languages | code_blocks_count | link |
|----|-------------|----------|-------|---------------|-------------------|----------|----------------|-------------------|------|
| 1 | 1455 | claude | React 최적화 방법 | 6 | 6 | true | {javascript,python} | 2 | https://claude.ai/chat/abc123 |
| 2 | 1456 | chatgpt | Python 비동기 프로그래밍 | 4 | 4 | true | {python} | 5 | https://chat.openai.com/c/def456 |
| 3 | 1457 | gemini | 머신러닝 기초 | 8 | 8 | true | {python,tensorflow} | 3 | https://gemini.google.com/... |

## 🔍 쿼리 예시

### 코드가 포함된 Claude 대화만
```sql
SELECT
    a.title,
    c.user_messages + c.assistant_messages as total_messages,
    c.code_languages,
    c.code_blocks_count,
    c.link
FROM learning.learning_artifacts a
JOIN learning.ai_chat_conversations c ON a.id = c.artifact_id
WHERE c.provider = 'claude'
  AND c.has_code = true
ORDER BY a.artifact_date DESC;
```

**결과:**
| title | total_messages | code_languages | code_blocks_count | link |
|-------|----------------|----------------|-------------------|------|
| React 최적화 방법 | 12 | {javascript,python} | 2 | https://claude.ai/chat/abc123 |

### Python 관련 대화 (모든 AI)
```sql
SELECT
    c.provider,
    a.title,
    c.code_blocks_count,
    a.artifact_date
FROM learning.learning_artifacts a
JOIN learning.ai_chat_conversations c ON a.id = c.artifact_id
WHERE 'python' = ANY(c.code_languages)
ORDER BY a.artifact_date DESC;
```

**결과:**
| provider | title | code_blocks_count | artifact_date |
|----------|-------|-------------------|---------------|
| gemini | 머신러닝 기초 | 3 | 2025-12-30 |
| chatgpt | Python 비동기 프로그래밍 | 5 | 2025-12-30 |
| claude | React 최적화 방법 | 2 | 2025-12-30 |

### 월별 AI 대화 통계
```sql
SELECT
    DATE_TRUNC('month', a.artifact_date) as month,
    c.provider,
    COUNT(*) as conversations,
    SUM(c.user_messages + c.assistant_messages) as total_messages,
    SUM(c.code_blocks_count) as total_code_blocks
FROM learning.learning_artifacts a
JOIN learning.ai_chat_conversations c ON a.id = c.artifact_id
GROUP BY month, c.provider
ORDER BY month DESC, conversations DESC;
```

**결과:**
| month | provider | conversations | total_messages | total_code_blocks |
|-------|----------|---------------|----------------|-------------------|
| 2025-12-01 | claude | 45 | 680 | 120 |
| 2025-12-01 | chatgpt | 23 | 310 | 85 |
| 2025-12-01 | gemini | 12 | 180 | 40 |

## 🆚 기존 Claude vs 새 AI Chat 비교

### 기존 (claude_conversations) - 날릴 예정
```sql
-- 추정 구조 (실제와 다를 수 있음)
learning.claude_conversations
├── uuid                -- 고유 ID
├── name                -- 대화 이름
├── summary             -- 요약?
├── user_messages       -- 사용자 메시지 수
├── assistant_messages  -- AI 메시지 수
├── has_code           -- 코드 포함 여부
└── ...

문제점:
❌ Claude만 지원
❌ 코드 언어 정보 없음
❌ 원본 링크 없음
❌ 메시지 내용 없음 (아마도?)
```

### 새로운 (ai_chat_conversations)
```sql
learning.ai_chat_conversations
├── provider              -- claude, chatgpt, gemini
├── title                 -- 제목
├── link                  -- 원본 대화 링크 ✓
├── user_messages
├── assistant_messages
├── has_code
├── code_languages[]      -- 언어 배열 ✓
├── code_blocks_count     -- 코드 블록 개수 ✓
├── conversation_path     -- 전체 대화 JSON 경로 ✓
├── created_at           -- 생성 시각
└── updated_at           -- 수정 시각

장점:
✅ 3개 AI 모두 지원
✅ 코드 언어 추적
✅ 원본 링크 보존
✅ 전체 대화 JSON 저장
✅ 시간 정보 정확
```

## 📂 파일 구조

```
learning_artifacts/
└── 2025/
    └── 12/
        └── 30/
            ├── ai_chat_claude/
            │   ├── claude_React_최적화_방법_20251230.json
            │   └── claude_TypeScript_제네릭_20251230.json
            ├── ai_chat_chatgpt/
            │   └── chatgpt_Python_비동기_프로그래밍_20251230.json
            ├── ai_chat_gemini/
            │   └── gemini_머신러닝_기초_20251230.json
            ├── github/
            │   └── commit_abc123.json
            └── baekjoon/
                └── 1234.json
```

각 JSON 파일에는 **전체 대화 내용**이 저장됨:
```json
{
  "provider": "claude",
  "title": "React 최적화 방법",
  "created_at": "2025-12-30T10:30:00Z",
  "messages": [
    {
      "role": "user",
      "content": "React에서 렌더링 최적화 어떻게 하나요?"
    },
    {
      "role": "assistant",
      "content": "React 렌더링 최적화는 여러 방법이 있습니다. 1. useMemo()를 사용하여..."
    },
    ...전체 대화...
  ],
  "code_blocks": [
    {
      "language": "javascript",
      "code": "const Component = React.memo(() => {...});"
    }
  ]
}
```

## 🎯 핵심 차이점

| 항목 | 기존 (claude_conversations) | 새로운 (ai_chat_conversations) |
|------|---------------------------|------------------------------|
| 지원 AI | Claude만 | Claude + ChatGPT + Gemini |
| 원본 링크 | ❌ | ✅ |
| 코드 언어 | ❌ | ✅ (배열) |
| 전체 대화 | ❌ (아마도) | ✅ (JSON 파일) |
| 메시지 내용 검색 | ❌ | ✅ (파일에서) |
| 코드 재사용 | ❌ | ✅ (code_blocks) |
| 생성/수정 시각 | ? | ✅ |
