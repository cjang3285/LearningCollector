# AI Chat Markdown Integration

## 개요

Claude, ChatGPT, Gemini의 브라우저 확장 프로그램이 내보낸 마크다운 파일을 자동으로 파싱하여 DB에 저장하는 기능입니다.

## 지원되는 AI 제공자

- **Claude Exporter** - Claude 대화 내보내기
- **ChatGPT Exporter** - ChatGPT 대화 내보내기
- **Gemini Exporter** - Gemini 대화 내보내기

## 설치

### 1. 의존성 설치

```bash
pip install watchdog
```

### 2. 데이터베이스 마이그레이션

`ai_chat_conversations` 테이블을 생성해야 합니다:

```bash
psql -U postgres -d my_blog -f docs/migration_ai_chat_conversations.sql
```

또는 PostgreSQL 클라이언트에서 직접 실행:

```sql
-- docs/migration_ai_chat_conversations.sql 참조
CREATE TABLE learning.ai_chat_conversations ( ... );
```

## 사용법

### 1. 마크다운 파일 직접 제공

```bash
# 단일 파일
python main.py --ai-chat ~/Downloads/Claude-Conversation-Export.md

# 여러 파일
python main.py --ai-chat \
  ~/Downloads/Claude-Export1.md \
  ~/Downloads/ChatGPT-Export2.md \
  ~/Downloads/Gemini-Export3.md

# 날짜 지정
python main.py --ai-chat ~/Downloads/*.md --date 2025-12-28
```

### 2. 다운로드 폴더 자동 스캔

```bash
# 다운로드 폴더에서 AI 채팅 파일 자동 검색
python main.py --ai-chat-scan

# GitHub + AI Chat 동시 수집
python main.py --ai-chat-scan
```

### 3. 실시간 파일 감시 (백그라운드)

다운로드 폴더를 감시하여 새로운 AI 채팅 마크다운이 다운로드되면 자동으로 수집:

```bash
# 실시간 감시 시작
python export/ai_chat_export.py --watch

# 또는 collector로 직접 실행
python collectors/ai_chat_collector.py --watch
```

### 4. 개별 모듈 테스트

#### 파서 테스트

```bash
# 마크다운 파일 파싱만 테스트
python parse/ai_chat_parse.py ~/Downloads/Claude-Export.md
```

출력 예시:
```
제공자: claude
제목: Service Expansion Priority
생성일: 2025-01-04T01:06:27.296Z
수정일: 2025-01-04T01:06:27.296Z
메시지: 4개 (사용자: 2, AI: 2)
코드 블록: 0개

첫 메시지 미리보기:
[user] 현재 우리가 운영중인 서비스는...
```

#### 수집기 테스트

```bash
# 파일 리스트로 수집
python collectors/ai_chat_collector.py file1.md file2.md

# 다운로드 폴더 스캔
python collectors/ai_chat_collector.py --scan

# 실시간 감시
python collectors/ai_chat_collector.py --watch
```

## 마크다운 형식

### Claude Exporter 형식

```markdown
# Service Expansion Priority

**Created:** 2025-01-04T01:06:27.296Z
**Updated:** 2025-01-04T01:06:27.296Z
**Link:** https://claude.ai/chat/...

## Prompt:

현재 우리가 운영중인 서비스는...

## Response:

서비스 확장 우선순위를 분석하겠습니다...

---

*Powered by Claude Exporter*
```

### ChatGPT Exporter 형식

```markdown
# Algorithm Problem Solving

**Created:** 2025-01-04T00:01:02.000Z
**Updated:** 2025-01-04T00:15:30.000Z
**User:** user@example.com
**Link:** https://chatgpt.com/c/...

## Prompt:

이 알고리즘 문제를 풀어주세요...

## Response:

이 문제는 동적 프로그래밍으로 해결할 수 있습니다...

```python
def solution(n):
    dp = [0] * (n + 1)
    return dp[n]
```

---

*Powered by ChatGPT Exporter*
```

### Gemini Exporter 형식

```markdown
# GitHub Blog Project

## Prompt:

GitHub 블로그 프로젝트 구조를 설계해주세요...

## Response:

다음과 같은 구조를 제안합니다...

---

*Powered by Gemini Exporter*
```

## 데이터베이스 스키마

### learning_artifacts

모든 AI 채팅 대화는 `learning_artifacts` 테이블에 메타데이터가 저장됩니다:

```sql
INSERT INTO learning.learning_artifacts (
    artifact_date,
    source_type,      -- 'ai_chat_claude', 'ai_chat_chatgpt', 'ai_chat_gemini'
    title,
    summary,
    tags,             -- ['claude', 'ai_chat', 'python', 'javascript']
    storage_path,
    metadata
) VALUES ( ... );
```

### ai_chat_conversations

AI 채팅 전용 상세 정보:

