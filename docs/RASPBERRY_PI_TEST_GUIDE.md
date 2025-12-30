# 라즈베리파이 전체 테스트 가이드
## 다운로드 감지 → DB 저장까지 완전 테스트

---

## 🎯 목표
Claude Exporter로 다운로드한 `.md` 파일이 자동으로:
1. 감지되고
2. 파싱되고
3. DB에 저장되는 것을 확인!

---

## 📋 준비물
- ✅ 라즈베리파이 (PostgreSQL 실행 중)
- ✅ LearningETL 프로젝트 클론됨
- ✅ Python 3.8+ 설치됨

---

## 🚀 Step 1: SSH 접속 및 준비

```bash
# 1. SSH 접속
ssh user@raspberry-pi-ip

# 2. 프로젝트 디렉토리로 이동
cd /path/to/LearningETL

# 3. 최신 코드 받기
git fetch origin
git checkout claude/review-code-tests-alignment-DtRbe
git pull

# 4. 현재 브랜치 확인
git branch
# * claude/review-code-tests-alignment-DtRbe
```

---

## 🗑️ Step 2: 기존 Claude 데이터 삭제 (선택)

⚠️ **주의**: 기존 claude 데이터 1,114개가 모두 삭제됩니다!

```bash
# 마이그레이션 실행
bash scripts/clean-migrate-db.sh

# 입력 프롬프트:
# 계속하시겠습니까? (yes/no): yes
# PostgreSQL 비밀번호 입력: [비밀번호]
# 정말 삭제하시겠습니까? (DELETE 입력): DELETE

# 결과:
# ✓ claude_conversations 테이블 삭제
# ✓ claude 타입 artifacts 삭제 (1,114개)
# ✓ ai_chat_conversations 테이블 생성
```

---

## ⚙️ Step 3: .env 파일 설정

```bash
# .env 파일 생성
cp .env.example .env
nano .env
```

**편집할 내용:**
```bash
# GitHub (테스트는 false로)
COLLECT_GITHUB=false

# Baekjoon (테스트는 false로)
COLLECT_BAEKJOON=false

# AI Chat (테스트는 true로!)
COLLECT_AI_CHAT=true

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=my_blog
DB_USER=postgres
DB_PASSWORD=your_password
```

저장: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 📝 Step 4: 테스트용 Claude MD 파일 생성

```bash
# Downloads 디렉토리 확인/생성
mkdir -p ~/Downloads

# 테스트 파일 생성
cat > ~/Downloads/Claude-Test_React_Optimization-2025-12-30.md << 'EOF'
# React Performance Optimization

**Created:** 2025-12-30T10:30:00Z
**Updated:** 2025-12-30T11:45:00Z
**Link:** [Open in Claude](https://claude.ai/chat/test-abc123)

---

## Prompt:
React에서 렌더링 최적화는 어떻게 하나요?

## Response:
React 렌더링 최적화는 여러 방법이 있습니다.

### 1. React.memo()
컴포넌트를 메모이제이션합니다.

```javascript
const MemoizedComponent = React.memo(({ data }) => {
  return <div>{data.map(item => <Item key={item.id} {...item} />)}</div>;
});
```

### 2. useMemo()
계산 비용이 큰 값을 메모이제이션합니다.

```javascript
const expensiveValue = useMemo(() => {
  return heavyCalculation(input);
}, [input]);
```

## Prompt:
코드 분할도 도움이 되나요?

## Response:
네, React.lazy()를 사용하세요.

```typescript
import React, { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <HeavyComponent />
    </Suspense>
  );
}
```

---

*Powered by Claude Exporter*
EOF

# 파일 확인
ls -lh ~/Downloads/Claude-*.md
```

---

## 🎬 Step 5: main.py 실행 (전체 플로우 테스트!)

```bash
# 가상환경 활성화 (있다면)
source venv/bin/activate

# 의존성 설치 (처음이면)
pip install -r requirements.txt

# main.py 실행!
python main.py

# 기대 출력:
# [INFO] AI 채팅 파일 모니터 초기화
#   감시 폴더: /home/user/Downloads
#   저장 폴더: ./temp/ai_chat
# [INFO] AI 채팅 파일 감지: Claude-Test_React_Optimization-2025-12-30.md
# [INFO] [OK] AI 채팅 파일 수집: Claude-Test_React_Optimization-2025-12-30.md
# [INFO] 감지된 제공자: claude
# [INFO] 파일 저장: learning_artifacts/2025/12/30/ai_chat_claude/claude_React_Performance_Optimization_20251230.json
# [INFO] [DB] learning_artifacts 저장: id=1, React Performance Optimization
# [INFO] [DB] ai_chat_conversations 저장: id=1, provider=claude, title=React Performance Optimization
```

