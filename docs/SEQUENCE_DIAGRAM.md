# Learning Artifacts ETL - 시퀀스 다이어그램

## 1. 전체 ETL 프로세스 흐름

```
User          main.py      Collector     Exporter      Parser        Saver         DB
 │              │              │             │            │            │            │
 │─python main.py───────>│     │             │            │            │            │
 │              │         │    │             │            │            │            │
 │              │─run()──>│    │             │            │            │            │
 │              │         │    │             │            │            │            │
 │              │         │─collect()──>│    │            │            │            │
 │              │         │    │         │   │            │            │            │
 │              │         │    │         │─export()──>│   │            │            │
 │              │         │    │         │   │        │   │            │            │
 │              │         │    │         │   │        │   │            │            │
 │              │         │    │         │<──data─────│   │            │            │
 │              │         │    │         │   │            │            │            │
 │              │         │    │         │─parse(data)───>│            │            │
 │              │         │    │         │   │            │            │            │
 │              │         │    │         │   │            │            │            │
 │              │         │    │         │<──parsed───────│            │            │
 │              │         │    │         │   │                         │            │
 │              │         │    │         │─save_all(parsed)───────>│   │            │
 │              │         │    │         │   │                      │   │            │
 │              │         │    │         │   │                      │─INSERT───>│   │
 │              │         │    │         │   │                      │   │       │   │
 │              │         │    │         │   │                      │   │       │   │
 │              │         │    │         │   │                      │<──id──────│   │
 │              │         │    │         │<──artifact_ids───────────│   │           │
 │              │         │    │<────────│   │                          │           │
 │              │         │<──result────│    │                          │           │
 │              │<────────│    │             │                          │           │
 │<──summary────│         │    │             │                          │           │
 │              │         │    │             │                          │           │
```

## 2. GitHub 수집 상세 시퀀스

```
GitHubCollector   GitHubExporter     GitHub API    GitHubParser   GitHubSaver    PostgreSQL
       │                 │                │              │              │              │
       │─collect()──>│   │                │              │              │              │
       │             │   │                │              │              │              │
       │             │─export_today()─>│  │              │              │              │
       │             │   │             │  │              │              │              │
       │             │   │─GET /user/repos──>│           │              │              │
       │             │   │             │  │  │           │              │              │
       │             │   │<──repos[]───│  │  │           │              │              │
       │             │   │             │  │              │              │              │
       │             │   │─for each repo─────>│          │              │              │
       │             │   │             │  │   │          │              │              │
       │             │   │─GET /commits?since=──>│       │              │              │
       │             │   │             │  │   │  │       │              │              │
       │             │   │<──commits[]─┼──┼───┼──│       │              │              │
       │             │   │             │  │   │          │              │              │
       │             │   │─GET /commit/{sha}───>│        │              │              │
       │             │   │             │  │   │  │       │              │              │
       │             │   │<──diff+files┼──┼───┼──│       │              │              │
       │             │   │             │  │              │              │              │
       │             │<──commits[]────│  │              │              │              │
       │             │   │                │              │              │              │
       │             │─parse_commits(commits)───>│       │              │              │
       │             │   │                │      │       │              │              │
       │             │   │                │      │─detect_language()    │              │
       │             │   │                │      │─extract_comments()   │              │
       │             │   │                │      │       │              │              │
       │             │<──parsed[]────────┼──────│       │              │              │
       │             │   │                │              │              │              │
       │             │─save_all(parsed)──┼──────┼──────>│              │              │
       │             │   │                │              │              │              │
       │             │   │                │              │─save_artifact()────>│       │
       │             │   │                │              │              │      │       │
       │             │   │                │              │              │─INSERT INTO─>│
       │             │   │                │              │              │  learning_   │
       │             │   │                │              │              │  artifacts   │
       │             │   │                │              │              │      │       │
       │             │   │                │              │              │<─artifact_id─│
       │             │   │                │              │              │      │       │
       │             │   │                │              │─save_commit()──────>│       │
       │             │   │                │              │              │      │       │
       │             │   │                │              │              │─INSERT INTO─>│
       │             │   │                │              │              │  github_     │
       │             │   │                │              │              │  commits     │
       │             │   │                │              │              │      │       │
       │             │<──artifact_ids────┼──────┼───────│              │              │
       │<──result────│   │                │              │              │              │
       │             │   │                │              │              │              │
```

## 3. Claude 수집 상세 시퀀스 (수동 다운로드 방식)

