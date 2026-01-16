# 테스트 가이드

LearningCollector 프로젝트의 테스트 스위트입니다.

## 테스트 구조

```
tests/
├── fixtures/          # 테스트 데이터
│   ├── ai_chat/      # AI 채팅 마크다운 샘플
│   ├── github/       # GitHub API 응답 샘플
│   └── baekjoon/     # Baekjoon 문제 샘플
├── conftest.py       # pytest 설정 및 공통 픽스처
├── test_basic.py     # 기본 기능 테스트 (17 tests)
├── test_parsers.py   # 파서 모듈 테스트
├── test_integration.py  # 통합 테스트
└── run_all_tests.py  # 전체 테스트 실행 스크립트
```

## 빠른 시작

### 전체 테스트 실행

```bash
python -m pytest tests/ -v
```

### 기본 테스트만 실행

```bash
python -m pytest tests/test_basic.py -v
```

## 테스트 결과 (2024-01-16)

✅ **18개 테스트 모두 통과**

- 기본 기능: 17/17 통과
- 통합 테스트: 1/1 통과

## 주요 검증 항목

✅ AI 제공자 감지 (Claude, ChatGPT, Gemini)
✅ 프로그래밍 언어 감지 (Python, C++, Java, C)
✅ JSON/마크다운 파일 읽기/쓰기
✅ 날짜 형식 변환
✅ 데이터 수집 및 저장

## 참고

- pytest 설정: `pytest.ini`
- 테스트 픽스처: `conftest.py`
- 자세한 내용: [pytest 문서](https://docs.pytest.org/)
