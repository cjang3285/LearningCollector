# 개인 학습 정보 수집 자동화 도구

SOLID 원칙 기반 확장 가능한 학습 데이터 수집 파이프라인.

모든 학습 활동(GitHub 커밋, AI 채팅, 백준 문제풀이)을 자동으로 수집하여 PostgreSQL DB에 저장합니다.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![SOLID](https://img.shields.io/badge/Architecture-SOLID-orange.svg)](docs/DESIGN_PATTERNS.md)

---

## 주요 특징

### 핵심 기능

- **GitHub 커밋 수집**: REST API로 커밋 메타데이터 및 diff 수집
- **AI 채팅 수집**: Claude, ChatGPT, Gemini 마크다운 파싱
- **백준 풀이 수집**: 백준허브 연동 레포에서 푸시된 문제 풀이 수집
- **PostgreSQL 저장**: 추출된 데이터를 구조화하여 DB 저장 (JSONB 활용)

### 아키텍처

- **SOLID 원칙 적용**: 유지보수성, 확장성, 테스트 용이성
- **설정 기반 확장**: 새 Collector 추가 시 YAML 파일만 수정
- **플러그인 시스템**: 외부 Collector 로드 가능
- **동적 클래스 로딩**: 런타임에 Collector 추가/제거
- **하위 호환성**: 기존 코드 수정 없이 확장

---

## 빠른 시작

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
psql -h localhost -U postgres -d my_blog -f scripts/installation/create-schema.sql
```

상세 설치 가이드: [INSTALL.md](INSTALL.md)

### 2. 실행

```bash
# 기본 실행 (GitHub + Baekjoon + AI Chat 자동 스캔)
python main.py

# GitHub만 제외
python main.py --skip-github

# 특정 날짜
python main.py --date 2025-12-25

# Claude ZIP 첫 임포트
python main.py --import-zip --all
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

## 문서

### 핵심 문서

| 문서 | 설명 |
|------|------|
| [설치 가이드](INSTALL.md) | E2E 설치 및 설정 |
| [아키텍처 진화](docs/ARCHITECTURE_EVOLUTION.md) | 리팩토링 전후 비교 |
| [설계 패턴](docs/DESIGN_PATTERNS.md) | Factory, Registry, 동적 로딩 설명 |
| [DB 가이드](docs/DATABASE_GUIDE.md) | DB 스키마 및 설정 |

### 사용 가이드

- [Standalone 가이드](docs/STANDALONE_GUIDE.md) - 현재 사용 중인 모드
- [Cron 설정](docs/CRON_GUIDE.md) - 자동화 설정

---

## 프로젝트 구조

```
LearningETL/
├── main.py                     # 메인 실행 파일 (Factory 사용)
│
├── interfaces/                 # 인터페이스 계층 (SOLID - DIP, ISP)
│   ├── __init__.py             # IParser, ISaver, ICollector
│   ├── contexts.py             # CollectionContext
│   └── results.py              # CollectionResult
│
├── factories/                  # 객체 생성 팩토리 (SOLID - OCP)
│   ├── __init__.py
│   └── collector_factory.py    # 동적 Collector 생성
│
├── collectors/                 # 수집 오케스트레이터 (ICollector 구현)
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
│   ├── collectors.yaml         # Collector 설정
│   └── collector_config.py     # 설정 로더
│
├── bulk_import/                # Claude ZIP 일괄 임포트
│   ├── converters/
│   ├── formatters/
│   └── parsers/
│
├── cli/                        # CLI 쿼리 도구
├── scripts/                    # 운영 스크립트
├── tests/                      # 테스트
│
└── docs/                       # 문서
    ├── DESIGN_PATTERNS.md
    ├── ARCHITECTURE_EVOLUTION.md
    └── ...
```

---

## 새로운 Collector 추가 방법

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
  notion:
    enabled: true
    class_path: "collectors.notion_collector.NotionCollector"
    priority: 25
    description: "Notion 페이지 수집"
```

---

## SOLID 원칙 적용

| 원칙 | 적용 방법 | 효과 |
|------|-----------|------|
| **SRP** | Collector는 조율만, Parser는 파싱만, Saver는 저장만 | 단일 책임 |
| **OCP** | YAML 설정으로 확장, 코드 수정 불필요 | 확장에 개방 |
| **LSP** | 모든 Collector가 `ICollector` 구현 | 다형성 |
| **ISP** | 최소한의 메서드만 정의 (3개) | 인터페이스 부담 감소 |
| **DIP** | 인터페이스에 의존, 구체 클래스 교체 가능 | 테스트 용이 (Mock 주입) |

상세 설명: [DESIGN_PATTERNS.md](docs/DESIGN_PATTERNS.md)

---

## 자동화 설정

### 실시간 파일 감지 (Daemon)

AI 채팅 파일 자동 수집 (파일 감지 즉시 처리)

```bash
# 설치
bash scripts/installation/install-daemon.sh

# 시작
sudo systemctl start learningetl

# 상태 확인
sudo systemctl status learningetl
```

### 매일 자정 전체 스캔 (systemd timer 권장)

```bash
# 설치
bash scripts/installation/setup-daily-timer.sh

# 상태 확인
systemctl list-timers learningetl-daily.timer

# 로그 확인
journalctl -u learningetl-daily.service -f
```

장점:
- 시스템 재부팅 시 놓친 작업 자동 실행 (Persistent=true)
- journalctl 통합 로그 관리
- 실행 상태 추적 및 실패 알림
- 의존성 관리 (PostgreSQL 준비 후 실행)

---

## 데이터베이스

### 스키마

```sql
learning.learning_artifacts          -- 모든 학습 활동 메타데이터
learning.github_commits              -- GitHub 커밋 상세
learning.baekjoon_solutions          -- 백준 문제풀이
learning.ai_chat_conversations       -- AI Chat (Claude/ChatGPT/Gemini)
```

JSONB 활용: 유연한 메타데이터 저장 + GIN 인덱스로 검색

상세: [DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md)

---

## 자주 쓰는 명령어

### AI 채팅 파일 감지 안 됨

1. 파일명 확인: `Claude-`, `ChatGPT-`, `Gemini-`로 시작하는지
2. 확장자 확인: `.md` 파일인지
3. 다운로드 폴더 확인: `.env`에 설정한 경로 확인

### DB 연결

```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# DB 접속 테스트
psql -h localhost -U postgres -d my_blog
```

---

## 의존성

- Python 3.8+
- PostgreSQL 12+
- GitHub Personal Access Token
- 백준허브 연동 레포 - [BaekjoonHub](https://github.com/BaekjoonHub/BaekjoonHub)
- AI chat exporter chrome extensions
  - [Claude Exporter](https://chromewebstore.google.com/detail/claude-exporter/elhmfakncmnghlnabnolalcjkdpfjnin)
  - [ChatGPT Exporter](https://chromewebstore.google.com/detail/chatgpt-exporter/pldlpacbeonbjfhlongcdflcgfcnglkl)
  - [Gemini Chat Exporter](https://chromewebstore.google.com/detail/gemini-chat-exporter/bhmoomcflhcfhingnjjieheeadmdefkc)

---

## 아키텍처 히스토리

### 현재: 설정 기반 + 동적 로딩

- YAML 설정 파일로 Collector 관리
- 동적 클래스 로딩 (importlib)
- 런타임 활성화/비활성화
- 플러그인 시스템 기반

### Phase 1~5: SOLID 리팩토링

- Phase 1: 인터페이스 정의 (IParser, ISaver, ICollector)
- Phase 2: Parser 리팩토링 (DIP 적용)
- Phase 3: Saver 리팩토링 (DIP 적용)
- Phase 4: Collector 리팩토링 (SRP, LSP 적용)
- Phase 5: CollectorFactory 도입 (OCP 적용)

### Phase 0: 리팩토링 전

- 절차적 프로그래밍
- 하드코딩

전체 변화 과정: [ARCHITECTURE_EVOLUTION.md](docs/ARCHITECTURE_EVOLUTION.md)

---

## 기여

Issues와 Pull Requests를 환영합니다.

---

## 라이선스

MIT License

---

## 관련 프로젝트

- [BaekjoonHub](https://github.com/BaekjoonHub/BaekjoonHub) - 백준 해결 문제를 지정한 레포지터리로 자동 커밋 푸시
- [Claude Exporter](https://github.com/jasonkneen/claude-exporter) - Claude 대화 내보내기
- [ChatGPT Exporter](https://github.com/pionxzh/chatgpt-exporter) - ChatGPT 대화 내보내기
- [Gemini Chat Exporter](https://github.com/jiajunhang/gemini-chat-exporter) - Gemini 대화 내보내기

---

<div align="center">

Made with SOLID principles

[Documentation](docs/) | [Report Bug](https://github.com/cjang3285/LearningETL/issues) | [Request Feature](https://github.com/cjang3285/LearningETL/issues)

</div>