```
User    ClaudeCollector   ClaudeParser      ZIP File    ClaudeSaver   PostgreSQL
  │            │                │                │            │              │
  │─download ZIP manually────>│  │                │            │              │
  │            │                │  │                │            │              │
  │─collect(zip_path)─>│       │  │                │            │              │
  │            │        │       │  │                │            │              │
  │            │        │─parse_zip(path)────>│     │            │              │
  │            │        │       │              │     │            │              │
  │            │        │       │─open ZIP─────────>│            │              │
  │            │        │       │              │     │            │              │
  │            │        │       │<─conversations.json│            │              │
  │            │        │       │              │                  │              │
  │            │        │       │─JSON.parse() │                  │              │
  │            │        │       │              │                  │              │
  │            │        │<──conversations[]────│                  │              │
  │            │        │       │                                 │              │
  │            │        │─filter_by_date(convs)                   │              │
  │            │        │       │                                 │              │
  │            │        │─for each conversation─>│                │              │
  │            │        │       │                │                │              │
  │            │        │       │─parse_conversation()            │              │
  │            │        │       │  - extract messages             │              │
  │            │        │       │  - extract code blocks          │              │
  │            │        │       │  - calculate duration           │              │
  │            │        │       │                │                │              │
  │            │        │<──ConversationData[]───│                │              │
  │            │        │       │                                 │              │
  │            │        │─save_all(conversations)────────>│       │              │
  │            │        │       │                         │       │              │
  │            │        │       │                         │─for each conv─>│     │
  │            │        │       │                         │       │        │     │
  │            │        │       │                         │─save_artifact()──────>│
  │            │        │       │                         │       │        │     │
  │            │        │       │                         │       │    INSERT    │
  │            │        │       │                         │       │ learning_   │
  │            │        │       │                         │       │ artifacts    │
  │            │        │       │                         │       │        │     │
  │            │        │       │                         │<──artifact_id──┼─────│
  │            │        │       │                         │       │              │
  │            │        │       │                         │─save_conversation()─>│
  │            │        │       │                         │       │              │
  │            │        │       │                         │       │    INSERT    │
  │            │        │       │                         │       │   claude_    │
  │            │        │       │                         │       │conversations │
  │            │        │       │                         │       │              │
  │            │        │       │                         │<──id──┼──────────────│
  │            │        │       │                         │       │              │
  │            │        │<──artifact_ids──────────────────│       │              │
  │            │<───────│       │                                 │              │
  │<──result───│        │       │                                 │              │
  │            │        │       │                                 │              │
```

## 4. 백준 수집 상세 시퀀스

```
BaekjoonCollector BaekjoonExporter  solved.ac  Selenium   BaekjoonParser BaekjoonSaver  DB
       │                 │              API       (BOJ)          │              │        │
       │─collect()──>│   │               │         │             │              │        │
       │             │   │               │         │             │              │        │
       │             │─export_today()─>│ │         │             │              │        │
       │             │   │              │ │         │             │              │        │
       │             │   │─GET /user/{handle}──>│  │             │              │        │
       │             │   │              │ │     │  │             │              │        │
       │             │   │<──user data──│ │     │  │             │              │        │
       │             │   │              │ │        │             │              │        │
       │             │   │─load cache   │ │        │             │              │        │
       │             │   │ (solved.json)│ │        │             │              │        │
       │             │   │              │ │        │             │              │        │
       │             │   │─diff(current, cache)   │             │              │        │
       │             │   │  → today's problems    │             │              │        │
       │             │   │              │ │        │             │              │        │
       │             │   │─for each problem───────────>│         │              │        │
       │             │   │              │ │        │   │         │              │        │
       │             │   │─setup_driver()│        │   │         │              │        │
       │             │   │              │ │        │   │         │              │        │
       │             │   │─load_cookies()│        │   │         │              │        │
       │             │   │              │ │        │   │         │              │        │
       │             │   │─navigate to problem────────>│         │              │        │
       │             │   │              │ │        │   │         │              │        │
       │             │   │─get submissions────────────>│         │              │        │
       │             │   │              │ │        │   │         │              │        │
       │             │   │<──submission code──────────│         │              │        │
       │             │   │              │ │                      │              │        │
       │             │<──problems[]─────│ │                      │              │        │
       │             │   │                                       │              │        │
       │             │─parse_problems(problems)────────>│        │              │        │
       │             │   │                               │       │              │        │
       │             │   │                               │─analyze_code()       │        │
       │             │   │                               │  - count lines       │        │
       │             │   │                               │  - extract comments  │        │
       │             │   │                               │       │              │        │
       │             │<──parsed[]────────────────────────│       │              │        │
       │             │   │                                       │              │        │
       │             │─save_all(parsed)──────────────────────────────>│         │        │
       │             │   │                                       │     │         │        │
       │             │   │                                       │     │─save_artifact()─>│
       │             │   │                                       │     │         │        │
       │             │   │                                       │     │    INSERT        │
       │             │   │                                       │     │  learning_       │
       │             │   │                                       │     │  artifacts       │
       │             │   │                                       │     │         │        │
       │             │   │                                       │     │<─artifact_id─────│
       │             │   │                                       │     │         │        │
       │             │   │                                       │     │─save_solution()─>│
       │             │   │                                       │     │         │        │
       │             │   │                                       │     │    INSERT        │
       │             │   │                                       │     │  baekjoon_       │
       │             │   │                                       │     │  solutions       │
       │             │   │                                       │     │         │        │
       │             │<──artifact_ids────────────────────────────┼─────│                  │
       │<──result────│   │                                             │                  │
       │             │   │                                             │                  │
```

