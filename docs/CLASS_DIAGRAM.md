# Learning Artifacts ETL - 클래스 다이어그램

## 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Learning ETL Pipeline                           │
│                              (main.py)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
        │ GitHubCollector  │ │ClaudeCollector│ │BaekjoonCollector│
        └──────────────────┘ └──────────────┘ └─────────────────┘
                │                   │                   │
        ┌───────┼───────┐          │          ┌────────┼────────┐
        ▼       ▼       ▼          ▼          ▼        ▼        ▼
    [Export] [Parse] [Save]    [Parse]    [Export] [Parse]  [Save]
                                 [Save]
```

## 계층별 클래스 다이어그램

### 1. Collectors Layer (통합 수집기)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Collectors                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │GitHubCollector  │  │ClaudeCollector  │  │BaekjoonCollector│ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │- exporter       │  │- saver          │  │- exporter       │ │
│  │- parser         │  │                 │  │- parser         │ │
│  │- saver          │  │                 │  │- saver          │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │+ collect()      │  │+ collect()      │  │+ collect()      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│         │                      │                     │          │
│         │                      │                     │          │
│    [1.Export]            [1.Parse]             [1.Export]       │
│    [2.Parse]             [2.Save]              [2.Parse]        │
│    [3.Save]                                    [3.Save]         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Export Layer (데이터 수집)

```
┌──────────────────────────────────────────────────────────────┐
│                      Export Layer                             │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────┐              ┌────────────────────┐   │
│  │ GitHubExporter    │              │ BaekjoonExporter   │   │
│  ├───────────────────┤              ├────────────────────┤   │
│  │- token            │              │- cookies_file      │   │
│  │- username         │              │- cache_path        │   │
│  │                   │              │- driver            │   │
│  ├───────────────────┤              ├────────────────────┤   │
│  │+ export_today()   │              │+ setup()           │   │
│  │+ get_commits()    │              │+ export_today()    │   │
│  └───────────────────┘              │+ get_submissions() │   │
│         │                           └────────────────────┘   │
│         │                                     │              │
│         ▼                                     ▼              │
│  GitHub REST API                     Selenium + solved.ac    │
│                                                               │
│  ❌ ClaudeExporter (삭제됨 - 수동 다운로드 방식)              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 3. Parse Layer (데이터 파싱)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Parse Layer                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐     │
│  │GitHubParser  │  │ClaudeParser  │  │BaekjoonParser     │     │
│  ├──────────────┤  ├──────────────┤  ├───────────────────┤     │
│  │              │  │              │  │                   │     │
│  ├──────────────┤  ├──────────────┤  ├───────────────────┤     │
│  │+ parse()     │  │+ parse_zip() │  │+ parse_problems() │     │
│  │+ detect_lang()│  │+ filter()   │  │+ analyze_code()   │     │
│  │+ extract_    │  │+ parse_conv()│  │+ get_summary()    │     │
│  │  comments()  │  │              │  │                   │     │
│  └──────────────┘  └──────────────┘  └───────────────────┘     │
│         │                  │                    │               │
│         ▼                  ▼                    ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐     │
│  │ CommitData   │  │Conversation  │  │ ProblemData       │     │
│  │ (dataclass)  │  │Data          │  │ (dataclass)       │     │
│  └──────────────┘  │(dataclass)   │  └───────────────────┘     │
│                    └──────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Storage Layer (DB 저장) - 상속 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ┌────────────────┐                            │
│                    │   BaseSaver    │ (Base Class)               │
│                    ├────────────────┤                            │
│                    │- db_config     │                            │
│                    │- artifacts_dir │                            │
│                    ├────────────────┤                            │
│                    │+ _get_db_conn()│                            │
│                    │+ _ensure_dir() │                            │
│                    │+ save_to_file()│                            │
│                    │+ save_artifact│                            │
│                    └────────────────┘                            │
│                           △                                      │
│              ┌────────────┼────────────┐                         │
│              │            │            │                         │
│     ┌────────┴──────┐ ┌──┴──────────┐ ┌┴──────────────┐         │
│     │ GitHubSaver   │ │ClaudeSaver  │ │BaekjoonSaver  │         │
│     ├───────────────┤ ├─────────────┤ ├───────────────┤         │
│     │               │ │             │ │               │         │
│     ├───────────────┤ ├─────────────┤ ├───────────────┤         │
│     │+ save_all()   │ │+ save_all() │ │+ save_all()   │         │
│     │+ save_commit()│ │+ save_conv()│ │+ save_solution│         │
│     └───────────────┘ └─────────────┘ └───────────────┘         │
│              │            │            │                         │
│              └────────────┼────────────┘                         │
│                           ▼                                      │
│                  PostgreSQL Database                             │
│                 ┌──────────────────┐                             │
│                 │learning_artifacts│                             │
│                 │github_commits    │                             │
│                 │claude_conversations                            │
│                 │baekjoon_solutions│                             │
│                 └──────────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 클래스 관계도 (UML 스타일)