**실시간 로그 보기:**
```bash
# 별도 터미널에서
tail -f logs/ai_chat_export.log
tail -f logs/ai_chat_saver.log
```

---

## 🔍 Step 6: DB에 저장된 데이터 확인!

### 6-1. PostgreSQL 직접 확인
```bash
psql -d my_blog

# learning_artifacts 확인
SELECT
    id,
    artifact_date,
    source_type,
    title,
    tags
FROM learning.learning_artifacts
ORDER BY id DESC
LIMIT 5;
```

**기대 결과:**
```
 id | artifact_date | source_type    | title                         | tags
----+---------------+----------------+-------------------------------+--------------------------------
  1 | 2025-12-30    | ai_chat_claude | React Performance Optimization | {claude,ai_chat,javascript,typescript}
```

```sql
-- ai_chat_conversations 확인
SELECT
    id,
    provider,
    title,
    user_messages,
    assistant_messages,
    has_code,
    code_languages,
    code_blocks_count,
    link
FROM learning.ai_chat_conversations
ORDER BY id DESC
LIMIT 5;
```

**기대 결과:**
```
 id | provider | title                          | user_messages | assistant_messages | has_code | code_languages           | code_blocks_count | link
----+----------+--------------------------------+---------------+--------------------+----------+--------------------------+-------------------+--------------------------------
  1 | claude   | React Performance Optimization |             2 |                  2 | t        | {javascript,typescript}  |                 3 | https://claude.ai/chat/test-abc123
```

```sql
-- 종료
\q
```

### 6-2. CLI로 확인 (더 편함!)
```bash
# 통계 보기
python cli.py stats

# 기대 출력:
# ========================================
# 학습 통계
# ========================================
# 총 학습 활동: 1개
#
# 소스별 통계:
# - AI Chat (Claude): 1개
#
# 날짜별 통계:
# - 2025-12-30: 1개
```

```bash
# AI Chat 목록 보기
python cli.py list ai-chat

# 기대 출력:
# ========================================
# AI Chat 대화 목록
# ========================================
#
# [2025-12-30] Claude
# React Performance Optimization
# - 메시지: 4개 (사용자: 2, AI: 2)
# - 코드: 3개 블록 (javascript, typescript)
# - 링크: https://claude.ai/chat/test-abc123
```

```bash
# 특정 대화 상세보기
python cli.py show ai-chat 1

# 기대 출력:
# ========================================
# AI Chat 대화 상세
# ========================================
# ID: 1
# 제공자: claude
# 제목: React Performance Optimization
# 생성일: 2025-12-30 10:30:00
# 수정일: 2025-12-30 11:45:00
# 링크: https://claude.ai/chat/test-abc123
#
# 메시지:
# - 사용자 메시지: 2개
# - AI 메시지: 2개
#
# 코드:
# - 코드 블록: 3개
# - 언어: javascript, typescript
#
# 파일 경로:
# learning_artifacts/2025/12/30/ai_chat_claude/claude_React_Performance_Optimization_20251230.json
```

---

## 🎉 Step 7: 실제 Claude 대화 테스트!

이제 진짜 Claude 대화를 테스트해보세요:

### 7-1. Chrome Extension 설치
1. Chrome 웹스토어에서 "Claude Exporter" 검색
2. 설치

### 7-2. Claude에서 대화하기
1. https://claude.ai 접속
2. 새 대화 시작
3. 질문: "Python 비동기 프로그래밍 기초 알려줘"
4. 대화 완료

### 7-3. 다운로드
1. 대화 페이지에서 Extension 아이콘 클릭
2. "Export as Markdown" 클릭
3. ~/Downloads/Claude-Python_비동기_프로그래밍-2025-12-30.md 저장됨

