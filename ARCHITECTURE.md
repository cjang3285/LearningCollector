# Learning Artifacts 아키텍처 설계

## 📊 개념: Learning Artifact (학습 아티팩트)

**Learning Artifact**는 모든 학습 활동의 산출물과 흔적을 의미합니다.

### 왜 "Artifact"인가?

- **소프트웨어 개발**: 빌드 산출물, 컴파일 결과물
- **학습**: 코드, 대화, 문제풀이, 필기 등 **학습의 증거**
- **확장성**: 다양한 소스를 하나의 개념으로 통합

### 수집 소스 (현재 + 계획)

| 소스 | 상태 | 설명 |
|------|------|------|
| GitHub | ✅ 구현 | 커밋, 코드 변경사항 |
| Claude | ✅ 구현 | AI 대화 내용 |
| 백준 | ✅ 구현 | 알고리즘 문제 풀이 |
| GoodNotes | 📋 계획 | iPad 필기 (PDF → OCR) |
| Notion | 📋 계획 | 학습 노트 |
| Browser History | 📋 계획 | 학습 관련 웹페이지 |
| YouTube | 📋 계획 | 시청 기록 |

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    데이터 수집 레이어                          │
├─────────────────────────────────────────────────────────────┤
│  Export 모듈                                                 │
│  ├── GitHub API        (REST API)                           │
│  ├── Claude Export     (Selenium 자동화)                     │
│  ├── 백준 크롤링        (Selenium + solved.ac API)           │
│  └── [미래] GoodNotes  (PDF 파싱 + OCR)                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    데이터 파싱 레이어                          │
├─────────────────────────────────────────────────────────────┤
│  Parse 모듈                                                  │
│  ├── 구조화 (Dataclass)                                      │
│  ├── 코드 분석 (언어 감지, 주석 추출)                         │
│  └── 메타데이터 생성                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  저장 레이어 (하이브리드)                      │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL (메타데이터)      │  파일 시스템 (원본 데이터)    │
│  ├── learning_artifacts       │  learning_artifacts/         │
│  ├── github_commits           │  ├── 2025/12/26/            │
│  ├── claude_conversations     │  │   ├── github/            │
│  ├── baekjoon_solutions       │  │   ├── claude/            │
│  └── blog_posts               │  │   └── baekjoon/          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    AI 분석 레이어                             │
├─────────────────────────────────────────────────────────────┤
│  Claude API                                                  │
│  ├── 학습 주제 추출                                           │
│  ├── 핵심 포인트 요약                                         │
│  └── 블로그 포스트 초안 생성                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  블로그 포스팅 레이어                          │
├─────────────────────────────────────────────────────────────┤
│  ├── 리뷰 대시보드 (웹 UI)                                    │
│  ├── 수정/승인                                                │
│  └── 자동 발행 (블로그 API)                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 💾 저장 전략: 하이브리드 접근

### 원칙

```
작고 자주 쿼리하는 데이터 → PostgreSQL
크고 가끔 읽는 데이터 → 파일 시스템
```

### 저장 규칙

| 데이터 | 크기 | 저장 위치 | 예시 |
|--------|------|-----------|------|
| 메타데이터 | < 10KB | PostgreSQL | 날짜, 제목, 요약, 통계 |
| 짧은 텍스트 | < 100KB | PostgreSQL TEXT/JSONB | 코드 스니펫, 짧은 대화 |
| 긴 텍스트 | > 100KB | 파일 (.json, .txt) | 전체 대화 로그, diff |
| 바이너리 | > 1MB | 파일 (.pdf, .png) | PDF, 이미지 |

### 파일 구조

```
learning_artifacts/
├── 2025/
│   └── 12/
│       └── 26/
│           ├── github/
│           │   ├── commit_abc123.json          # 전체 커밋 데이터
│           │   └── files/
│           │       └── main.py                 # 변경된 파일 원본
│           ├── claude/
│           │   └── conversation_uuid.json      # 전체 대화 내용
│           ├── baekjoon/
│           │   ├── problem_1234.py             # 제출 코드
│           │   └── problem_1234_analysis.json  # 분석 결과
│           └── goodnotes/
│               ├── notebook_1.pdf              # 원본 PDF
│               ├── notebook_1_ocr.txt          # OCR 텍스트
│               └── images/
│                   ├── page_001.png
│                   └── page_002.png
```