```
                    LearningETL
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        │ uses          │ uses          │ uses
        ▼               ▼               ▼
 GitHubCollector  ClaudeCollector  BaekjoonCollector
        │               │               │
        │               │               │
    ┌───┼───┐          │          ┌────┼────┐
    │   │   │          │          │    │    │
    ▼   ▼   ▼          ▼          ▼    ▼    ▼
   GExp GP GS        CP,CS      BExp  BP   BS

범례:
  GExp = GitHubExporter      CP = ClaudeParser      BExp = BaekjoonExporter
  GP   = GitHubParser        CS = ClaudeSaver       BP   = BaekjoonParser
  GS   = GitHubSaver                                BS   = BaekjoonSaver
```

## 데이터 클래스 (Dataclass)

```
┌──────────────────────────────────────────────────────────────┐
│                     Data Models                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  CommitData          ConversationData      ProblemData       │
│  ├─ repo             ├─ uuid               ├─ problem_id     │
│  ├─ sha              ├─ name               ├─ title          │
│  ├─ message          ├─ summary            ├─ tier           │
│  ├─ date             ├─ messages           ├─ tags           │
│  ├─ files[]          ├─ has_code           ├─ submission     │
│  │  ├─ filename      ├─ code_blocks[]      │  ├─ code        │
│  │  ├─ language      ├─ duration           │  ├─ language    │
│  │  ├─ additions     └─ created_at         │  ├─ memory      │
│  │  ├─ deletions                           │  └─ time        │
│  │  ├─ content                              ├─ url           │
│  │  └─ comments[]                           └─ solved_at     │
│  └─ stats                                                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## 의존성 다이어그램

```
main.py
  │
  └─> collectors/
        ├─> github_collector.py
        │     ├─> export/github_export.py
        │     ├─> parse/github_parse.py
        │     └─> storage/github_saver.py
        │           └─> storage/base_saver.py
        │
        ├─> claude_collector.py
        │     ├─> parse/claude_parse.py
        │     └─> storage/claude_saver.py
        │           └─> storage/base_saver.py
        │
        └─> baekjoon_collector.py
              ├─> export/baekjoon_export.py
              ├─> parse/baekjoon_parse.py
              └─> storage/baekjoon_saver.py
                    └─> storage/base_saver.py

  └─> config/
        └─> settings.py
              └─> DB config, paths, constants
```

## 핵심 디자인 패턴

### 1. Template Method Pattern (BaseSaver)
```
BaseSaver (추상 베이스)
  │
  ├─ _get_db_connection()  (공통)
  ├─ save_to_file()        (공통)
  ├─ save_artifact()       (공통)
  │
  └─> GitHubSaver, ClaudeSaver, BaekjoonSaver
      └─ save_all()        (구체 구현)
```

### 2. Facade Pattern (Collector)
```
Collector (파사드)
  │
  ├─ Export  (복잡한 API 호출)
  ├─ Parse   (복잡한 데이터 구조화)
  └─ Save    (복잡한 DB 저장)
      │
      └─> 단순한 collect() 메서드로 통합
```

### 3. Strategy Pattern (각 소스별 구현)
```
Collector Interface
  │
  ├─ GitHubCollector   (GitHub API 전략)
  ├─ ClaudeCollector   (ZIP 파싱 전략)
  └─> BaekjoonCollector (Selenium 전략)
```

## 패키지 구조 요약

```
LearningConvertedToPost/
│
├── main.py                 [LearningETL]
│
├── collectors/             [Facade Layer]
│   ├── github_collector    [GitHubCollector]
│   ├── claude_collector    [ClaudeCollector]
│   └── baekjoon_collector  [BaekjoonCollector]
│
├── export/                 [Data Source Layer]
│   ├── github_export       [GitHubExporter]
│   └── baekjoon_export     [BaekjoonExporter]
│
├── parse/                  [Parsing Layer]
│   ├── github_parse        [GitHubParser, CommitData]
│   ├── claude_parse        [ClaudeParser, ConversationData]
│   └── baekjoon_parse      [BaekjoonParser, ProblemData]
│
├── storage/                [Persistence Layer]
│   ├── base_saver          [BaseSaver] (Base Class)
│   ├── github_saver        [GitHubSaver]
│   ├── claude_saver        [ClaudeSaver]
│   └── baekjoon_saver      [BaekjoonSaver]
│
└── config/                 [Configuration]
    └── settings            [Constants, DB config]
```