```sql
CREATE TABLE learning.ai_chat_conversations (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES learning.learning_artifacts(id),
    provider VARCHAR(50) NOT NULL,  -- 'claude', 'chatgpt', 'gemini'
    title TEXT NOT NULL,
    link TEXT,
    user_messages INTEGER,
    assistant_messages INTEGER,
    has_code BOOLEAN,
    conversation_path TEXT,
    code_languages TEXT[],          -- ['python', 'javascript']
    code_blocks_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT NOW()
);
```

## 파일 저장 구조

마크다운 원본은 JSON으로 변환되어 다음 경로에 저장됩니다:

```
learning_artifacts/
├── 2025/
│   └── 12/
│       └── 29/
│           ├── ai_chat_claude/
│           │   └── claude_Service_Expansion_Priority_20251229.json
│           ├── ai_chat_chatgpt/
│           │   └── chatgpt_Algorithm_Problem_Solving_20251229.json
│           └── ai_chat_gemini/
│               └── gemini_GitHub_Blog_Project_20251229.json
```

## 제공자 감지 로직

파일명 또는 내용에서 AI 제공자를 자동으로 감지:

1. **파일명 기반 감지**
   - `Claude-*.md` → claude
   - `ChatGPT-*.md` → chatgpt
   - `Gemini-*.md` → gemini

2. **Footer 기반 감지** (fallback)
   - `Powered by Claude Exporter` → claude
   - `Powered by ChatGPT Exporter` → chatgpt
   - `Powered by Gemini Exporter` → gemini

## 코드 블록 추출

마크다운의 코드 블록을 자동으로 추출하여 저장:

```python
# 코드 블록 예시
{
    'language': 'python',
    'code': 'def hello():\n    print("world")',
    'lines': 2
}
```

프로그래밍 언어는 태그로 자동 추가되어 검색 가능:

```sql
SELECT * FROM learning.learning_artifacts
WHERE 'python' = ANY(tags) AND source_type LIKE 'ai_chat_%';
```

## 통합 수집 예시

모든 소스를 한 번에 수집:

```bash
python main.py \
  --date 2025-12-29 \
  --claude-zip ~/Downloads/conversations.zip \
  --ai-chat ~/Downloads/Claude-*.md ~/Downloads/ChatGPT-*.md \
  --ai-chat-scan
```

출력:
```
============================================================
Learning Artifacts ETL - 2025-12-29
============================================================

[GitHub] 데이터 수집 시작...
[OK] 총 3개 커밋 수집 완료

[Claude] 데이터 수집 시작...
[OK] Claude 대화 5개 저장 완료

[AI Chat] 마크다운 파일 수집 시작...
파일 수: 8개
[1/2] 8개 파일 파싱...
파싱 완료: {'claude': 4, 'chatgpt': 3, 'gemini': 1}
[2/2] DB에 저장...
[OK] AI 채팅 대화 8개 저장 완료

[Baekjoon] 데이터 수집 시작...
[OK] 백준 문제 2개 저장 완료

============================================================
수집 완료
============================================================
총 아티팩트: 18개
  - GitHub: 3개
  - Claude: 5개
  - AI Chat: 8개
  - 백준: 2개
============================================================
```

## 문제 해결

### 1. 파일이 감지되지 않음

**문제:** 다운로드 폴더에 파일이 있는데 스캔되지 않음

**해결:**
```bash
# 파일명 확인
ls ~/Downloads/Claude-*.md
ls ~/Downloads/ChatGPT-*.md
ls ~/Downloads/Gemini-*.md

# 파일명이 다른 경우 직접 지정
python main.py --ai-chat ~/Downloads/my-conversation.md
```

### 2. 제공자 감지 실패

**문제:** `provider: unknown`으로 표시됨

**원인:** 파일명과 내용 모두에서 제공자를 찾을 수 없음

**해결:** 마크다운 파일의 footer를 확인:
```markdown
---

*Powered by Claude Exporter*
```

### 3. 데이터베이스 오류

**문제:** `relation "learning.ai_chat_conversations" does not exist`

**해결:** 마이그레이션 실행
```bash
psql -U postgres -d my_blog -f docs/migration_ai_chat_conversations.sql
```

### 4. 코드 블록이 추출되지 않음

**문제:** `code_blocks_count: 0`

**확인:** 마크다운 코드 블록 형식
```markdown
\`\`\`python
def hello():
    print("world")
\`\`\`
```

## 향후 개선 사항

- [ ] 다중 언어 대화 지원 (한국어, 영어 감지)
- [ ] 대화 주제 자동 분류 (AI 분석)
- [ ] 중복 대화 감지 및 제거
- [ ] 마크다운 → HTML 변환 (블로그 포스트)
- [ ] 대화 검색 API (Elasticsearch)

## 관련 파일

- `parse/ai_chat_parse.py` - 마크다운 파서
- `export/ai_chat_export.py` - 파일 감시 및 수집
- `collectors/ai_chat_collector.py` - 통합 수집기
- `storage/ai_chat_saver.py` - DB 저장
- `docs/migration_ai_chat_conversations.sql` - DB 마이그레이션
- `main.py` - 메인 진입점
