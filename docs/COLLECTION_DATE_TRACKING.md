# 수집 날짜 추적 (Collection Date Tracking)

## 개요

개인 학습 정보 수집 도구는 증분 수집(Incremental Collection)을 지원하기 위해 마지막 수집 날짜를 추적합니다.
이 문서는 날짜 추적 메커니즘과 파일 손실 시 대응 방법을 설명합니다.

## 작동 방식

### 1. 파일 기반 추적 (Primary)

시스템은 `logs/` 디렉토리의 수집 결과 파일명에서 날짜를 추출합니다:

```
logs/
├── collect_result_2026-01-14.json  # 신규 형식
├── collect_result_2026-01-13.json
├── etl_result_2026-01-12.json      # 하위 호환 (구 형식)
└── etl_result_2026-01-11.json
```

**작동 원리:**
- `collect_result_YYYY-MM-DD.json` 또는 `etl_result_YYYY-MM-DD.json` 패턴 탐색
- 파일명에서 날짜를 추출하여 가장 최근 날짜 반환
- 해당 날짜 다음날부터 오늘까지를 수집 범위로 계산

**장점:**
- DB 접근 불필요
- 파일로 직접 확인 가능
- 디버깅 및 수동 수정 용이
- 추가 테이블 불필요

### 2. DB 조회 (Fallback)

파일에서 날짜를 찾을 수 없는 경우 DB의 `learning_artifacts` 테이블을 조회:

```sql
SELECT MAX(artifact_date)
FROM learning.learning_artifacts
WHERE source_type = 'github'  -- 또는 'baekjoon'
```

**사용 시나리오:**
- 로그 파일이 삭제된 경우
- 첫 실행 시
- 로그 디렉토리가 초기화된 경우

## 구현 상세

### 핵심 모듈: `storage/collection_tracker.py`

```python
def get_last_collection_date_from_files() -> Optional[date]:
    """
    로그 파일에서 마지막 수집 날짜 추출

    Returns:
        가장 최근 수집 날짜 (파일이 없으면 None)
    """
    pattern = re.compile(r'(collect_result|etl_result)_(\d{4}-\d{2}-\d{2})\.json')

    dates = []
    for file in LOGS_DIR.glob('*.json'):
        match = pattern.match(file.name)
        if match:
            date_str = match.group(2)
            file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            dates.append(file_date)

    return max(dates) if dates else None


def get_last_collection_date(source_type: str) -> Optional[date]:
    """
    마지막 수집 날짜 조회 (파일 우선, DB fallback)

    1. logs/ 폴더의 파일에서 날짜 추출 (우선)
    2. 파일이 없으면 DB의 learning_artifacts 테이블에서 조회 (fallback)
    """
    # 1. 파일에서 조회
    last_date_from_files = get_last_collection_date_from_files()
    if last_date_from_files:
        return last_date_from_files

    # 2. DB에서 조회
    return query_last_date_from_db(source_type)
```

### 수집 범위 계산

```python
def get_collection_date_range(source_type: str, default_days_back: int = 7) -> tuple[date, date]:
    """
    수집할 날짜 범위 계산

    Returns:
        (start_date, end_date) 튜플
    """
    today = date.today()
    last_date = get_last_collection_date(source_type)

    if last_date:
        start_date = last_date + timedelta(days=1)  # 다음날부터 수집
    else:
        start_date = today - timedelta(days=default_days_back)  # 첫 실행: 7일 전부터

    return (start_date, today)
```

## 파일 손실 시 대응

### 시나리오 1: 로그 파일 전체 삭제

**증상:**
```bash
$ rm logs/*.json
$ python main.py
```

**대응:**
1. 시스템이 자동으로 DB fallback 사용
2. `learning_artifacts` 테이블에서 마지막 수집 날짜 조회
3. 정상적으로 증분 수집 재개

**로그 출력:**
```
[github] 파일에서 날짜를 찾을 수 없어 DB 조회
[github] 마지막 수집 날짜 (DB): 2026-01-13
[github] 수집 범위: 2026-01-14 ~ 2026-01-14
```

### 시나리오 2: DB와 로그 파일 모두 없음 (첫 실행)

**증상:**
- 새로운 환경에 설치
- 데이터가 전혀 없는 상태