## 5. 에러 처리 시퀀스

```
Collector     Exporter      Parser        Saver         Result
    │             │             │            │             │
    │─collect()──>│             │            │             │
    │             │             │            │             │
    │             │─export()──>X (API Error) │             │
    │             │             │            │             │
    │             │<──Exception─│            │             │
    │             │             │            │             │
    │             │─log error   │            │             │
    │             │             │            │             │
    │             │─return []   │            │             │
    │             │             │            │             │
    │<──empty─────│             │            │             │
    │             │             │            │             │
    │─return {success: False}──────────────────────>│      │
    │                                                │      │
    │<──────────────────────────────────────────────│      │
```

## 6. DB 트랜잭션 시퀀스

```
Saver         PostgreSQL     learning_artifacts  source_table
  │                │                  │                │
  │─save_all()────>│                  │                │
  │                │                  │                │
  │                │─BEGIN TRANSACTION│                │
  │                │                  │                │
  │                │─INSERT INTO──────────>│           │
  │                │   learning_artifacts  │           │
  │                │                  │    │           │
  │                │<──artifact_id────┼────│           │
  │                │                  │                │
  │                │─INSERT INTO──────┼────────────────────>│
  │                │   github_commits │                │    │
  │                │   (artifact_id)  │                │    │
  │                │                  │                │    │
  │                │<──commit_id──────┼────────────────┼────│
  │                │                  │                │    │
  │                │─COMMIT───────────┼────────────────┼────│
  │                │                  │                │    │
  │<──success──────│                  │                │    │
  │                │                  │                │    │
  │                                                         │
  만약 에러 발생:                                           │
  │                │                  │                │    │
  │                │─ROLLBACK─────────┼────────────────┼────│
  │                │                  │                │    │
  │<──error────────│                  │                │    │
  │                │                  │                │    │
```

## 7. 파일 저장 시퀀스 (향후 구현)

```
Saver         BaseSaver      File System     PostgreSQL
  │                │               │              │
  │─save_all()────>│               │              │
  │                │               │              │
  │                │─_ensure_directory()──>│      │
  │                │               │       │      │
  │                │               │─mkdir -p─>│  │
  │                │               │       │   │  │
  │                │<──path────────┼───────│   │  │
  │                │               │           │  │
  │                │─save_to_file()────────────>│  │
  │                │               │           │  │
  │                │               │─write JSON──>│
  │                │               │           │  │
  │                │<──file_path───┼───────────│  │
  │                │               │              │
  │                │─save_artifact(path)─────────────>│
  │                │               │              │  │
  │                │               │      INSERT INTO│
  │                │               │    learning_    │
  │                │               │    artifacts    │
  │                │               │  (storage_path) │
  │                │               │              │  │
  │                │<──artifact_id─┼──────────────┼──│
  │<──result───────│               │                 │
  │                │               │                 │
```

## 시퀀스 다이어그램 범례

```
│    수직선 (객체 생명선)
─    메시지 (동기 호출)
<─   응답
─>   메서드 호출
X    에러/실패
──>│ 데이터 전달
```

## 주요 흐름 요약

1. **GitHub 수집**: API → Parse → DB (3단계)
2. **Claude 수집**: Parse (수동 ZIP) → DB (2단계)
3. **백준 수집**: API + Selenium → Parse → DB (3단계)

모든 흐름은 **Collector**가 중앙에서 조율하며, **BaseSaver**가 DB 저장을 표준화합니다.
