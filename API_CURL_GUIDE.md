# GitHub API curl 호출 가이드

실제 데이터를 curl로 가져와서 샘플 데이터로 저장하는 방법입니다.

## 🔑 사전 준비

```bash
# 환경 변수 설정 (터미널에서 실행)
export GITHUB_TOKEN="your_github_token_here"
export GITHUB_USERNAME="your_username"
```

---

## 📊 1. GitHub 일반 레포 API

### 1-1. 사용자 저장소 목록 가져오기

```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28" \
     "https://api.github.com/user/repos?per_page=5&sort=updated&direction=desc" \
     > tests/fixtures/github/user_repos.json
```

**파라미터:**
- `per_page=5`: 최대 5개만 가져오기
- `sort=updated`: 최근 업데이트 순
- `direction=desc`: 내림차순

---

### 1-2. 특정 레포의 커밋 목록 가져오기

```bash
# 예시: LearningCollector 레포의 오늘 커밋
# since/until 날짜는 UTC 기준 ISO 8601 형식
REPO_NAME="LearningCollector"
SINCE=$(date -u -d "today 00:00:00" +"%Y-%m-%dT%H:%M:%SZ")
UNTIL=$(date -u -d "today 23:59:59" +"%Y-%m-%dT%H:%M:%SZ")

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$REPO_NAME/commits?since=$SINCE&until=$UNTIL&per_page=10" \
     > tests/fixtures/github/commits_list.json
```

**파라미터:**
- `since`: 시작 시간 (ISO 8601)
- `until`: 종료 시간 (ISO 8601)
- `per_page=10`: 최대 10개

**특정 날짜 예시:**
```bash
# 2025-01-13 커밋 가져오기
SINCE="2025-01-13T00:00:00Z"
UNTIL="2025-01-13T23:59:59Z"
```

---

### 1-3. 커밋 상세 정보 가져오기 (파일 변경 포함)

```bash
# 먼저 1-2에서 받은 commits_list.json에서 SHA를 확인
# 예시 SHA: abc123def456

COMMIT_SHA="abc123def456"  # 실제 SHA로 변경

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$REPO_NAME/commits/$COMMIT_SHA" \
     > tests/fixtures/github/commit_detail.json
```

**응답에 포함되는 정보:**
- 커밋 메시지, 작성자, 날짜
- `files[]`: 변경된 파일 목록
  - `filename`: 파일명
  - `status`: added/modified/deleted
  - `additions`: 추가 라인 수
  - `deletions`: 삭제 라인 수
  - `patch`: diff 내용
- `stats`: 전체 통계

---

### 1-4. 파일 내용 가져오기

```bash
# 특정 커밋의 파일 내용
FILE_PATH="src/main.py"

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$REPO_NAME/contents/$FILE_PATH?ref=$COMMIT_SHA" \
     > tests/fixtures/github/file_content.json
```

**응답 형식:**
- `content`: base64로 인코딩된 파일 내용
- `encoding`: "base64"
- 디코딩 필요: `base64 -d`

---

## 🎯 2. BaekjoonHub API

### 2-1. BaekjoonHub 레포 커밋 목록

```bash
BAEKJOON_REPO="BaekjoonHub"  # 본인의 백준허브 레포 이름
SINCE="2025-01-13T00:00:00Z"
UNTIL="2025-01-13T23:59:59Z"

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$BAEKJOON_REPO/commits?since=$SINCE&until=$UNTIL&per_page=10" \
     > tests/fixtures/baekjoon/commits_list.json
```

---

### 2-2. 백준 커밋 상세 정보 (파일 목록 포함)

```bash
# 백준허브는 자동으로 README.md와 코드 파일을 함께 커밋
COMMIT_SHA="def789ghi012"  # 실제 SHA로 변경

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$BAEKJOON_REPO/commits/$COMMIT_SHA" \
     > tests/fixtures/baekjoon/commit_detail.json
```

**백준허브 커밋 구조:**
- `files[]`에서 다음 파일들 확인:
  - `백준/Silver/1234. 문제명/README.md`
  - `백준/Silver/1234. 문제명/solution.py`

---

### 2-3. 백준 문제 README 가져오기

```bash
# commit_detail.json에서 README 경로 확인 후
README_PATH="백준/Silver/1260. DFS와 BFS/README.md"

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$BAEKJOON_REPO/contents/$README_PATH?ref=$COMMIT_SHA" \
     > tests/fixtures/baekjoon/readme_content.json
```

---

### 2-4. 백준 코드 파일 가져오기

