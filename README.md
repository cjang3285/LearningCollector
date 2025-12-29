# Learning Artifacts ETL Pipeline

모든 학습 활동(GitHub 커밋, AI 채팅, 백준 문제풀이)을 자동으로 수집하여 PostgreSQL DB에 저장하는 ETL 파이프라인입니다.

## 🎯 주요 기능

- **GitHub 커밋 수집**: REST API로 커밋 메타데이터 및 diff 수집
- **AI 채팅 수집**: Claude, ChatGPT, Gemini 마크다운 자동 파싱
- **백준 풀이 수집**: TIL 레포에서 크롬 확장 프로그램이 푸시한 문제 풀이 수집
- **PostgreSQL 저장**: 모든 데이터를 구조화하여 DB 저장
- **자동화**: cron job 또는 스케줄러로 일일 자동 수집

## 📋 전제조건

- Python 3.8+
- PostgreSQL 12+
- GitHub Personal Access Token
- 백준 TIL 레포 (선택)
- AI 채팅 브라우저 확장 프로그램 (선택)

## 🚀 빠른 시작

### 1. 설치

```bash
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```bash
# GitHub 설정
GITHUB_TOKEN=ghp_your_token_here
GITHUB_USERNAME=your_username

# 백준 TIL 설정 (선택)
BAEKJOON_HANDLE=your_handle
BAEKJOON_TIL_REPO=Baekjoon_solutions

# PostgreSQL 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=my_blog
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. 데이터베이스 마이그레이션

```bash
# DB 스키마 생성
psql -U postgres -d my_blog -f docs/migration_ai_chat_conversations.sql
```

### 4. 실행

```bash
# GitHub + 백준 수집
python main.py

# AI 채팅 자동 스캔
python main.py --ai-chat-scan

# 특정 날짜 수집
python main.py --date 2025-12-28

# 첫 Claude 마이그레이션 (모든 대화)
python main.py --claude-zip ~/Downloads/conversations.zip --all
```

## 📚 데이터 소스

### 1️⃣ GitHub 커밋

**방식**: GitHub REST API
**수집 내용**:
- 커밋 메타데이터 (SHA, 메시지, 날짜)
- 변경된 파일 목록
- Diff 및 패치
- 코드 주석

### 2️⃣ AI 채팅 (Claude, ChatGPT, Gemini)

**방식**: 브라우저 확장 프로그램 → 마크다운 내보내기
**수집 내용**:
- 대화 제목 및 메타데이터
- 사용자/AI 메시지 쌍
- 코드 블록 (언어별)
- 생성/수정 날짜

**지원 확장 프로그램**:
- [Claude Exporter](https://chromewebstore.google.com/)
- [ChatGPT Exporter](https://chromewebstore.google.com/)
- [Gemini Chat Exporter](https://chromewebstore.google.com/)

### 3️⃣ 백준 문제풀이

**방식**: TIL 레포 (GitHub API)
**수집 내용**:
- 문제 번호, 제목, 티어
- 제출 코드 및 언어
- 메모리/시간 성능
- 문제 태그 및 설명

**전제조건**:
백준 자동 커밋 크롬 확장 프로그램 설치 필요

## 📁 프로젝트 구조

```
LearningETL/
├── main.py                     # 메인 진입점
├── requirements.txt            # Python 패키지
│
├── config/
│   └── settings.py            # 환경 설정
│
├── export/                     # 데이터 수집
│   ├── github_export.py
│   ├── baekjoon_export.py
│   └── ai_chat_export.py      # 파일 감시
│
├── parse/                      # 데이터 파싱
│   ├── github_parse.py
│   ├── baekjoon_parse.py
│   ├── ai_chat_parse.py
│   └── claude_migration_parse.py
│
├── collectors/                 # 통합 수집기
│   ├── github_collector.py
│   ├── baekjoon_collector.py
│   ├── ai_chat_collector.py
│   └── claude_migration_collector.py
│
├── storage/                    # 데이터 저장
│   ├── base_saver.py
│   ├── github_saver.py
│   ├── baekjoon_saver.py
│   └── ai_chat_saver.py
│
└── docs/                       # 문서
    ├── ARCHITECTURE.md
    └── AI_CHAT_INTEGRATION.md
```

## 💾 데이터베이스 스키마

### learning_artifacts (통합 메타데이터)

모든 학습 활동의 중앙 테이블

```sql
- id: 고유 ID
- artifact_date: 학습 날짜
- source_type: github, ai_chat_claude, baekjoon 등
- title: 제목
- tags: 태그 배열
- storage_path: 파일 저장 경로
- metadata: JSONB 추가 정보
```

### 소스별 상세 테이블

- `github_commits`: GitHub 커밋 상세
- `ai_chat_conversations`: AI 채팅 대화
- `baekjoon_solutions`: 백준 문제 풀이

## 🔧 고급 사용법

### AI 채팅 실시간 감시

다운로드 폴더를 감시하여 새 마크다운 파일 자동 수집:

```bash
python export/ai_chat_export.py --watch
```

### 백준 코드 직접 지정

```bash
python export/baekjoon_export.py
```

### 개별 모듈 테스트

```bash
# 파서 테스트
python parse/ai_chat_parse.py ~/Downloads/Claude-Export.md

# 수집기 테스트
python collectors/ai_chat_collector.py --scan
```

## 📊 사용 예시

### 일상적 사용 (매일 자동 수집)

```bash
# crontab -e
0 23 * * * cd /path/to/LearningETL && python main.py --ai-chat-scan
```

### 첫 설정 시 (전체 데이터 마이그레이션)

```bash
# Claude 전체 대화 마이그레이션
python main.py --claude-zip conversations.zip --all

# 이후부터는 마크다운으로 일일 수집
python main.py --ai-chat-scan
```

## 🛠️ 문제 해결

### GitHub API Rate Limit

```bash
# 토큰 확인
echo $GITHUB_TOKEN

# Rate limit 확인
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

### AI 채팅 파일 감지 안 됨

1. 파일명 확인: `Claude-`, `ChatGPT-`, `Gemini-`로 시작하는지
2. 확장자 확인: `.md` 파일인지
3. 다운로드 폴더 확인: `~/Downloads`가 맞는지

### 백준 TIL 레포 연결 실패

```bash
# TIL 레포 확인
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$GITHUB_USERNAME/Baekjoon_solutions
```

## 📖 추가 문서

- [시스템 아키텍처](docs/ARCHITECTURE.md)
- [AI Chat 통합 가이드](docs/AI_CHAT_INTEGRATION.md)

## 🤝 기여

Issues와 Pull Requests를 환영합니다!

## 📄 라이선스

MIT License

## 🔗 관련 프로젝트

- [Claude Exporter](https://github.com/)
- [백준 자동 커밋](https://github.com/)
