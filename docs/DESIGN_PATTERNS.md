# 설계 패턴 및 아키텍처 개념 설명

## 목차
1. [Collector Registry 패턴](#collector-registry-패턴)
2. [Factory 패턴](#factory-패턴)
3. [동적 클래스 로딩](#동적-클래스-로딩)
4. [리팩토링 전후 비교](#리팩토링-전후-비교)

---

## Collector Registry 패턴

### 개념

**Collector Registry**는 사용 가능한 모든 Collector의 메타데이터를 중앙에서 관리하는 레지스트리 패턴입니다.

각 Collector의 정보를 다음과 같이 저장합니다:
- **클래스 경로**: 어떤 Python 클래스를 사용할지
- **활성화 여부**: 실행 시 활성화할지 말지
- **우선순위**: 실행 순서
- **설정 키**: 환경변수로 제어할지
- **설명**: 무슨 Collector인지

### 왜 필요한가?

**문제**: 새로운 데이터 소스(예: Notion, Slack)를 추가할 때마다 코드를 여러 곳 수정해야 함
- `main.py`에 Collector 인스턴스 생성 코드 추가
- `run()` 메서드에 실행 로직 추가
- 조건문 추가 (`if` 문 증가)

**해결**: Registry에 등록만 하면 자동으로 인식되고 실행됨
- 새로운 Collector 추가 시 **YAML 파일만 수정**
- 기존 코드는 **전혀 수정하지 않음** (Open/Closed Principle)

---

## Factory 패턴

### 개념

**Factory 패턴**은 객체 생성을 전담하는 클래스를 만들어, 객체 생성 로직을 한 곳에 집중시키는 패턴입니다.

```python
# Factory 없이 (Before)
github_collector = GitHubCollector()
baekjoon_collector = BaekjoonCollector()
ai_chat_collector = AIChatCollector()

# Factory 사용 (After)
factory = CollectorFactory()
collectors = factory.create_all_collectors()  # 자동으로 모든 Collector 생성
```

### 도입 이유

#### 1. **중복 제거**
```python
# Before: main.py에서 직접 생성
if COLLECT_GITHUB:
    self.github_collector = GitHubCollector()
if COLLECT_BAEKJOON:
    self.baekjoon_collector = BaekjoonCollector()
self.ai_chat_collector = AIChatCollector()

# After: Factory가 알아서 생성
self.collectors = CollectorFactory.create_all_collectors(enabled_only=True)
```

#### 2. **설정 기반 관리**
```yaml
# config/collectors.yaml
collectors:
  github:
    enabled: false    # true로 변경하면 활성화
    class_path: "collectors.github_collector.GitHubCollector"
```

코드 수정 없이 **설정 파일만** 수정하면 됩니다.

#### 3. **일관된 인터페이스**
모든 Collector가 동일한 방식으로 생성되므로:
- 생성 로직 버그 감소
- 테스트 코드 작성 용이
- 의존성 주입 가능

#### 4. **확장 용이성**
새로운 Collector 추가 절차:

**Before (Factory 없이)**:
1. Collector 클래스 작성
2. `main.py` 수정 (import 추가)
3. `__init__` 수정 (인스턴스 생성)
4. `run()` 수정 (실행 로직 추가)
5. 설정 파일 수정 (환경변수 추가)

**After (Factory 사용)**:
1. Collector 클래스 작성
2. `collectors.yaml`에 추가

```yaml
notion:
  enabled: true
  class_path: "collectors.notion_collector.NotionCollector"
  priority: 25
```

코드 수정 불필요.

---

## 동적 클래스 로딩

### 개념

**동적 클래스 로딩**은 문자열로 된 클래스 경로를 읽어서 런타임에 클래스를 불러오는 기술입니다.

```python
# 정적 로딩 (일반적인 방법)
from collectors.github_collector import GitHubCollector
collector = GitHubCollector()

# 동적 로딩 (Factory 내부)
class_path = "collectors.github_collector.GitHubCollector"
module_path, class_name = class_path.rsplit('.', 1)  # 분리
module = importlib.import_module(module_path)        # 모듈 import
collector_class = getattr(module, class_name)        # 클래스 가져오기
collector = collector_class()                        # 인스턴스 생성
```

### 왜 필요한가?

#### 1. **설정 기반 아키텍처**
YAML 파일에 클래스 경로를 저장하면, 코드 수정 없이 Collector 교체 가능:

```yaml
# 구현체 A 사용
github:
  class_path: "collectors.github_collector.GitHubCollector"

# 테스트용 구현체 B로 변경
github:
  class_path: "collectors.github_collector_v2.GitHubCollectorV2"
```

코드는 그대로, **설정만 변경**

#### 2. **런타임 확장성**
서버 재시작 없이 새로운 Collector 추가:
1. 새 Collector 클래스 작성
2. YAML 파일 수정
3. `factory.reload_config()` 호출
4. 재시작 불필요

#### 3. **테스트 용이성**
Mock Collector 주입이 쉬움:

```yaml
# 테스트 환경에서는 Mock 사용
github:
  class_path: "tests.mocks.MockGitHubCollector"
```

---

## 리팩토링 전후 비교

### Phase 0: 리팩토링 전 (Hard-coded)

```python
# main.py
class LearningETL:
    def __init__(self):
        # 하드코딩된 Collector 생성
        self.github_collector = GitHubCollector() if COLLECT_GITHUB else None
        self.baekjoon_collector = BaekjoonCollector() if COLLECT_BAEKJOON else None
        self.ai_chat_collector = AIChatCollector()

    def run(self, ...):
        # 각 Collector를 직접 호출
        if self.github_collector:
            results['github'] = self.github_collector.collect_github(...)

        if self.baekjoon_collector:
            results['baekjoon'] = self.baekjoon_collector.collect_baekjoon(...)

        if ai_chat_scan:
            results['ai_chat'] = self.ai_chat_collector.collect_from_downloads(...)
```

**문제점**:
-  새 Collector 추가 시 코드 수정 필요 (OCP 위반)
-  Collector마다 다른 메서드명 (`collect_github`, `collect_baekjoon`)
-  조건문 난립 (`if` 문이 계속 증가)
-  테스트 어려움 (의존성 주입 불가)

---

### Phase 5: CollectorFactory (Registry 하드코딩)

```python
# factories/collector_factory.py
class CollectorFactory:
    COLLECTOR_REGISTRY = {
        'github': {
            'class': GitHubCollector,  # 클래스 직접 참조
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
            collector = config['class']()  # 직접 인스턴스 생성
            collectors[name] = collector
        return collectors
```

```python
# main.py
class LearningETL:
    def __init__(self):
        # Factory로 생성 (코드 간결해짐)
        self.collectors = CollectorFactory.create_all_collectors(enabled_only=True)

    def run(self, ...):
        # 통일된 방식으로 실행
        github_collector = self.collectors.get('github')
        if github_collector:
            results['github'] = github_collector.collect_github(...)
```

**개선점**:
-  Collector 생성 로직 중앙화
-  일관된 생성 패턴
-  Registry 패턴 도입

**남은 문제**:
-  Registry가 여전히 코드에 하드코딩됨
-  새 Collector 추가 시 Python 코드 수정 필요
-  클래스를 직접 import 해야 함

---

### Phase 6: 설정 기반 + 동적 로딩 (현재)

```yaml
# config/collectors.yaml (코드 밖으로 분리)
collectors:
  github:
    enabled: false
    class_path: "collectors.github_collector.GitHubCollector"  # 문자열
    priority: 10
    description: "GitHub 커밋 수집"

  notion:  # 새 Collector 추가 (코드 수정 없이)
    enabled: true
    class_path: "collectors.notion_collector.NotionCollector"
    priority: 15
    description: "Notion 페이지 수집"
```

```python
# factories/collector_factory.py
class CollectorFactory:
    def __init__(self, config: CollectorConfig = None):
        self.config = config or CollectorConfig()  # YAML 로드
        self._cache = {}

    def _import_collector_class(self, class_path: str):
        """동적 클래스 로딩 (importlib 사용)"""
        module_path, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def create_collector(self, name: str):
        config = self.config.get_collector_config(name)
        class_path = config['class_path']

        # 문자열로부터 클래스 동적 로드
        collector_class = self._import_collector_class(class_path)
        return collector_class()
```

```python
# main.py (코드 수정 없음)
class LearningETL:
    def __init__(self):
        self.collectors = CollectorFactory.create_all_collectors(enabled_only=True)
```

**개선점**:
-  **코드 밖으로 설정 분리** (YAML 파일)
-  **동적 클래스 로딩** (문자열 → 클래스)
-  **OCP** (새 Collector 추가 시 코드 수정 불필요)
-  **우선순위 기반 정렬** (실행 순서 제어)
-  **런타임 활성화/비활성화** (재시작 불필요)
-  **플러그인 시스템 가능** (외부 Collector 로드)

---

## 성능 영향 분석

### 리팩토링이 속도에 미치는 영향

#### 1. **초기화 시간**

**Before (하드코딩)**:
```python
# 직접 import (컴파일 타임)
from collectors.github_collector import GitHubCollector
collector = GitHubCollector()
```

**After (동적 로딩)**:
```python
# 런타임 import (importlib)
module = importlib.import_module("collectors.github_collector")
collector_class = getattr(module, "GitHubCollector")
collector = collector_class()
```

동적 로딩은 런타임에 import를 수행하므로 직접 import보다 약간 느립니다.

#### 2. **실행 시간 (실제 ETL 작업)**

ETL 작업 자체의 실행 시간은 리팩토링 전후가 동일합니다.

#### 3. **캐싱 최적화**

Factory는 클래스 캐싱을 사용:

```python
def _import_collector_class(self, class_path):
    if class_path in self._cache:
        return self._cache[class_path]  # 캐시된 클래스 반환

    # 첫 로드만 import 수행
    module = importlib.import_module(module_path)
    collector_class = getattr(module, class_name)
    self._cache[class_path] = collector_class  # 캐싱
    return collector_class
```

같은 Collector를 여러 번 생성해도 첫 번째 로드 이후에는 캐시에서 즉시 반환됩니다.

#### 4. **유지보수 작업**

리팩토링으로 개발 작업 개선:
- 새 Collector 추가: 코드 수정 불필요, YAML만 수정
- 버그 수정: 한 곳만 수정 (전파 오류 감소)
- 테스트: Mock 주입 용이

#### 결론

**런타임 성능**: 유사한 수준 (동적 로딩 오버헤드는 미미함)
**개발 작업**: 개선됨 (확장 용이)

---

## 요약

| 항목 | Before | Phase 5 | Phase 6 (현재) |
|------|--------|---------|----------------|
| **Collector 추가** | 코드 수정 필요 | 코드 수정 필요 | YAML만 수정  |
| **설정 위치** | Python 코드 | Python 코드 | YAML 파일 |
| **클래스 로딩** | 직접 import | 직접 import | 동적 로딩 |
| **런타임 변경** | 불가능 | 불가능 | 가능  |
| **플러그인 지원** | 불가능 | 불가능 | 가능 |
| **우선순위 제어** | 코드 수정 | 코드 수정 | YAML 설정 |
| **실행 성능** | 동일 | 동일 | 동일 |
| **개발 작업** | 여러 파일 수정 | Factory 코드 수정 | 설정만 수정 |

**핵심 메시지**:
- 확장성: 플러그인 방식으로 외부 Collector 로드 가능
- 유지보수: 코드 수정 없이 설정만으로 제어

