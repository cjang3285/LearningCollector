# Learning Loop ETL Pipeline

찬욱님의 모든 학습 활동을 자동으로 수집하고 블로그 포스팅으로 변환하는 ETL 파이프라인

## 프로젝트 구조

```
learning-etl/
├── sources/              # 데이터 소스별 모듈 (export + parse)
│   ├── claude_export.py    # Claude Export 자동화
│   ├── claude_parse.py     # Claude 대화 파서
│   ├── github_export.py    # GitHub 커밋 수집
│   ├── github_parse.py     # GitHub 데이터 파서
│   ├── baekjoon_export.py  # 백준 문제 풀이 수집
│   └── baekjoon_parse.py   # 백준 데이터 파서
│
├── collectors/           # 통합 수집기
│   └── collect_all.py     # 전체 데이터 수집 & 통합
│
└── README.md
```

## 설치

### 1. 필수 패키지

```bash
# Ubuntu/라즈베리파이
sudo apt update
sudo apt install chromium-browser chromium-chromedriver python3-pip

# Python 패키지
pip3 install selenium requests
```

### 2. 환경변수 설정

```bash
# GitHub
export GITHUB_TOKEN="ghp_your_token_here"
export GITHUB_USERNAME="your_username"

# 백준
export BAEKJOON_HANDLE="your_handle"
```

`.bashrc` 또는 `.zshrc`에 추가하여 영구 설정

## 사용 방법

### A. 개별 소스 수집

#### 1. Claude

```bash
# 최초 1회 설정 (쿠키 저장)
python3 sources/claude_export.py --setup

# Export 실행
python3 sources/claude_export.py

# 파싱만 (이미 ZIP이 있는 경우)
python3 sources/claude_parse.py ~/Downloads/conversations.zip
```

#### 2. GitHub

```bash
# 오늘 커밋 수집
python3 sources/github_export.py

# 파싱만
python3 sources/github_parse.py
```

#### 3. 백준

```bash
# 최초 1회 설정 (쿠키 저장)
python3 sources/baekjoon_export.py --setup

# 오늘 푼 문제 + 제출 코드 수집
python3 sources/baekjoon_export.py

# 파싱만
python3 sources/baekjoon_parse.py
```

### B. 통합 수집 (권장)

```bash
# 모든 소스에서 데이터 수집 + 통합
python3 collectors/collect_all.py

# 출력: ~/learning-data/learning-YYYYMMDD.json
```

### C. 자동화 (cron)

```bash
crontab -e
```

```cron
# 매일 밤 23:50 실행
50 23 * * * cd /home/pi/learning-etl && python3 collectors/collect_all.py >> /var/log/learning-etl.log 2>&1
```

## 출력 데이터 구조

### 통합 JSON (learning-YYYYMMDD.json)

```json
{
  "metadata": {
    "collected_at": "2025-12-26T23:50:00Z",
    "date": "2025-12-26"
  },
  "claude": {
    "success": true,
    "count": 3,
    "data": [
      {
        "uuid": "...",
        "name": "대화 제목",
        "summary": "요약",
        "user_messages": 5,
        "assistant_messages": 5,
        "has_code": true,
        "code_blocks": [...],
        "duration_minutes": 45.2
      }
    ]
  },
  "github": {
    "success": true,
    "count": 8,
    "summary": {
      "total_commits": 8,
      "total_repos": 3,
      "total_additions": 245,
      "total_deletions": 67,
      "total_files": 15,
      "languages": {"Python": 8, "JavaScript": 5, "Go": 2},
      "total_comments": 32
    },
    "data": [
      {
        "repo": "learning-etl",
        "sha": "abc123...",
        "message": "Add GitHub collector",
        "date": "2025-12-26T14:30:00Z",
        "url": "https://github.com/...",
        "files": [
          {
            "filename": "github_export.py",
            "status": "modified",
            "additions": 50,
            "deletions": 10,
            "changes": 60,
            "patch": "diff --git...",
            "content": "#!/usr/bin/env python3...",
            "language": "Python",
            "comments": [
              {
                "line_number": 5,
                "comment_type": "docstring",
                "content": "GitHub 커밋 수집"
              }
            ]
          }
        ],
        "stats": {"additions": 50, "deletions": 10}
      }
    ]
  },
  "baekjoon": {
    "success": true,
    "count": 2,
    "summary": {
      "total_problems": 2,
      "tiers": {"Gold IV": 1, "Silver II": 1},
      "tags": {"DP": 1, "그래프": 1},
      "languages": {"Python 3": 2},
      "total_code_lines": 45,
      "total_comments": 8
    },
    "data": [
      {
        "problem_id": 1234,
        "title": "문제 제목",
        "tier": "Gold IV",
        "tags": ["DP", "그래프"],
        "url": "https://www.acmicpc.net/problem/1234",
        "submission": {
          "submission_id": "12345678",
          "language": "Python 3",
          "code": "# DP 풀이\ndef solve():\n    ...",
          "memory": "31256 KB",
          "time": "72 ms"
        },
        "code_analysis": {
          "language": "Python 3",
          "total_lines": 25,
          "code_lines": 18,
          "comment_lines": 4,
          "blank_lines": 3,
          "comments": [
            {
              "line_number": 1,
              "comment_type": "single",
              "content": "DP 풀이"
            }
          ]
        }
      }
    ]
  },
  "summary": {
    "total_activities": 13,
    "conversations": 3,
    "commits": 8,
    "problems": 2
  }
}
```