```bash
CODE_PATH="백준/Silver/1260. DFS와 BFS/DFS와 BFS.py"

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$BAEKJOON_REPO/contents/$CODE_PATH?ref=$COMMIT_SHA" \
     > tests/fixtures/baekjoon/code_content.json
```

---

### 2-5. 디렉토리 내용 목록 가져오기

```bash
# 문제 폴더 내의 파일 목록 (README.md가 아닌 코드 파일 찾기용)
PROBLEM_DIR="백준/Silver/1260. DFS와 BFS"

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$BAEKJOON_REPO/contents/$PROBLEM_DIR?ref=$COMMIT_SHA" \
     > tests/fixtures/baekjoon/directory_listing.json
```

---

## 📁 저장할 파일 구조

```
tests/fixtures/
├── github/
│   ├── user_repos.json          # 사용자 저장소 목록
│   ├── commits_list.json        # 커밋 목록
│   ├── commit_detail.json       # 커밋 상세 (파일 변경 포함)
│   └── file_content.json        # 파일 내용
│
└── baekjoon/
    ├── commits_list.json        # 백준허브 커밋 목록
    ├── commit_detail.json       # 백준 커밋 상세
    ├── readme_content.json      # README.md 내용
    ├── code_content.json        # 코드 파일 내용
    └── directory_listing.json   # 문제 폴더 파일 목록
```

---

## 🚀 빠른 실행 스크립트

```bash
#!/bin/bash
# 실제 데이터를 한번에 수집하는 스크립트

# 환경 변수 설정
export GITHUB_TOKEN="your_token"
export GITHUB_USERNAME="your_username"

# 디렉토리 생성
mkdir -p tests/fixtures/github
mkdir -p tests/fixtures/baekjoon

echo "1. 사용자 저장소 목록..."
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/user/repos?per_page=5&sort=updated" \
     > tests/fixtures/github/user_repos.json

echo "2. 오늘의 커밋 목록..."
REPO_NAME="LearningCollector"
SINCE=$(date -u -d "today 00:00:00" +"%Y-%m-%dT%H:%M:%SZ")
UNTIL=$(date -u -d "today 23:59:59" +"%Y-%m-%dT%H:%M:%SZ")

curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_USERNAME/$REPO_NAME/commits?since=$SINCE&until=$UNTIL" \
     > tests/fixtures/github/commits_list.json

# commits_list.json에서 첫 번째 SHA 추출
COMMIT_SHA=$(cat tests/fixtures/github/commits_list.json | grep -m1 '"sha"' | cut -d'"' -f4)

if [ -n "$COMMIT_SHA" ]; then
    echo "3. 커밋 상세 정보 (SHA: $COMMIT_SHA)..."
    curl -H "Authorization: Bearer $GITHUB_TOKEN" \
         -H "Accept: application/vnd.github+json" \
         "https://api.github.com/repos/$GITHUB_USERNAME/$REPO_NAME/commits/$COMMIT_SHA" \
         > tests/fixtures/github/commit_detail.json
fi

echo "완료!"
```

---

## 🎯 다음 단계 계획

### 1단계: 실제 데이터 수집
```bash
# 위의 curl 명령어들을 실행해서 JSON 파일들 저장
```

### 2단계: 샘플 데이터 확인
```bash
# 받은 JSON 구조 확인
cat tests/fixtures/github/commit_detail.json | jq '.' | head -50
```

### 3단계: 파서 테스트 작성
- `tests/test_github_parser.py`: GitHub 응답 파싱 테스트
- `tests/test_baekjoon_parser.py`: BaekjoonHub 응답 파싱 테스트

### 4단계: 파서 구현 검증
- 실제 데이터로 `parse/github_parse.py` 테스트
- 실제 데이터로 `parse/baekjoon_parse.py` 테스트

---

## 📝 중요 참고사항

### API Rate Limit
- **인증 안 함**: 시간당 60회
- **인증 함**: 시간당 5,000회

현재 남은 횟수 확인:
```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     "https://api.github.com/rate_limit"
```

### 날짜 형식
- ISO 8601: `2025-01-13T00:00:00Z`
- UTC 기준 (끝에 Z 붙임)
- 한국 시간 → UTC: 9시간 빼기

### 한글 URL 인코딩
백준 폴더명에 한글이 있는 경우:
```bash
# 한글 경로는 URL 인코딩 필요
# "백준" -> "%EB%B0%B1%EC%A4%80"

# 또는 curl이 자동 인코딩하도록 --data-urlencode 사용
```