**대응:**
1. `get_last_collection_date()` → `None` 반환
2. 기본값 7일 전부터 수집 시작

**로그 출력:**
```
[github] 수집 이력 없음 (첫 실행)
[github] 첫 실행, 7일 전부터 수집: 2026-01-07
[github] 수집 범위: 2026-01-07 ~ 2026-01-14
```

### 시나리오 3: 특정 날짜 강제 재수집

**목적:**
- 특정 기간 누락 데이터 재수집
- 데이터 오류 수정 후 재수집

**방법 1: 로그 파일 조작**
```bash
# 2026-01-10 이후 재수집하려면
$ rm logs/collect_result_2026-01-1[1-4].json

# 다시 실행하면 2026-01-11부터 수집
$ python main.py
```

**방법 2: 특정 날짜 직접 지정**
```bash
# main.py에서 --date 옵션 지원 시
$ python main.py --date 2026-01-10
```

## 문제 해결

### Q1: 수집이 매번 같은 날짜만 반복됩니다

**원인:**
- 커밋/문제가 0개인 날이 계속되어 로그 파일이 생성되지 않음
- 이전에는 이런 문제가 있었으나, 현재는 해결됨

**해결:**
- 현재 시스템은 데이터가 0개여도 `collect_result_*.json` 파일 생성
- 파일명에서 날짜를 추적하므로 문제 없음

### Q2: 로그 파일이 너무 많이 쌓입니다

**권장 사항:**
```bash
# 90일 이전 로그 파일 정리 (cron 등록 권장)
find logs/ -name "*.json" -type f -mtime +90 -delete
```

**주의:**
- 최소 1개 이상의 최근 로그 파일 유지 필요
- 전체 삭제 시 DB fallback 사용되므로 치명적이지 않음

### Q3: 마지막 수집 날짜가 부정확합니다

**진단:**
```bash
# 로그 파일 확인
$ ls -la logs/*.json

# 수동으로 최근 날짜 확인
$ ls -t logs/*.json | head -1
```

**해결:**
```bash
# 1. 잘못된 로그 파일 삭제
$ rm logs/collect_result_2026-01-15.json  # 미래 날짜 등

# 2. 수동으로 날짜 조정 (필요 시)
$ rm logs/collect_result_2026-01-1[2-4].json  # 2026-01-12부터 재수집
```

## 마이그레이션 가이드

### 구 형식 (etl_result_*.json) → 신규 형식 (collect_result_*.json)

**하위 호환성:**
- 시스템은 자동으로 두 형식 모두 인식
- 기존 `etl_result_*.json` 파일 그대로 사용 가능
- 새로운 수집부터 `collect_result_*.json` 형식 사용

**마이그레이션 (선택사항):**
```bash
# 기존 파일을 새 형식으로 변경하려면
$ cd logs/
$ for file in etl_result_*.json; do
    mv "$file" "${file/etl_result/collect_result}"
done
```

**주의:**
- 마이그레이션은 선택사항 (필수 아님)
- 혼재 상태여도 정상 작동

## 모니터링

### 수집 범위 확인
```bash
# 다음 수집 범위 미리보기
$ python -c "
from storage.collection_tracker import get_collection_date_range
start, end = get_collection_date_range('github')
print(f'수집 범위: {start} ~ {end}')
"
```

### 로그 파일 현황
```bash
# 로그 파일 개수 및 날짜 범위
$ ls logs/*.json | wc -l
$ ls logs/*.json | head -1  # 가장 오래된 파일
$ ls logs/*.json | tail -1  # 가장 최근 파일
```

## 관련 파일

- `storage/collection_tracker.py` - 날짜 추적 핵심 로직
- `collectors/github_collector.py` - GitHub 수집 시 사용
- `collectors/baekjoon_collector.py` - 백준 수집 시 사용
- `main.py` - 수집 결과 파일 생성 (303번째 줄)
- `storage/db_utils.py` - 하위 호환 래퍼 (deprecated)

## 참고 자료

- [아키텍처 문서](ARCHITECTURE_EVOLUTION.md)
- [데이터베이스 가이드](DATABASE_GUIDE.md)
- [설치 가이드](../INSTALL.md)