### PostgreSQL 테이블 설계

핵심 테이블:
1. **`learning_artifacts`** - 모든 학습 활동의 메타데이터
2. **`github_commits`** - GitHub 커밋 (artifact에 연결)
3. **`claude_conversations`** - Claude 대화 (artifact에 연결)
4. **`baekjoon_solutions`** - 백준 풀이 (artifact에 연결)
5. **`goodnotes_notes`** - GoodNotes 필기 (미래)
6. **`blog_posts`** - 생성된 블로그 포스트

---

## 🔍 데이터 흐름

### 1. 수집 단계

```python
# export/github_export.py
exporter = GitHubExporter()
commits = exporter.export_today()  # GitHub API 호출
```

### 2. 파싱 단계

```python
# parse/github_parse.py
parser = GitHubParser()
parsed = parser.parse_commits(commits)  # 구조화
```

### 3. 저장 단계

```python
# storage/artifact_saver.py (미래 구현)
saver = ArtifactSaver()

# 1) 파일 시스템에 원본 저장
file_path = saver.save_to_file(parsed, 'github')
# → learning_artifacts/2025/12/26/github/commit_abc123.json

# 2) PostgreSQL에 메타데이터 저장
artifact_id = saver.save_to_db({
    'artifact_date': '2025-12-26',
    'source_type': 'github',
    'title': commit.message,
    'storage_path': file_path,
    'metadata': {...}
})
```

### 4. 조회/분석 단계

```sql
-- 최근 7일 활동 조회
SELECT * FROM learning_artifacts
WHERE artifact_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY artifact_date DESC;

-- Python 관련 커밋만
SELECT a.*, g.repo, g.message
FROM learning_artifacts a
JOIN github_commits g ON a.id = g.artifact_id
WHERE 'python' = ANY(a.tags);
```

---

## 🎯 확장성 고려사항

### 새로운 소스 추가 방법

1. **Export 모듈 작성** (`export/goodnotes_export.py`)
2. **Parse 모듈 작성** (`parse/goodnotes_parse.py`)
3. **DB 테이블 추가** (선택, 필요시)
4. **config 업데이트** (환경변수 추가)

### 예시: GoodNotes 추가

```python
# export/goodnotes_export.py
class GoodNotesExporter:
    def export_pdfs(self, source_dir):
        # iPad에서 PDF 가져오기
        pass

# parse/goodnotes_parse.py
class GoodNotesParser:
    def parse_pdf(self, pdf_path):
        # OCR 수행
        # 이미지 추출
        pass
```

---

## 🔐 보안 고려사항

### 민감 정보 관리

1. **Git에 절대 올리지 말 것**:
   - API 토큰 (`.env`, `config/secrets.py`)
   - 쿠키 파일 (`.pkl`, `.json`)
   - 개인 학습 데이터 (`learning_artifacts/`)

2. **쿠키란?**
   - 웹사이트 로그인 상태를 유지하는 데이터
   - Claude, 백준은 API가 없어 Selenium으로 자동화
   - 쿠키 저장으로 매번 로그인 불필요

3. **환경변수 사용**:
   ```bash
   export GITHUB_TOKEN="ghp_..."
   export BAEKJOON_HANDLE="andy1692"
   ```

4. **`.gitignore` 필수**:
   - 모든 민감 정보 제외
   - temp, logs, learning_artifacts 제외

---

## 📈 성능 최적화

### PostgreSQL 인덱스

- `artifact_date` - 날짜별 조회 (가장 많이 사용)
- `source_type` - 소스별 필터링
- `tags` - GIN 인덱스 (배열 검색)
- `metadata` - GIN 인덱스 (JSONB 검색)

### 파일 압축 (미래)

- 오래된 데이터 자동 압축 (gzip)
- S3 Glacier로 아카이빙

---

## 🚀 다음 단계

1. **나머지 모듈 완성** (Claude, 백준)
2. **DB 저장 모듈** 구현
3. **AI 분석 모듈** (Claude API)
4. **블로그 포스트 생성기**
5. **리뷰 대시보드** (웹 UI)
6. **GoodNotes OCR** 통합
