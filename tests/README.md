# Learning ETL 테스트 가이드

전체 코드베이스의 단위 테스트 및 통합 테스트를 포함합니다.

## 📁 테스트 구조

```
tests/
├── __init__.py              # 테스트 패키지
├── test_config.py           # Config 모듈 테스트
├── test_export.py           # Export 모듈 테스트
├── test_parse.py            # Parse 모듈 테스트
├── test_storage.py          # Storage 모듈 테스트
├── test_collectors.py       # Collectors 통합 테스트
├── test_main.py             # Main ETL 파이프라인 테스트
├── run_all_tests.py         # 통합 테스트 러너 (TestSuite + TestRunner)
├── test_github.py           # GitHub 개별 테스트 (레거시)
├── test_db_save.py          # DB 저장 개별 테스트 (레거시)
└── README.md                # 이 파일
```

## 🔧 사전 준비

### 1. 필수 패키지 설치

```bash
pip install requests psycopg2-binary selenium
```

### 2. 환경변수 설정

```bash
export GITHUB_TOKEN="ghp_your_token_here"
export GITHUB_USERNAME="your_username"
export BAEKJOON_HANDLE="your_handle"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="my_blog"
export DB_USER="postgres"
export DB_PASSWORD="your_password"
```

## 🚀 테스트 실행 방법

### 1. 전체 테스트 실행 (권장)

```bash
# TestSuite + TestRunner 사용
python tests/run_all_tests.py

# 상세 레벨 조정 (0: 최소, 1: 기본, 2: 상세)
python tests/run_all_tests.py -v 2
```

### 2. 특정 모듈만 테스트

```bash
# Config 모듈만 테스트
python tests/run_all_tests.py -m config

# Export 모듈만 테스트
python tests/run_all_tests.py -m export

# Parse 모듈만 테스트
python tests/run_all_tests.py -m parse

# Storage 모듈만 테스트
python tests/run_all_tests.py -m storage

# Collectors 모듈만 테스트
python tests/run_all_tests.py -m collectors

# Main ETL 파이프라인만 테스트
python tests/run_all_tests.py -m main
```

### 3. Python unittest 직접 사용

```bash
# 전체 테스트
python -m unittest discover -s tests -p "test_*.py" -v

# 특정 테스트 파일만
python -m unittest tests.test_config -v

# 특정 테스트 클래스만
python -m unittest tests.test_config.TestConfigSettings -v

# 특정 테스트 메서드만
python -m unittest tests.test_config.TestConfigSettings.test_github_settings -v
```

### 4. 개별 테스트 파일 직접 실행

```bash
# 각 테스트 파일을 직접 실행
python tests/test_config.py
python tests/test_export.py
python tests/test_parse.py
python tests/test_storage.py
python tests/test_collectors.py
python tests/test_main.py
```

## 📊 테스트 레이어

### Layer 1: Config 테스트
- **파일**: `test_config.py`
- **테스트 대상**: `config/settings.py`
- **테스트 내용**:
  - 프로젝트 루트 및 디렉토리 존재 확인
  - GitHub/Baekjoon 설정값 확인
  - DB 설정 반환 함수 테스트
  - 로그 파일 경로 생성 테스트

### Layer 2: Export 테스트
- **파일**: `test_export.py`
- **테스트 대상**: `export/github_export.py`, `export/baekjoon_export.py`
- **테스트 내용**:
  - Exporter 초기화 (토큰/핸들 검증)
  - API 호출 (Mock 사용)
  - 데이터 수집 결과 검증

### Layer 3: Parse 테스트
- **파일**: `test_parse.py`
- **테스트 대상**: `parse/github_parse.py`, `parse/claude_parse.py`, `parse/baekjoon_parse.py`
- **테스트 내용**:
  - Parser 초기화
  - 빈 데이터 파싱
  - 샘플 데이터 파싱 및 구조화

### Layer 4: Storage 테스트
- **파일**: `test_storage.py`
- **테스트 대상**: `storage/*.py`
- **테스트 내용**:
  - BaseSaver 초기화 및 DB 설정
  - 각 Saver (GitHub, Claude, Baekjoon, Artifact) 초기화
  - DB 저장 로직 (Mock DB 사용)
  - 파일 경로 생성 로직

### Layer 5: Collectors 테스트
- **파일**: `test_collectors.py`
- **테스트 대상**: `collectors/*.py`
- **테스트 내용**:
  - Collector 초기화 (Export + Parse + Storage 통합)
  - 전체 수집 워크플로우 (Mock 사용)
  - 에러 처리 및 결과 반환

### Layer 6: Main ETL 테스트
- **파일**: `test_main.py`
- **테스트 대상**: `main.py`
- **테스트 내용**:
  - LearningCollector 초기화
  - 전체 ETL 파이프라인 실행
  - 각 Collector 활성화/비활성화
  - 결과 요약 생성

## 🧪 테스트 전략

### 1. 단위 테스트 (Unit Tests)
- **Layer 1-4**: 각 모듈의 클래스와 함수를 독립적으로 테스트
- **Mock 사용**: 외부 의존성 (API, DB)은 Mock으로 대체
- **빠른 실행**: 네트워크/DB 없이 빠르게 실행

### 2. 통합 테스트 (Integration Tests)
- **Layer 5-6**: 여러 모듈이 함께 작동하는지 테스트
- **워크플로우 검증**: Export → Parse → Storage 전체 흐름
- **실제 의존성**: 일부 테스트는 실제 API/DB 사용 (선택적)

### 3. Mock vs Real
- **기본 전략**: Mock을 사용하여 빠르고 안정적인 테스트
- **실제 테스트**: `test_github.py`, `test_db_save.py` (레거시)
- **환경 분리**: 환경변수로 Mock/Real 전환 가능

## 📈 테스트 결과 예시

```
======================================================================
테스트 스위트 구성 중...
======================================================================

[1/6] Config 모듈 테스트 추가
[2/6] Export 모듈 테스트 추가
[3/6] Parse 모듈 테스트 추가
[4/6] Storage 모듈 테스트 추가
[5/6] Collectors 모듈 테스트 추가
[6/6] Main ETL 파이프라인 테스트 추가

테스트 스위트 구성 완료!
총 테스트 케이스 수: 45

======================================================================
테스트 실행 시작
======================================================================

test_baekjoon_settings (test_config.TestConfigSettings) ... ok
test_db_config (test_config.TestConfigSettings) ... ok
test_directories_created (test_config.TestConfigSettings) ... ok
...
(중략)
...

======================================================================
테스트 결과 요약
======================================================================
실행된 테스트: 45
성공: 40
실패: 0
에러: 0
스킵: 5

✓ 모든 테스트 통과!
```

## 🐛 트러블슈팅

### 1. ModuleNotFoundError: No module named 'selenium'

```bash
pip install selenium
```

### 2. GITHUB_TOKEN not set

```bash
export GITHUB_TOKEN="your_token"
```

또는 테스트가 자동으로 스킵됩니다.

### 3. DB 연결 실패

Storage 테스트는 Mock DB를 사용하므로 실제 DB 없이도 실행 가능합니다.
실제 DB 테스트는 `test_db_save.py`를 사용하세요.

## 📚 참고

- Python unittest 문서: https://docs.python.org/3/library/unittest.html
- TestSuite 사용법: https://docs.python.org/3/library/unittest.html#unittest.TestSuite
- Mock 사용법: https://docs.python.org/3/library/unittest.mock.html
