# SOLID 원칙 리팩토링 계획

## 현재 코드베이스 문제점 분석

### 1. Single Responsibility Principle (SRP) 위반

**문제**: Collector 클래스들이 너무 많은 책임을 가짐

현재 구조:
```python
class AIChatCollector:
    def __init__(self):
        self.parser = AIMarkdownParser()     # 파싱 책임
        self.saver = AIChatSaver()           # 저장 책임

    def collect_from_files(self, files):     # 수집 + 조율 책임
        # 1. 파싱
        conversations = self.parser.parse_multiple(files)
        # 2. 저장
        artifact_ids = self.saver.save_all(conversations)
        # 3. 결과 취합
        return result
```

**책임**:
- ✅ 데이터 수집 (Export)
- ✅ 데이터 파싱 (Parse)
- ✅ 데이터 저장 (Save)
- ✅ 워크플로우 조율

**리팩토링 방향**:
- Collector는 **워크플로우 조율**만 담당
- Parser, Saver는 인터페이스에 의존 (DIP)

---

### 2. Open/Closed Principle (OCP) 위반

**문제**: 새로운 데이터 소스 추가 시 기존 코드 수정 필요

현재 `main.py`:
```python
class LearningETL:
    def __init__(self):
        self.github_collector = GitHubCollector() if COLLECT_GITHUB else None
        self.baekjoon_collector = BaekjoonCollector() if COLLECT_BAEKJOON else None
        self.ai_chat_collector = AIChatCollector()

    def run(self, ...):
        # GitHub 수집
        if COLLECT_GITHUB:
            github_result = self.github_collector.collect(...)

        # Baekjoon 수집
        if COLLECT_BAEKJOON:
            baekjoon_result = self.baekjoon_collector.collect(...)

        # AI Chat 수집
        if ai_chat_scan:
            ai_chat_result = self.ai_chat_collector.collect(...)
```

**문제점**:
- 새로운 collector 추가 시 `__init__`, `run` 모두 수정 필요
- 확장에 닫혀있음 (OCP 위반)

**리팩토링 방향**:
- Collector Registry 패턴
- Factory 패턴으로 동적 생성

---

### 3. Dependency Inversion Principle (DIP) 위반

**문제**: 구체 클래스에 직접 의존

현재:
```python
class AIChatCollector:
    def __init__(self):
        self.parser = AIMarkdownParser()  # 구체 클래스에 의존
        self.saver = AIChatSaver()        # 구체 클래스에 의존
```

**리팩토링 방향**:
```python
# 추상 인터페이스
class IParser(ABC):
    @abstractmethod
    def parse_multiple(self, files: List[str]) -> List[Dict]:
        pass

class ISaver(ABC):
    @abstractmethod
    def save_all(self, data: List[Dict], date: date) -> List[int]:
        pass

# Collector는 인터페이스에 의존
class AIChatCollector:
    def __init__(self, parser: IParser, saver: ISaver):
        self.parser = parser
        self.saver = saver
```

---

### 4. Liskov Substitution Principle (LSP)

**현재 상태**: Collector들이 공통 인터페이스 없음

- `GitHubCollector.collect(target_date, all_dates)`
- `AIChatCollector.collect_from_files(file_paths, target_date)`
- `BaekjoonCollector.collect(target_date)`

**문제점**: 다형성 활용 불가, 일관된 인터페이스 없음

**리팩토링 방향**:
```python
class ICollector(ABC):
    @abstractmethod
    def collect(self, context: CollectionContext) -> CollectionResult:
        pass
```

---

### 5. Interface Segregation Principle (ISP)

**현재 상태**: 큰 문제 없음 (각 클래스가 필요한 메서드만 구현)

---

## 리팩토링 우선순위

### Phase 1: 인터페이스 정의 (기초 작업)
- [ ] `interfaces/` 폴더 생성
- [ ] `IParser` 인터페이스 정의
- [ ] `ISaver` 인터페이스 정의
- [ ] `ICollector` 인터페이스 정의
- [ ] `IExporter` 인터페이스 정의

### Phase 2: Parser 리팩토링 (DIP 적용)
- [ ] `AIMarkdownParser` → `IParser` 구현
- [ ] `GitHubParser` → `IParser` 구현
- [ ] `BaekjoonParser` → `IParser` 구현
- [ ] 기존 코드 동작 테스트

### Phase 3: Saver 리팩토링 (DIP 적용)
- [ ] `AIChatSaver` → `ISaver` 구현
- [ ] `GitHubSaver` → `ISaver` 구현
- [ ] `BaekjoonSaver` → `ISaver` 구현
- [ ] 기존 코드 동작 테스트

### Phase 4: Collector 리팩토링 (SRP, LSP 적용)
- [ ] `AIChatCollector` → `ICollector` 구현, 의존성 주입 적용
- [ ] `GitHubCollector` → `ICollector` 구현, 의존성 주입 적용
- [ ] `BaekjoonCollector` → `ICollector` 구현, 의존성 주입 적용
- [ ] 기존 코드 동작 테스트

### Phase 5: CollectorFactory 구현 (OCP 적용)
- [ ] `CollectorFactory` 생성
- [ ] `CollectorRegistry` 패턴 구현
- [ ] `main.py` 리팩토링 (동적 Collector 생성)
- [ ] 기존 코드 동작 테스트

### Phase 6: 설정 기반 Collector 관리
- [ ] YAML/JSON 설정 파일로 Collector 관리
- [ ] 런타임에 Collector 활성화/비활성화
- [ ] 기존 코드 동작 테스트

---

## 예상 리팩토링 후 구조

### 디렉토리 구조
```
LearningETL/
├── interfaces/          # 새로 추가
│   ├── i_parser.py
│   ├── i_saver.py
│   ├── i_collector.py
│   └── i_exporter.py
├── collectors/          # 리팩토링
│   ├── ai_chat_collector.py
│   ├── github_collector.py
│   ├── baekjoon_collector.py
│   └── factory.py       # 새로 추가
├── parse/               # IParser 구현체
├── storage/             # ISaver 구현체
├── export/              # IExporter 구현체
└── config/
    └── collectors.yaml  # 새로 추가
```

### 사용 예시

**Before**:
```python
# main.py
class LearningETL:
    def __init__(self):
        self.github_collector = GitHubCollector()
        self.ai_chat_collector = AIChatCollector()

    def run(self):
        if COLLECT_GITHUB:
            self.github_collector.collect(...)
        if ai_chat_scan:
            self.ai_chat_collector.collect_from_files(...)
```

**After**:
```python
# main.py
class LearningETL:
    def __init__(self, config: Config):
        self.factory = CollectorFactory(config)
        self.collectors = self.factory.create_active_collectors()

    def run(self, context: CollectionContext):
        results = []
        for collector in self.collectors:
            if collector.should_run(context):
                result = collector.collect(context)
                results.append(result)
        return results
```

---

## 리팩토링 원칙

1. **점진적 리팩토링**: 한 번에 하나씩 변경
2. **테스트 우선**: 각 Phase 후 기존 동작 유지 확인
3. **하위 호환성**: 기존 CLI/API 유지
4. **문서화**: 변경 사항 문서 업데이트

---

## 다음 단계

Phase 1부터 시작: 인터페이스 정의