## 각 모듈 상세

### Claude

**Export (claude_export.py)**
- Selenium headless로 claude.ai 자동 로그인
- Settings → Privacy → Export 클릭
- conversations.zip 다운로드

**Parse (claude_parse.py)**
- ZIP 파싱 → conversations.json 추출
- 날짜 필터링 (오늘만)
- 코드 블록 추출
- 대화 통계 생성

### GitHub

**Export (github_export.py)**
- GitHub REST API 사용
- Personal Access Token 필요
- 모든 저장소의 오늘 커밋 수집
- **커밋별 파일 변경사항 (diff) 수집**
- **변경된 파일의 전체 코드 가져오기**
- `since`/`until` 파라미터로 날짜 필터

**Parse (github_parse.py)**
- 커밋 데이터 구조화
- **파일별 언어 감지 (확장자 기반)**
- **코드에서 주석 추출 (Python, C++, Java 등)**
- 저장소별/언어별 그룹화
- 통계 생성 (커밋 수, 추가/삭제 라인, 주석 수)

### 백준

**Export (baekjoon_export.py)**
- solved.ac API로 당일 푼 문제 찾기 (diff 방식)
- **Selenium으로 백준 로그인 후 제출 코드 크롤링**
- 문제 상세 정보 + 제출 코드 수집

**Parse (baekjoon_parse.py)**
- 문제 데이터 구조화
- **코드 분석 (라인 수, 주석 추출)**
- **주석 파싱 (Python, C++, Java 지원)**
- 티어/태그별 그룹화

## 주의사항

### 1. Claude 쿠키 만료
- Google 로그인 쿠키는 30~60일 유효
- 만료 시 `--setup` 재실행 필요

### 2. GitHub Rate Limit
- Personal Token: 5000 req/hr
- 충분하지만, 너무 많은 저장소가 있으면 주의

### 3. solved.ac Rate Limit
- 15분당 ~256회
- 문제 수집 시 페이지네이션 주의

### 4. 백준 Diff 방식
- solved.ac는 타임스탬프 미제공
- 이전 캐시 (`~/.baekjoon_solved.json`)와 비교
- **최초 실행 시 모든 문제가 "오늘 푼 문제"로 나옴**
- 다음날부터 정상 작동

## 다음 단계

### 🚧 구현 예정

1. **AI 분석 모듈**
   - Claude API로 대화/커밋 분석
   - 학습 주제 추출
   - 핵심 포인트 요약

2. **포스트 생성기**
   - Dev Log (커밋) 템플릿
   - Algorithm (백준) 템플릿
   - Deep Dive (학습) 템플릿

3. **리뷰 대시보드**
   - 웹 UI로 포스트 미리보기
   - 수정/승인 기능

4. **블로그 API 연동**
   - 승인된 포스트 자동 업로드

## 라이선스

MIT License
