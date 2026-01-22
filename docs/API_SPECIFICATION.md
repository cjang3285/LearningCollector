# GitHub API 사용 명세

LearningCollector는 GitHub GraphQL API와 REST API를 하이브리드로 사용합니다.

---

## 1. GraphQL API (메타데이터 수집)

**목적**: 커밋 메타데이터를 효율적으로 수집

**사용 위치**: `api/github_graphql.py`

### 1.1 레포지토리 목록 조회

**쿼리**:
```graphql
query($username: String!, $cursor: String) {
  user(login: $username) {
    repositories(first: 100, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        owner {
          login
        }
      }
    }
  }
}
```

**목적**: 사용자의 모든 레포지토리 목록 가져오기

**페이지네이션**: 100개씩, cursor 기반

**반환**: 레포 이름 + 소유자

---

### 1.2 브랜치 목록 조회

**쿼리**:
```graphql
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    refs(refPrefix: "refs/heads/", first: 100, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
      }
    }
  }
}
```

**목적**: 레포지토리의 모든 브랜치 목록

**페이지네이션**: 100개씩, cursor 기반

**반환**: 브랜치 이름 (예: main, master, claude/rebuild-project-architecture-shkat)

---

### 1.3 브랜치 커밋 조회 ⭐ 핵심

**쿼리**:
```graphql
query($owner: String!, $name: String!, $branch: String!, $since: GitTimestamp!) {
  repository(owner: $owner, name: $name) {
    ref(qualifiedName: $branch) {
      target {
        ... on Commit {
          history(first: 100, since: $since) {
            nodes {
              oid              # 커밋 SHA
              message          # 커밋 메시지
              committedDate    # 커밋 날짜
              additions        # 추가된 라인 수
              deletions        # 삭제된 라인 수
              changedFiles     # 변경된 파일 수
              author {
                name
                email
                user {
                  login
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**변수**:
```json
{
  "owner": "사용자명",
  "name": "레포명",
  "branch": "refs/heads/브랜치명",
  "since": "2026-01-21T00:00:00+00:00"
}
```

**중요 사항**:
- ❌ `since`와 `until`을 **동시에 사용 불가** (GitHub 제약)
- ✅ `since`만 사용하고, `until`은 클라이언트 사이드 필터링
- `first: 100`: 최대 100개까지만 (페이지네이션 필요 시 `after` 사용)

**반환**: 커밋 메타데이터 (SHA, 메시지, 날짜, 작성자)

**제약**: 파일 내용, diff, patch는 제공하지 않음

---

## 2. REST API (상세 정보 수집)

**목적**: 백준 풀이 코드 등 파일 내용 가져오기

**사용 위치**: `core/github_collector.py`

### 2.1 커밋 상세 정보 조회

**엔드포인트**:
```
GET https://api.github.com/repos/{owner}/{repo}/commits/{sha}
```

**헤더**:
```
Authorization: token {GITHUB_TOKEN}
```

**응답 구조**:
```json
{
  "sha": "커밋 SHA",
  "commit": {
    "message": "커밋 메시지",
    "author": { ... }
  },
  "files": [
    {
      "filename": "백준/1234_두수의합.py",
      "status": "added",
      "additions": 10,
      "deletions": 0,
      "patch": "+a, b = map(int, input().split())\n+print(a + b)"
    }
  ]
}
```

**사용 용도**:
1. **백준 커밋**: `patch` 필드에서 풀이 코드 추출
2. **개발 커밋**: `files` 배열에서 변경된 파일 목록 추출

**코드 추출 로직**:
```python
# patch에서 추가된 코드만 추출
code_lines = [
    line[1:]  # '+' 제거
    for line in patch.split("\n")
    if line.startswith("+") and not line.startswith("+++")
]
```

---

## 3. 하이브리드 전략

### 왜 GraphQL + REST?

| 단계 | API | 이유 |
|------|-----|------|
| 1. 레포 목록 | GraphQL | 페이지네이션 효율적 |
| 2. 브랜치 목록 | GraphQL | 한 번에 100개 조회 |
| 3. 커밋 메타데이터 | GraphQL | 빠른 필터링 (`since`) |
| 4. 파일 내용 | REST | GraphQL은 patch 미제공 |

### 복잡도

**시간 복잡도**: O(레포 수 × 평균 브랜치 수)
- GraphQL이 기간 필터링하므로 커밋 수는 영향 없음
- 각 브랜치당 최대 100개 커밋만 조회

**API 호출 수**:
- 레포 목록: 1회 (페이지네이션 포함 시 최대 N회)
- 브랜치 목록: R회 (레포 수)
- 커밋 조회: R × B회 (레포 × 브랜치)
- REST (백준): 백준 커밋 수만큼

**예시** (LearningCollector 프로젝트):
- 레포: 9개
- 평균 브랜치: 3.8개
- 총 GraphQL 호출: ~34회
- REST 호출: 백준 커밋 수 (예: 32개)

---

## 4. 필터링 전략

### GraphQL (서버 사이드)
```graphql
history(first: 100, since: "2026-01-21T00:00:00Z")
```
→ `since` 이후 커밋만 가져옴

### Python (클라이언트 사이드)
```python
commit_date = datetime.fromisoformat(commit["committedDate"])
if commit_date <= end_date:
    filtered_commits.append(commit)
```
→ `end_date` 이후 커밋 제거

---

## 5. 에러 처리

### GraphQL 에러
```python
if "errors" in response:
    print(f"GraphQL 에러: {response['errors']}")
    return []
```

### REST 에러
```python
if response.status_code != 200:
    print(f"REST API 실패: HTTP {response.status_code}")
    return ""
```

### 재시도 로직
- GraphQL: 없음 (에러 시 빈 배열)
- REST: 없음 (에러 시 빈 문자열)
- Gemini API만 재시도 로직 있음 (exponential backoff)

---

## 6. 제약사항

### GitHub API Rate Limit
- **인증**: 5,000 req/hour
- **미인증**: 60 req/hour

**현재 사용량** (1회 실행):
- GraphQL: ~40회
- REST: ~30회
- **총**: ~70회 (충분히 여유 있음)

### GraphQL 제약
- `since`와 `until` 동시 사용 불가
- `history`는 최대 100개 (페이지네이션 필요)
- 파일 내용 제공 안 함

### REST 제약
- 커밋당 1회 호출 필요 (느림)
- 파일 내용이 크면 응답 느림

---

## 7. 개선 가능성

### 현재 미구현
- GraphQL 페이지네이션 (브랜치당 100개 이상 커밋)
- REST API 재시도 로직
- 동시 요청 (병렬 처리)

### 성능 최적화
- 브랜치별 병렬 조회
- REST API 배치 요청
- 캐싱 전략
