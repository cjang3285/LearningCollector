# 아키텍처 진화: SOLID 리팩토링 전후 비교

## 목차
1. [리팩토링 개요](#리팩토링-개요)
2. [Phase별 진화 과정](#phase별-진화-과정)
3. [아키텍처 다이어그램](#아키텍처-다이어그램)
4. [디렉토리 구조 변화](#디렉토리-구조-변화)
5. [주요 개선사항](#주요-개선사항)

---

## 리팩토링 개요

### 목표

**SOLID 원칙**을 적용하여 코드베이스의 유지보수성, 확장성, 테스트 용이성을 향상시키기

### 기간

2025년 12월 (Phase 1~6, 총 6단계)

### 주요 개선사항

| 항목 | Before | After |
|------|--------|-------|
| **새 Collector 추가** | 코드 직접 수정 필요 | YAML 파일만 수정 |
| **테스트 작성** | 의존성으로 인해 어려움 | Mock 주입으로 쉬워짐 |
| **코드 중복** | 높음 | 낮음 (인터페이스 사용) |
| **확장성** | 제한적 | 플러그인 방식으로 확장 가능 |
| **런타임 성능** | 기준 | 유사한 수준 유지 |

---

## Phase별 진화 과정

### Phase 0: 리팩토링 전 (Legacy)

**특징**: 절차적 프로그래밍, 하드코딩, 중복 코드

#### 아키텍처

```
main.py
├─ GitHubCollector (직접 생성)
├─ BaekjoonCollector (직접 생성)
└─ AIChatCollector (직접 생성)
    ├─ AIMarkdownParser (직접 생성)
    ├─ AIChatSaver (직접 생성)
    └─ AIExportWatcher (직접 생성)
```

#### 코드 예시

```python
# main.py (Before)
class LearningETL:
    def __init__(self):
        # 하드코딩된 Collector 생성
        self.github_collector = GitHubCollector() if COLLECT_GITHUB else None
        self.baekjoon_collector = BaekjoonCollector() if COLLECT_BAEKJOON else None
        self.ai_chat_collector = AIChatCollector()

    def run(self, target_date, ai_chat_scan=False):
        results = {}

        # GitHub 수집
        if COLLECT_GITHUB and self.github_collector:
            # Export
            commits = self.github_collector.exporter.export_today()
            # Parse
            parsed = self.github_collector.parser.parse_commits(commits)
            # Save
            artifact_ids = self.github_collector.saver.save_all(commits, target_date)
            results['github'] = {'commits_count': len(commits), ...}

        # Baekjoon 수집 (동일한 패턴 반복)
        if COLLECT_BAEKJOON and self.baekjoon_collector:
            ...

        # AI Chat 수집 (또 다른 패턴)
        if ai_chat_scan:
            ...

        return results
```

#### 문제점

 **SRP 위반**: Collector가 너무 많은 책임 (Export + Parse + Save + 조율)
 **OCP 위반**: 새 Collector 추가 시 `main.py` 수정 필요
 **DIP 위반**: 구체 클래스에 직접 의존 (테스트 어려움)
 **LSP 위반**: Collector마다 다른 인터페이스 (`collect_github` vs `collect_baekjoon`)
 **코드 중복**: Export → Parse → Save 패턴 반복
 **테스트 불가**: Mock 주입 어려움

---

### Phase 1: 인터페이스 정의

**목표**: 추상화 계층 도입 (DIP, ISP)

#### 생성된 인터페이스

```python
# interfaces/__init__.py
class IParser(ABC):
    @abstractmethod
    def parse_multiple(self, files: List[str]) -> List[Dict]:
        pass

class ISaver(ABC):
    @abstractmethod
    def save(self, data: Dict, artifact_date: date) -> Optional[int]:
        pass

    @abstractmethod
    def save_all(self, data_list: List[Dict], artifact_date: date) -> List[int]:
        pass

class ICollector(ABC):
    @abstractmethod
    def collect(self, context: CollectionContext) -> CollectionResult:
        pass

    @abstractmethod
    def should_run(self, context: CollectionContext) -> bool:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass
```

#### 개선사항

 **DIP**: 추상화에 의존 (인터페이스)
 **ISP**: 최소한의 메서드만 정의
 **테스트 가능**: Mock 구현 가능

---

### Phase 2-4: Parser/Saver/Collector 리팩토링

**목표**: 인터페이스 구현 + SRP 적용

#### Phase 2: Parser 리팩토링

```python
# parse/ai_chat_parse.py (After)
class AIMarkdownParser(IParser):
    def parse_multiple(self, files: List[str]) -> List[Dict]:
        """IParser 인터페이스 구현"""
        conversations = []
        for file_path in files:
            try:
                conv = self._parse_single(file_path)  # SRP: 파싱만 담당
                conversations.append(conv)
            except ParseError as e:
                logger.error(f"파싱 실패: {e}")
                continue
        return conversations
```

#### Phase 3: Saver 리팩토링

```python
# storage/ai_chat_saver.py (After)
class AIChatSaver(BaseSaver, ISaver):
    def save(self, data: Dict, artifact_date: date) -> Optional[int]:
        """ISaver 인터페이스 구현"""
        try:
            return self.save_ai_chat_artifact(data, artifact_date)
        except Exception as e:
            raise SaveError(f"저장 실패: {e}") from e

    def check_duplicate(self, data: Dict) -> bool:
        """중복 체크 (link 기반)"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id FROM learning.ai_chat_conversations WHERE link = %s",
            (data.get('link'),)
        )
        return cur.fetchone() is not None
```

#### Phase 4: Collector 리팩토링

```python
# collectors/ai_chat_collector.py (After)
class AIChatCollector(ICollector):
    def __init__(self):
        self.parser = AIMarkdownParser()  # IParser에 의존
        self.saver = AIChatSaver()         # ISaver에 의존

    def collect(self, context: CollectionContext) -> CollectionResult:
        """ICollector 인터페이스 구현 (SRP: 조율만 담당)"""
        try:
            # 1. Parse
            conversations = self.parser.parse_multiple(context.options['file_paths'])

            # 2. Save
            artifact_ids = self.saver.save_all(conversations, context.target_date)

            # 3. 결과 반환
            return CollectionResult(
                success=True,
                date=context.target_date,
                items_count=len(conversations),
                artifact_ids=artifact_ids
            )
        except Exception as e:
            logger.error(f"수집 실패: {e}")
            return CollectionResult(success=False, error=str(e), ...)
```

#### 개선사항

 **SRP**: Collector는 조율만, Parser는 파싱만, Saver는 저장만
 **LSP**: 모든 Collector가 동일한 `collect()` 메서드
 **DIP**: 인터페이스에 의존 (구체 클래스 교체 가능)
 **테스트 용이**: Mock Parser/Saver 주입 가능

---

### Phase 5: CollectorFactory 도입

**목표**: OCP 적용 (Registry 패턴)

#### Before (Phase 4)

```python
# main.py
class LearningETL:
    def __init__(self):
        # 여전히 하드코딩
        self.github_collector = GitHubCollector() if COLLECT_GITHUB else None
        self.baekjoon_collector = BaekjoonCollector() if COLLECT_BAEKJOON else None
        self.ai_chat_collector = AIChatCollector()
```

#### After (Phase 5)

```python
# factories/collector_factory.py
class CollectorFactory:
    # Registry에 등록 (코드에 하드코딩)
    COLLECTOR_REGISTRY = {
        'github': {
            'class': GitHubCollector,
            'enabled_by_default': False,
            'config_key': 'COLLECT_GITHUB'
        },
        'baekjoon': {...},
        'ai_chat': {...}
    }

    @classmethod
    def create_all_collectors(cls, enabled_only=True):
        collectors = {}
        for name, config in cls.COLLECTOR_REGISTRY.items():
            if enabled_only and not cls._is_enabled(name, config):
                continue
            collector = config['class']()
            collectors[name] = collector
        return collectors
```

```python
# main.py (대폭 간소화!)
class LearningETL:
    def __init__(self):
        # Factory로 일괄 생성
        self.collectors = CollectorFactory.create_all_collectors(enabled_only=True)

    def run(self, target_date, ...):
        github_collector = self.collectors.get('github')
        if github_collector:
            results['github'] = github_collector.collect_github(target_date)
        # ...
```

#### 개선사항

 **OCP**: Registry에 등록만 하면 자동 인식
 **중앙화**: Collector 생성 로직 한 곳에 집중
 **일관성**: 모든 Collector 동일한 방식으로 생성

 **한계**: Registry가 여전히 Python 코드에 하드코딩됨

---

### Phase 6: 설정 기반 + 동적 로딩 (현재)

**목표**: 완전한 OCP + 플러그인 시스템

#### 아키텍처

```
config/collectors.yaml (설정)
    ↓ (로드)
CollectorConfig (설정 관리)
    ↓ (주입)
CollectorFactory (동적 생성)
    ↓ (생성)
ICollector 구현체들
    ↓ (사용)
main.py
```

#### config/collectors.yaml

```yaml
collectors:
  github:
    enabled: false
    class_path: "collectors.github_collector.GitHubCollector"  # 문자열!
    priority: 10
    config_key: "COLLECT_GITHUB"
    description: "GitHub 커밋 수집"

  ai_chat:
    enabled: true
    class_path: "collectors.ai_chat_collector.AIChatCollector"
    priority: 30
    config_key: null
    description: "AI 채팅 마크다운 수집"
```

#### config/collector_config.py

```python
class CollectorConfig:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or PROJECT_ROOT / 'config' / 'collectors.yaml'
        self._config = {}
        self._runtime_overrides = {}  # 런타임 오버라이드
        self.load()

    def load(self):
        """YAML 파일 로드"""
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)

    def is_enabled(self, name: str) -> bool:
        """활성화 여부 (런타임 오버라이드 우선)"""
        if name in self._runtime_overrides:
            return self._runtime_overrides[name]

        config = self.get_collector_config(name)
        config_key = config.get('config_key')
        if config_key:
            # 환경변수 확인
            return os.getenv(config_key, 'false').lower() == 'true'

        return config.get('enabled', False)

    def set_enabled(self, name: str, enabled: bool):
        """런타임 활성화/비활성화"""
        self._runtime_overrides[name] = enabled
```

#### factories/collector_factory.py

```python
class CollectorFactory:
    def __init__(self, config: Optional[CollectorConfig] = None):
        self.config = config or CollectorConfig()
        self._cache = {}  # 클래스 캐시

    def _import_collector_class(self, class_path: str):
        """동적 클래스 로딩 (importlib)"""
        if class_path in self._cache:
            return self._cache[class_path]

        # "collectors.github_collector.GitHubCollector" → 모듈, 클래스 분리
        module_path, class_name = class_path.rsplit('.', 1)

        # 동적 import
        module = importlib.import_module(module_path)
        collector_class = getattr(module, class_name)

        # 캐싱
        self._cache[class_path] = collector_class
        return collector_class

    @classmethod
    def create_collector(cls, name: str) -> Optional[ICollector]:
        """클래스 메서드 (하위 호환성)"""
        instance = cls._get_default_instance()
        return instance._create_collector_impl(name)

    def _create_collector_impl(self, name: str) -> Optional[ICollector]:
        """실제 구현"""
        config = self.config.get_collector_config(name)
        class_path = config['class_path']

        # 문자열 → 클래스 (동적 로딩)
        collector_class = self._import_collector_class(class_path)
        return collector_class()
```

#### main.py (완전히 동일!)

```python
class LearningETL:
    def __init__(self):
        # 코드 수정 없음! (하위 호환성)
        self.collectors = CollectorFactory.create_all_collectors(enabled_only=True)
```

#### 개선사항

 **OCP**: 코드 수정 없이 YAML만 수정
 **동적 로딩**: 문자열 → 클래스 (런타임 로드)
 **플러그인 시스템**: 외부 Collector 로드 가능
 **런타임 설정**: 재시작 없이 활성화/비활성화
 **우선순위 제어**: 실행 순서 YAML에서 관리
 **하위 호환성**: 기존 코드 전혀 수정 안 함

---

## 아키텍처 다이어그램

### Before (Phase 0)

```
┌─────────────────────────────────────────────────────────┐
│                       main.py                            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ LearningETL                                       │   │
│  │                                                   │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │   │
│  │  │   GitHub    │  │  Baekjoon    │  │AI Chat  │ │   │
│  │  │  Collector  │  │  Collector   │  │Collector│ │   │
│  │  │             │  │              │  │         │ │   │
│  │  │ ┌────────┐  │  │  ┌────────┐ │  │┌──────┐ │ │   │
│  │  │ │Export  │  │  │  │Export  │ │  ││Export│ │ │   │
│  │  │ │Parse   │  │  │  │Parse   │ │  ││Parse │ │ │   │
│  │  │ │Save    │  │  │  │Save    │ │  ││Save  │ │ │   │
│  │  │ └────────┘  │  │  └────────┘ │  │└──────┘ │ │   │
│  │  └─────────────┘  └──────────────┘  └─────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
             ↓
        PostgreSQL
```

**특징**:
- 모든 로직이 `main.py`에 하드코딩
- Collector마다 다른 패턴
- 중복 코드 많음
- 테스트 불가능

---

### After (Phase 6)

```
┌─────────────────────────────────────────────────────────┐
│                   config/collectors.yaml                 │
│                   (설정 파일)                            │
└─────────────────────────────────────────────────────────┘
             ↓ (로드)
┌─────────────────────────────────────────────────────────┐
│              config/collector_config.py                  │
│              (설정 관리자)                               │
└─────────────────────────────────────────────────────────┘
             ↓ (주입)
┌─────────────────────────────────────────────────────────┐
│           factories/collector_factory.py                 │
│           (동적 Collector 생성)                          │
└─────────────────────────────────────────────────────────┘
             ↓ (생성)
┌─────────────────────────────────────────────────────────┐
│                    ICollector 구현체                     │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │   GitHub     │  │   Baekjoon    │  │  AI Chat    │  │
│  │  Collector   │  │   Collector   │  │  Collector  │  │
│  │              │  │               │  │             │  │
│  │   (조율만)   │  │   (조율만)    │  │   (조율만)  │  │
│  └──────────────┘  └───────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────┘
       ↓               ↓                  ↓
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  IParser    │  │  IParser    │  │  IParser    │
│ (파싱 전담) │  │ (파싱 전담) │  │ (파싱 전담) │
└─────────────┘  └─────────────┘  └─────────────┘
       ↓               ↓                  ↓
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  ISaver     │  │  ISaver     │  │  ISaver     │
│ (저장 전담) │  │ (저장 전담) │  │ (저장 전담) │
└─────────────┘  └─────────────┘  └─────────────┘
       ↓               ↓                  ↓
┌─────────────────────────────────────────────────────────┐
│                      PostgreSQL                          │
└─────────────────────────────────────────────────────────┘
```

**특징**:
- 설정과 코드 분리 (YAML)
- 모든 컴포넌트가 인터페이스 구현
- 책임 분리 (SRP)
- 동적 로딩 (확장 가능)
- 테스트 가능 (Mock 주입)

---

## 디렉토리 구조 변화

### Before

```
LearningETL/
├── main.py                # 모든 로직 집중
├── collectors/
│   ├── github_collector.py     # Export + Parse + Save
│   ├── baekjoon_collector.py
│   └── ai_chat_collector.py
├── export/
├── parse/
├── storage/
└── config/
    ├── settings.py
    └── logging_config.py
```

**문제점**:
- 인터페이스 없음
- Factory 없음
- 설정 파일 없음 (하드코딩)

---

### After

```
LearningETL/
├── main.py                # Factory 사용
│
├── interfaces/            #  새로 추가
│   ├── __init__.py        # IParser, ISaver, ICollector
│   ├── contexts.py        # CollectionContext
│   └── results.py         # CollectionResult
│
├── factories/             #  새로 추가
│   ├── __init__.py
│   └── collector_factory.py  # 동적 Collector 생성
│
├── collectors/            #  리팩토링됨 (ICollector 구현)
│   ├── github_collector.py    # 조율만 담당 (SRP)
│   ├── baekjoon_collector.py
│   └── ai_chat_collector.py
│
├── parse/                 #  리팩토링됨 (IParser 구현)
│   ├── github_parse.py
│   ├── baekjoon_parse.py
│   └── ai_chat_parse.py
│
├── storage/               #  리팩토링됨 (ISaver 구현)
│   ├── base_saver.py
│   ├── github_saver.py
│   ├── baekjoon_saver.py
│   └── ai_chat_saver.py
│
├── config/
│   ├── settings.py
│   ├── logging_config.py
│   ├── collectors.yaml    #  새로 추가 (Collector 설정)
│   └── collector_config.py  #  새로 추가 (설정 관리)
│
├── export/
├── bulk_import/
├── cli/
├── scripts/
├── tests/
└── docs/
    ├── DESIGN_PATTERNS.md        #  새로 추가
    └── ARCHITECTURE_EVOLUTION.md #  새로 추가
```

---

## 주요 개선사항

### 1. 코드 품질

| 항목 | Before | After |
|------|--------|-------|
| **SOLID 준수** | 미적용 | 완전 적용 |
| **코드 중복** | 높음 | 낮음 |
| **순환 의존성** | 있음 | 없음 |

### 2. 개발 생산성

| 작업 | Before | After |
|------|--------|-------|
| **새 Collector 추가** | 코드 수정 필요 | YAML 설정만 수정 |
| **버그 수정** | 여러 파일 수정 | 한 곳만 수정 |
| **테스트 작성** | 어려움 | 쉬움 (Mock 주입 가능) |

### 3. 확장성

| 기능 | Before | After |
|------|--------|-------|
| **런타임 설정 변경** | 불가능 | 가능 |

### 4. 유지보수성

| 항목 | Before | After |
|------|--------|-------|
| **설정 위치** | 코드 곳곳 | YAML 한 곳 |
| **의존성 파악** | 어려움 | 명확함 (인터페이스) |
| **문서화** | 부족 | 개선 |

---

### 새로운 Collector 추가 방법

1. `collectors/new_collector.py` 작성 (ICollector 구현)
2. `config/collectors.yaml`에 추가:
   ```yaml
   new_source:
     enabled: true
     class_path: "collectors.new_collector.NewCollector"
     priority: 25
     description: "새로운 데이터 소스"
   ```

### 테스트 작성 방법

```python
# Mock 주입 가능!
def test_collector():
    mock_parser = MockParser()
    mock_saver = MockSaver()

    collector = AIChatCollector()
    collector.parser = mock_parser  # 주입
    collector.saver = mock_saver    # 주입

    result = collector.collect(context)
    assert result.success == True
```

---

## 결론

### 달성한 것

- **SOLID 적용**: 5가지 원칙 모두 적용
- **설정 기반 아키텍처**: 코드 수정 없이 확장 가능
- **동적 로딩**: 런타임에서 동작
- **하위 호환성**: 리팩토링 전 사용하던 코드 수정 없이 호환
- **테스트 용이성**: Mock 주입 가능
