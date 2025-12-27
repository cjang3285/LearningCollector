# Learning Artifacts ETL Pipeline

모든 학습 활동(GitHub, Claude, 백준)을 자동으로 수집하여 PostgreSQL DB에 저장하고, 향후 블로그 포스팅으로 변환하는 자동화 파이프라인

## ✨ 주요 기능

- **GitHub 커밋 수집**: GitHub API로 모든 저장소의 커밋 자동 수집
- **Claude 대화 수집**: 수동 다운로드한 ZIP 파일 파싱
- **백준 문제풀이 수집**: solved.ac API + Selenium으로 제출 코드 크롤링
- **PostgreSQL 자동 저장**: 구조화된 데이터를 DB에 저장
- **날짜별 필터링**: 특정 날짜의 학습 활동만 수집

## 📋 시스템 요구사항

### 필수 소프트웨어

- Python 3.8+
- PostgreSQL 12+
- Chromium/Chrome (백준 크롤링용)

### Python 패키지

```bash
pip install -r requirements.txt
```

주요 패키지:
- `psycopg2-binary`: PostgreSQL 연결
- `requests`: GitHub/solved.ac API
- `selenium`: 웹 크롤링 (백준)

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 환경변수 설정
export GITHUB_TOKEN="ghp_your_token_here"
export GITHUB_USERNAME="your_username"
export BAEKJOON_HANDLE="your_handle"

# PostgreSQL 설정
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="my_blog"
export DB_USER="postgres"
export DB_PASSWORD="your_password"
```

또는 `.env` 파일 생성:

```bash
cp .env.example .env
# .env 파일 편집
```

### 2. 데이터베이스 스키마 생성

```bash
# PostgreSQL에 접속하여 스키마 생성
psql -U postgres -d my_blog -f schema.sql
```

### 3. 실행

#### GitHub + 백준 자동 수집

```bash
python main.py
```

#### Claude 포함 전체 수집

```bash
# 1. claude.ai에서 수동으로 Export → ZIP 다운로드
# 2. ZIP 경로와 함께 실행
python main.py --claude-zip ~/Downloads/conversations.zip
```

#### 특정 날짜 수집

```bash
python main.py --date 2025-12-26 --claude-zip conversations.zip
```

## 📁 프로젝트 구조

```
LearningConvertedToPost/
├── main.py                     # 메인 진입점
├── config/                     # 설정
│   └── settings.py
├── export/                     # 데이터 수집
│   ├── github_export.py
│   └── baekjoon_export.py
├── parse/                      # 데이터 파싱
│   ├── github_parse.py
│   ├── claude_parse.py
│   └── baekjoon_parse.py
├── collectors/                 # 통합 수집기
│   ├── github_collector.py
│   ├── claude_collector.py
│   └── baekjoon_collector.py
├── storage/                    # 데이터 저장
│   ├── base_saver.py
│   ├── github_saver.py
│   ├── claude_saver.py
│   └── baekjoon_saver.py
├── tests/                      # 테스트
└── docs/                       # 문서
    └── ARCHITECTURE.md         # 상세 아키텍처
```

## 🔧 설정

### GitHub Token 발급

1. GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. 권한 선택: `repo`, `read:user`
4. 환경변수에 설정: `export GITHUB_TOKEN="ghp_..."`

### 백준 설정 (선택사항)

백준 크롤링은 로그인이 필요합니다. 최초 1회 설정:

```bash
python -m export.baekjoon_export --setup
# 브라우저가 열리면 수동 로그인
# 로그인 후 Enter 키 입력 → 쿠키 저장
```

## 📊 데이터베이스 구조

### 주요 테이블

- **learning_artifacts**: 모든 학습 활동의 메타데이터
- **github_commits**: GitHub 커밋 상세 정보
- **claude_conversations**: Claude 대화 내용
- **baekjoon_solutions**: 백준 문제풀이 코드

상세 스키마는 [ARCHITECTURE.md](ARCHITECTURE.md) 참고

## 🎯 사용 예시

### 1. 오늘 학습 활동 수집

```bash
python main.py
```

결과:
```
============================================================
Learning Artifacts ETL - 2025-12-27
============================================================