### 7-4. 자동 감지 확인!
```bash
# main.py가 실행 중이라면 자동 감지!
# 로그 확인:
tail -f logs/ai_chat_export.log

# 출력:
# [INFO] AI 채팅 파일 감지: Claude-Python_비동기_프로그래밍-2025-12-30.md
# [INFO] [OK] AI 채팅 파일 수집
# [INFO] 감지된 제공자: claude
# [INFO] [DB] learning_artifacts 저장: id=2
# [INFO] [DB] ai_chat_conversations 저장: id=2
```

### 7-5. DB 확인
```bash
python cli.py list ai-chat

# 출력:
# [2025-12-30] Claude - React Performance Optimization
# [2025-12-30] Claude - Python 비동기 프로그래밍
```

---

## 🔧 트러블슈팅

### 파일이 감지되지 않을 때
```bash
# 1. Downloads 경로 확인
echo $HOME/Downloads
ls -la ~/Downloads/Claude-*.md

# 2. .env의 DOWNLOAD_DIR 확인
cat .env | grep DOWNLOAD_DIR

# 3. 수동으로 파일 처리
python -c "
from parse.ai_chat_parse import AIMarkdownParser
from storage.ai_chat_saver import AIChatSaver
from datetime import date

parser = AIMarkdownParser()
data = parser.parse_file('$HOME/Downloads/Claude-Test_React_Optimization-2025-12-30.md')

saver = AIChatSaver()
artifact_id = saver.save_ai_chat_artifact(data.to_dict(), date.today())
print(f'저장 완료! artifact_id={artifact_id}')
"
```

### DB 연결 실패
```bash
# PostgreSQL 실행 확인
sudo systemctl status postgresql

# 시작
sudo systemctl start postgresql

# .env 비밀번호 확인
cat .env | grep DB_PASSWORD
```

### 로그 확인
```bash
# 모든 로그 보기
ls -lh logs/

# AI Chat 관련 로그
tail -100 logs/ai_chat_export.log
tail -100 logs/ai_chat_parse.log
tail -100 logs/ai_chat_saver.log
```

---

## 📊 성공 확인 체크리스트

- [ ] 테스트 MD 파일 생성됨
- [ ] main.py 실행 시 파일 감지됨
- [ ] JSON 파일 저장됨 (learning_artifacts/...)
- [ ] DB에 learning_artifacts 레코드 생성
- [ ] DB에 ai_chat_conversations 레코드 생성
- [ ] CLI로 데이터 조회 가능
- [ ] 실제 Claude 대화 다운로드 & 자동 처리 성공

---

## 🎯 다음 단계

### Cron으로 자동화
```bash
bash scripts/setup-cron.sh

# 매일 자동 실행 설정
```

### ChatGPT, Gemini도 테스트
```bash
# ChatGPT Exporter, Gemini Exporter 설치
# 대화 다운로드 → 자동 감지 & 저장!
```

### 통계 확인
```bash
# 월별 통계
python cli.py stats --month 2025-12

# 언어별 통계
python -c "
import psycopg2
conn = psycopg2.connect(dbname='my_blog', user='postgres')
cur = conn.cursor()
cur.execute('''
    SELECT
        UNNEST(code_languages) as language,
        COUNT(*) as count
    FROM learning.ai_chat_conversations
    WHERE code_languages IS NOT NULL
    GROUP BY language
    ORDER BY count DESC
''')
for row in cur.fetchall():
    print(f'{row[0]}: {row[1]}개')
"
```

---

## 💡 팁

1. **실시간 모니터링**
   ```bash
   # tmux로 여러 창 띄우기
   tmux new -s learningetl
   # 창 1: main.py 실행
   # 창 2: tail -f logs/ai_chat_export.log
   # 창 3: psql 대기
   ```

2. **빠른 테스트**
   ```bash
   # 파일 생성하고 즉시 확인
   cat > ~/Downloads/Claude-Quick-Test.md << 'EOF'
   # Quick Test
   ## Prompt:
   Hello
   ## Response:
   Hi!
   EOF

   sleep 2
   python cli.py list ai-chat | tail -5
   ```

3. **JSON 파일 직접 보기**
   ```bash
   # 가장 최근 파일
   find learning_artifacts -name "*.json" -type f -printf '%T+ %p\n' | sort -r | head -1 | cut -d' ' -f2 | xargs cat | python -m json.tool
   ```

즐거운 테스트 되세요! 🚀
