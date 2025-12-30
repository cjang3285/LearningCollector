# Learning Artifacts ETL Pipeline

> **SOLID 원칙 기반** 확장 가능한 학습 데이터 수집 파이프라인

모든 학습 활동(GitHub 커밋, AI 채팅, 백준 문제풀이)을 자동으로 수집하여 PostgreSQL DB에 저장합니다.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![SOLID](https://img.shields.io/badge/Architecture-SOLID-orange.svg)](docs/DESIGN_PATTERNS.md)

---

## ✨ 주요 특징

### 🎯 핵심 기능

- **GitHub 커밋 수집**: REST API로 커밋 메타데이터 및 diff 수집 (Co-Author 추적 포함)
- **AI 채팅 수집**: Claude, ChatGPT, Gemini 마크다운 자동 파싱
- **백준 풀이 수집**: 백준허브 연동 레포에서 자동 푸시된 문제 풀이 수집
- **PostgreSQL 저장**: 모든 데이터를 구조화하여 DB 저장 (JSONB 활용)

### 🏗️ 아키텍처 강점

- ✅ **SOLID 원칙 완전 적용**: 유지보수성, 확장성, 테스트 용이성
- ✅ **설정 기반 확장**: 새 Collector 추가 시 **YAML 파일만 수정** (코드 수정 불필요!)
- ✅ **플러그인 시스템**: 외부 Collector 로드 가능
- ✅ **동적 클래스 로딩**: 런타임에 Collector 추가/제거
- ✅ **완벽한 하위 호환성**: 기존 코드 전혀 수정 안 함

---

## 🚀 빠른 시작

### 1. 설치

```bash
# 클론
git clone https://github.com/cjang3285/LearningETL.git
cd LearningETL

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
nano .env  # GITHUB_TOKEN, DB 정보 입력

# DB 스키마 생성
psql -h localhost -U postgres -d my_blog -f scripts/create-schema.sql
```

**상세 설치 가이드**: [📖 INSTALL.md](INSTALL.md)

### 2. 실행

```bash
# GitHub + Baekjoon 수집
python main.py

# AI Chat 포함 (Downloads 폴더 스캔)
python main.py --ai-chat-scan

# 특정 날짜
python main.py --date 2025-12-25
```

### 3. 데이터 조회

```bash
# 통계
python -m cli stats

# AI Chat 목록
python -m cli list ai-chat

# 특정 대화 보기
python -m cli show ai-chat 1
```

---

## 📚 문서

### 📖 핵심 문서

| 문서 | 설명 |
|------|------|
| [🔧 설치 가이드](INSTALL.md) | E2E 설치 및 설정 |
| [🏗️ 아키텍처 진화](docs/ARCHITECTURE_EVOLUTION.md) | SOLID 리팩토링 전후 비교 |
| [🧩 설계 패턴](docs/DESIGN_PATTERNS.md) | Factory, Registry, 동적 로딩 설명 |
| [🗄️ DB 가이드](docs/DATABASE_GUIDE.md) | DB 스키마 및 설정 |
| [📋 리팩토링 계획](docs/REFACTORING_PLAN.md) | Phase 1~6 상세 계획 |

### 🎓 더 알아보기

- [Standalone 가이드](docs/standalone-guide.md) - 현재 사용 중인 모드
- [NAS 아키텍처](docs/NAS_ARCHITECTURE.md) - 향후 구현 설계

---

## 🏗️ 프로젝트 구조 (리팩토링 후)

```
LearningETL/
├── main.py                     # ✅ 메인 실행 파일 (Factory 사용)
│
├── interfaces/                 # ✨ 인터페이스 계층 (SOLID - DIP, ISP)
│   ├── __init__.py             # IParser, ISaver, ICollector
│   ├── contexts.py             # CollectionContext
│   └── results.py              # CollectionResult
│
├── factories/                  # ✨ 객체 생성 팩토리 (SOLID - OCP)
│   ├── __init__.py
│   └── collector_factory.py    # 동적 Collector 생성
│
├── collectors/                 # ETL 오케스트레이터 (ICollector 구현)
│   ├── github_collector.py     # Export → Parse → Save 조율
│   ├── baekjoon_collector.py
│   └── ai_chat_collector.py
│
├── parse/                      # 데이터 파싱 (IParser 구현)
│   ├── github_parse.py
│   ├── baekjoon_parse.py
│   └── ai_chat_parse.py
│
├── storage/                    # 데이터 저장 (ISaver 구현)
│   ├── base_saver.py           # BaseSaver (공통 로직)
│   ├── github_saver.py
│   ├── baekjoon_saver.py
│   └── ai_chat_saver.py
│
├── export/                     # 데이터 수집
│   ├── github_export.py
│   ├── baekjoon_export.py
│   └── ai_chat_export.py
│
├── config/                     # 설정 관리
│   ├── settings.py
│   ├── logging_config.py
│   ├── collectors.yaml         # ✨ Collector 설정 (새 Collector 추가 시 여기만 수정!)
│   └── collector_config.py     # ✨ 설정 로더
│
├── cli/                        # CLI 쿼리 도구
├── scripts/                    # 운영 스크립트
├── migration/                  # Claude ZIP 마이그레이션
├── tests/                      # 테스트 (Mock 주입 가능)
│
└── docs/                       # 📚 문서
    ├── DESIGN_PATTERNS.md      # ✨ 설계 패턴 설명
    ├── ARCHITECTURE_EVOLUTION.md  # ✨ 리팩토링 전후 비교
    └── ...
```

---

## 🎨 새로운 Collector 추가 방법

### Before 리팩토링 (5분, 5개 파일 수정)

1. `collectors/new_collector.py` 작성
2. `main.py` 수정 (import 추가)
3. `__init__` 수정 (인스턴스 생성)
4. `run()` 메서드 수정 (실행 로직)
5. 환경변수 설정

### After 리팩토링 (30초, 1개 파일 수정) ✨

**1. Collector 클래스 작성** (ICollector 인터페이스 구현)

```python
# collectors/notion_collector.py
from interfaces import ICollector, CollectionContext, CollectionResult

class NotionCollector(ICollector):
    def collect(self, context: CollectionContext) -> CollectionResult:
        # 수집 로직
        return CollectionResult(success=True, ...)

    def should_run(self, context: CollectionContext) -> bool:
        return True

    def get_name(self) -> str:
        return "notion"
```

**2. YAML 설정 파일에 추가**

```yaml
# config/collectors.yaml
collectors:
  notion:  # 이 한 줄만 추가하면 끝!
    enabled: true
    class_path: "collectors.notion_collector.NotionCollector"
    priority: 25
    description: "Notion 페이지 수집"
```

**끝!** 코드 수정 없이 즉시 사용 가능합니다.

---

## 🧩 SOLID 원칙 적용

| 원칙 | 적용 방법 | 효과 |
|------|-----------|------|
| **SRP** | Collector는 조율만, Parser는 파싱만, Saver는 저장만 | 책임 명확, 유지보수 용이 |
| **OCP** | YAML 설정으로 확장, 코드 수정 불필요 | 새 Collector 추가 시간 **10배 단축** |
| **LSP** | 모든 Collector가 `ICollector` 구현 | 다형성, 일관된 인터페이스 |
| **ISP** | 최소한의 메서드만 정의 (3개) | 인터페이스 부담 감소 |
| **DIP** | 인터페이스에 의존, 구체 클래스 교체 가능 | 테스트 용이 (Mock 주입) |

**상세 설명**: [📖 DESIGN_PATTERNS.md](docs/DESIGN_PATTERNS.md)

---

## 🔧 자동화 설정

### 실시간 파일 감지 (Daemon)

AI 채팅 파일 자동 수집 (파일 감지 즉시 처리)

```bash
# 설치
bash scripts/install-daemon.sh

# 시작
sudo systemctl start learningetl

# 상태 확인
sudo systemctl status learningetl
```

### 매일 자정 전체 스캔 (systemd timer 추천 ⭐)

```bash
# 설치
bash scripts/setup-daily-timer.sh

# 상태 확인
systemctl list-timers learningetl-daily.timer

# 로그 확인
journalctl -u learningetl-daily.service -f
```

**장점**:
- ✅ 시스템 재부팅 시 놓친 작업 자동 실행 (Persistent=true)
- ✅ journalctl 통합 로그 관리
- ✅ 실행 상태 추적 및 실패 알림
- ✅ 의존성 관리 (PostgreSQL 준비 후 실행)

---

## 💾 데이터베이스

### 스키마

```sql
learning.learning_artifacts          -- 모든 학습 활동 메타데이터
learning.github_commits              -- GitHub 커밋 상세
learning.baekjoon_solutions          -- 백준 문제풀이
learning.ai_chat_conversations       -- AI Chat (Claude/ChatGPT/Gemini)
```

**JSONB 활용**: 유연한 메타데이터 저장 + GIN 인덱스로 빠른 검색

**상세**: [📖 DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md)

---

## 📊 성능

| 항목 | 측정값 | 참고 |
|------|--------|------|
| **초기화 오버헤드** | +1ms | 동적 로딩 비용 (무시 가능) |
| **실행 시간** | 변화 없음 | 병목은 네트워크/DB (수 초) |
| **클래스 캐싱** | 첫 로드만 1ms, 이후 0ms | Factory 내부 캐싱 |
| **개발 속도** | **10배 향상** | 새 Collector 추가 5분→30초 |

**결론**: 런타임 성능 영향 없음 (0.05%), 개발 생산성 대폭 향상

**상세 분석**: [📖 DESIGN_PATTERNS.md#성능-영향-분석](docs/DESIGN_PATTERNS.md#성능-영향-분석)

---

## 🔮 미래 확장 방향

### 즉시 가능

- ✅ **외부 플러그인 개발** (Notion, Slack 등)
- ✅ **웹 UI 기반 설정 관리** (재시작 없이 활성화/비활성화)
- ✅ **성능 모니터링** (Prometheus/Grafana)

### 향후 계획

- 🎯 **조건부 실행** (스케줄, 네트워크 상태 기반)
- 🎯 **Collector 의존성 관리** (DAG 기반 실행 순서)
- 🎯 **분산 실행** (Celery/RQ 연동)
- 🎯 **설정 버전 관리** (스키마 변경 시 마이그레이션)

**상세 계획**: [📖 DESIGN_PATTERNS.md#미래-확장-방향](docs/DESIGN_PATTERNS.md#미래-확장-방향)

---

## 🐛 트러블슈팅

### GitHub API Rate Limit

```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

### AI 채팅 파일 감지 안 됨

1. 파일명 확인: `Claude-`, `ChatGPT-`, `Gemini-`로 시작하는지
2. 확장자 확인: `.md` 파일인지
3. 다운로드 폴더 확인: `.env`에 설정한 경로 확인

### DB 연결 실패

```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# DB 접속 테스트
psql -h localhost -U postgres -d my_blog
```

---

## 📋 전제조건

- Python 3.8+
- PostgreSQL 12+
- GitHub Personal Access Token
- **백준허브 연동 레포** (선택) - [BaekjoonHub](https://github.com/BaekjoonHub/BaekjoonHub)
- **AI 채팅 브라우저 확장** (선택):
  - [Claude Exporter](https://chromewebstore.google.com/detail/claude-exporter/elhmfakncmnghlnabnolalcjkdpfjnin)
  - [ChatGPT Exporter](https://chromewebstore.google.com/detail/chatgpt-exporter/pldlpacbeonbjfhlongcdflcgfcnglkl)
  - [Gemini Chat Exporter](https://chromewebstore.google.com/detail/gemini-chat-exporter/bhmoomcflhcfhingnjjieheeadmdefkc)

---

## 📖 아키텍처 히스토리

### Phase 6 (현재): 설정 기반 + 동적 로딩

- ✅ YAML 설정 파일로 Collector 관리
- ✅ 동적 클래스 로딩 (importlib)
- ✅ 런타임 활성화/비활성화
- ✅ 플러그인 시스템 기반 마련

### Phase 1~5: SOLID 리팩토링

- Phase 1: 인터페이스 정의 (IParser, ISaver, ICollector)
- Phase 2: Parser 리팩토링 (DIP 적용)
- Phase 3: Saver 리팩토링 (DIP 적용)
- Phase 4: Collector 리팩토링 (SRP, LSP 적용)
- Phase 5: CollectorFactory 도입 (OCP 적용)

### Phase 0: Legacy (리팩토링 전)

- 절차적 프로그래밍
- 하드코딩, 중복 코드
- 테스트 불가능

**전체 변화 과정**: [📖 ARCHITECTURE_EVOLUTION.md](docs/ARCHITECTURE_EVOLUTION.md)

---

## 🤝 기여

Issues와 Pull Requests를 환영합니다!

새로운 Collector를 개발하고 싶다면:
1. `ICollector` 인터페이스 구현
2. `collectors.yaml`에 등록
3. PR 제출

**가이드**: [📖 ARCHITECTURE_EVOLUTION.md#마이그레이션-가이드](docs/ARCHITECTURE_EVOLUTION.md#마이그레이션-가이드)

---

## 📄 라이선스

MIT License

---

## 🔗 관련 프로젝트

- [BaekjoonHub](https://github.com/BaekjoonHub/BaekjoonHub) - 백준 문제 자동 커밋
- [Claude Exporter](https://github.com/jasonkneen/claude-exporter) - Claude 대화 내보내기
- [ChatGPT Exporter](https://github.com/pionxzh/chatgpt-exporter) - ChatGPT 대화 내보내기
- [Gemini Chat Exporter](https://github.com/jiajunhang/gemini-chat-exporter) - Gemini 대화 내보내기

---

<div align="center">

**Made with ❤️ using SOLID principles**

[📖 Documentation](docs/) | [🐛 Report Bug](https://github.com/cjang3285/LearningETL/issues) | [✨ Request Feature](https://github.com/cjang3285/LearningETL/issues)

</div>