[GitHub] 데이터 수집 시작...
  ✅ 8개 커밋 수집

[Claude] ZIP 파일이 제공되지 않아 건너뜀

[Baekjoon] 데이터 수집 시작...
  ✅ 2개 문제 풀이 수집

============================================================
수집 완료
============================================================
총 아티팩트: 10개
  - GitHub: 8개
  - Claude: 0개
  - 백준: 2개
============================================================
```

### 2. 특정 기간 분석

```python
# Python 스크립트에서 사용
from collectors.github_collector import GitHubCollector
from datetime import date

collector = GitHubCollector()
result = collector.collect(target_date=date(2025, 12, 26))

print(f"커밋 수: {result['commits_count']}")
print(f"저장된 ID: {result['artifact_ids']}")
```

### 3. DB에서 조회

```sql
-- 최근 7일 활동
SELECT * FROM learning_artifacts
WHERE artifact_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY artifact_date DESC;

-- Python 관련 커밋만
SELECT a.*, g.repo, g.message
FROM learning_artifacts a
JOIN github_commits g ON a.id = g.artifact_id
WHERE 'python' = ANY(a.tags);

-- 오늘 푼 백준 문제
SELECT * FROM baekjoon_solutions
WHERE DATE(created_at) = CURRENT_DATE;
```

## 🤖 자동화 (Cron)

매일 밤 11시 50분에 자동 실행:

```bash
crontab -e
```

```cron
# Learning Artifacts ETL
50 23 * * * cd /home/user/LearningConvertedToPost && /usr/bin/python3 main.py >> /var/log/learning-etl.log 2>&1
```

## 🐛 문제 해결

### 1. PostgreSQL 연결 오류

```bash
# PostgreSQL 실행 여부 확인
sudo systemctl status postgresql

# DB 생성 여부 확인
psql -U postgres -l | grep my_blog
```

### 2. GitHub Rate Limit

```python
# rate limit 확인
import requests
headers = {'Authorization': f'token {GITHUB_TOKEN}'}
r = requests.get('https://api.github.com/rate_limit', headers=headers)
print(r.json())
```

### 3. 백준 쿠키 만료

```bash
# 쿠키 재설정
python -m export.baekjoon_export --setup
```

### 4. Chromium/ChromeDriver 오류 (Raspberry Pi)

```bash
# snap chromium 설치
sudo snap install chromium

# 경로 확인
which chromium
# /snap/bin/chromium

which chromium.chromedriver
# /snap/bin/chromium.chromedriver
```

## 📝 변경 이력

### 2025-12-27
- **[BREAKING]** Claude 자동 Export 제거, 수동 다운로드 방식으로 변경
- `db_savers/` → `storage/`로 리팩토링
- 테스트 파일 `tests/` 폴더로 분리
- 문서 `docs/` 폴더로 분리

### 2025-12-26
- Raspberry Pi 지원 (snap chromium)
- GitHub, Claude, 백준 통합 수집 완성
- PostgreSQL DB 저장 기능 구현

## 🔜 향후 계획

- [ ] AI 분석 모듈 (Claude API)
- [ ] 블로그 포스트 자동 생성
- [ ] 웹 대시보드 (Flask/FastAPI)
- [ ] GoodNotes PDF OCR 연동
- [ ] Notion API 연동

## 📚 문서

- [아키텍처 상세](ARCHITECTURE.md)
- [데이터베이스 스키마](docs/schema.sql) (예정)
- [API 문서](docs/api.md) (예정)

## 🤝 기여

이 프로젝트는 개인 학습 목적으로 제작되었습니다.

## 📄 라이선스

MIT License

## 👤 Author

**찬욱** (cjang3285)

- GitHub: [@cjang3285](https://github.com/cjang3285)
- 백준: [andy1692](https://www.acmicpc.net/user/andy1692)
