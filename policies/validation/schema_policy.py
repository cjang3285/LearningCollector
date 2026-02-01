"""
JSON 스키마 정책 정의
각 JSON 타입별 필수 필드와 정규식 패턴
"""
import re
from typing import Dict, List, Tuple, Any


class SchemaPolicy:
    """JSON 스키마 정책 클래스"""

    # 공통 정규식 패턴
    ISO_8601_PATTERN = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'
    SHA_PATTERN = r'^[a-f0-9]{40}$'
    SHA_SHORT_PATTERN = r'^[a-f0-9]{7,40}$'

    # 공통 상태 필드 스키마 (_status)
    STATUS_SCHEMA = {
        "draft_created": {
            "required": True,
            "type": bool,
            "pattern": None,
            "description": "초안 작성 여부"
        },
        "posted": {
            "required": True,
            "type": bool,
            "pattern": None,
            "description": "포스팅 여부"
        },
        "skipped": {
            "required": True,
            "type": bool,
            "pattern": None,
            "description": "영구 포기 여부"
        }
    }

    # 백준 정책
    BAEKJOON_SCHEMA = {
        "문제_번호": {
            "required": True,
            "type": str,
            "pattern": r'^(\d+|Unknown)$',  # 숫자 또는 Unknown
            "description": "백준 문제 번호 (예: 1234, 14425, Unknown)"
        },
        "문제명": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',  # 비어있지 않음
            "description": "문제 제목 (예: N번째 큰 수)"
        },
        "티어": {
            "required": True,
            "type": str,
            "pattern": r'^(Bronze|Silver|Gold|Platinum|Diamond|Ruby)(_[IVX]+)?|Unknown$',
            "description": "난이도 티어 (예: Silver_III, Gold_II, Unknown)"
        },
        "풀이_코드": {
            "required": True,
            "type": str,
            "pattern": r'^[\s\S]*$',  # 빈 문자열도 허용 (API 실패 시)
            "description": "전체 풀이 코드"
        },
        "실행_시간": {
            "required": False,
            "type": str,
            "pattern": r'^(\d+\s*ms)?$',  # 빈 문자열도 허용
            "description": "실행 시간 (예: 120 ms)"
        },
        "메모리": {
            "required": False,
            "type": str,
            "pattern": r'^(\d+\s*KB)?$',  # 빈 문자열도 허용
            "description": "메모리 사용량 (예: 2048 KB)"
        },
        "언어": {
            "required": True,
            "type": str,
            "pattern": r'^(Python|Java|C\+\+|C|JavaScript|Go|Kotlin|Rust|Swift|Ruby|C#|Unknown)$',
            "description": "프로그래밍 언어"
        },
        "제출한_날짜": {
            "required": True,
            "type": str,
            "pattern": ISO_8601_PATTERN,
            "description": "제출 시각 (ISO 8601 형식)"
        },
        "커밋_SHA": {
            "required": True,
            "type": str,
            "pattern": SHA_PATTERN,
            "description": "Git 커밋 SHA (40자 hex)"
        },
        "_status": {
            "required": True,
            "type": dict,
            "pattern": None,
            "description": "처리 상태 (draft_created, posted, skipped)"
        }
    }

    # 개발 커밋 정책
    COMMITS_SCHEMA = {
        "커밋_메시지": {
            "required": True,
            "type": str,
            "pattern": r'^[\s\S]+$',  # multiline 커밋 메시지 지원
            "description": "커밋 메시지"
        },
        "SHA": {
            "required": True,
            "type": str,
            "pattern": SHA_PATTERN,
            "description": "Git 커밋 SHA (40자 hex)"
        },
        "변경된_파일_목록": {
            "required": True,
            "type": list,
            "pattern": None,  # 리스트는 별도 검증
            "description": "변경된 파일 경로 리스트"
        },
        "추가_라인": {
            "required": False,
            "type": int,
            "pattern": None,
            "description": "총 추가된 라인 수"
        },
        "삭제_라인": {
            "required": False,
            "type": int,
            "pattern": None,
            "description": "총 삭제된 라인 수"
        },
        "변경_내용": {
            "required": False,
            "type": list,
            "pattern": None,
            "description": "상위 5개 코드 파일의 패치 (파일명, 추가, 삭제, 패치)"
        },
        "커밋_날짜": {
            "required": True,
            "type": str,
            "pattern": ISO_8601_PATTERN,
            "description": "커밋 날짜 (ISO 8601 형식)"
        },
        "레포지토리": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',
            "description": "레포지토리 이름"
        },
        "브랜치": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',
            "description": "브랜치 이름"
        },
        "_status": {
            "required": True,
            "type": dict,
            "pattern": None,
            "description": "처리 상태 (draft_created, posted, skipped)"
        }
    }

    # AI Chat 정책
    AI_CHAT_SCHEMA = {
        "대화_제목": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',
            "description": "대화 제목 (MD 내부 제목)"
        },
        "파일_제목": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',
            "description": "파일명 기반 제목 (AI 접두사 제외)"
        },
        "모든_대화_내용": {
            "required": True,
            "type": str,
            "pattern": r'^[\s\S]+$',  # 비어있지 않음 (줄바꿈 포함)
            "description": "대화 전체 내용"
        },
        "Exported_시간": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',  # 다양한 형식 허용
            "description": "내보낸 시각"
        },
        "AI_종류": {
            "required": True,
            "type": str,
            "pattern": r'^(ChatGPT|Gemini|Claude|Unknown)$',
            "description": "AI 종류 (ChatGPT, Gemini, Claude)"
        },
        "원본_파일": {
            "required": True,
            "type": str,
            "pattern": r'^(ChatGPT|Gemini|Claude)-.+\.md$',
            "description": "원본 MD 파일명"
        },
        "_status": {
            "required": True,
            "type": dict,
            "pattern": None,
            "description": "처리 상태 (draft_created, posted, skipped)"
        }
    }

    # Draft 검증 규칙
    DRAFT_VALIDATION_RULES = {
        "filename_pattern": r'^(algorithm|dev|study)_.+\.md$',
        "min_length": 200,  # 최소 글자 수
        "h1_pattern": r'^# .+',  # H1 제목 패턴
        "h2_pattern": r'^## .+',  # H2 섹션 패턴
        "error_keywords": [
            "# 오류",
            "초안 생성 중 오류 발생",
            "RESOURCE_EXHAUSTED",
            "429",
            "quota",
            "exceeded your current quota"
        ],
        "draft_type_mapping": {
            "baekjoon": "algorithm",
            "commits": "dev",
            "ai_chat": "study"
        }
    }

    @classmethod
    def get_schema(cls, json_type: str) -> Dict:
        """JSON 타입별 스키마 반환"""
        schemas = {
            "baekjoon": cls.BAEKJOON_SCHEMA,
            "commits": cls.COMMITS_SCHEMA,
            "ai_chat": cls.AI_CHAT_SCHEMA
        }
        return schemas.get(json_type, {})

    @classmethod
    def validate_field(cls, field_name: str, value: Any, schema: Dict) -> Tuple[bool, str]:
        """
        단일 필드 검증

        Returns:
            Tuple[bool, str]: (검증 통과 여부, 에러 메시지)
        """
        if field_name not in schema:
            return True, ""  # 스키마에 없는 필드는 허용

        field_schema = schema[field_name]

        # 타입 검증
        expected_type = field_schema["type"]
        if not isinstance(value, expected_type):
            return False, f"타입 불일치 (예상: {expected_type.__name__}, 실제: {type(value).__name__})"

        # 리스트는 별도 처리
        if expected_type == list:
            # 변경_내용은 빈 리스트 허용 (패치 없는 경우)
            if field_name == "변경_내용":
                for item in value:
                    if not isinstance(item, dict):
                        return False, f"변경_내용 항목이 dict가 아님: {type(item).__name__}"
                return True, ""
            # 일반 리스트
            if not value:  # 빈 리스트 체크
                return False, "빈 리스트"
            for item in value:
                if not isinstance(item, str):
                    return False, f"리스트 항목이 문자열이 아님: {type(item).__name__}"
            return True, ""

        # dict는 _status 필드 검증
        if expected_type == dict:
            return cls.validate_status(value)

        # 정규식 검증
        pattern = field_schema.get("pattern")
        if pattern:
            if not re.match(pattern, str(value)):
                description = field_schema.get("description", "")
                return False, f"패턴 불일치 ({description})"

        return True, ""

    @classmethod
    def validate_status(cls, status: Dict) -> Tuple[bool, str]:
        """
        _status 필드 검증

        Returns:
            Tuple[bool, str]: (검증 통과 여부, 에러 메시지)
        """
        required_fields = ["draft_created", "posted", "skipped"]

        for field in required_fields:
            if field not in status:
                return False, f"_status에 필수 필드 누락: {field}"
            if not isinstance(status[field], bool):
                return False, f"_status.{field}는 bool 타입이어야 함"

        return True, ""

    @classmethod
    def validate_json(cls, data: Dict, json_type: str) -> Tuple[bool, List[str]]:
        """
        전체 JSON 검증

        Returns:
            Tuple[bool, List[str]]: (검증 통과 여부, 에러 메시지 리스트)
        """
        schema = cls.get_schema(json_type)
        errors = []

        # 필수 필드 존재 확인
        for field_name, field_schema in schema.items():
            if field_schema["required"] and field_name not in data:
                errors.append(f"필수 필드 누락: {field_name}")

        # 각 필드 값 검증
        for field_name, value in data.items():
            if field_name in schema:
                is_valid, error_msg = cls.validate_field(field_name, value, schema)
                if not is_valid:
                    errors.append(f"{field_name}: {error_msg}")

        return len(errors) == 0, errors

    @classmethod
    def validate_json_lenient(cls, data: Dict, json_type: str) -> Tuple[bool, List[str]]:
        """
        느슨한 JSON 검증 (기존 JSON 호환)
        _status 필드가 없어도 통과

        Returns:
            Tuple[bool, List[str]]: (검증 통과 여부, 에러 메시지 리스트)
        """
        schema = cls.get_schema(json_type)
        errors = []

        # 필수 필드 존재 확인 (_status 제외)
        for field_name, field_schema in schema.items():
            if field_name == "_status":
                continue  # _status는 선택적
            if field_schema["required"] and field_name not in data:
                errors.append(f"필수 필드 누락: {field_name}")

        # 각 필드 값 검증
        for field_name, value in data.items():
            if field_name in schema:
                is_valid, error_msg = cls.validate_field(field_name, value, schema)
                if not is_valid:
                    errors.append(f"{field_name}: {error_msg}")

        return len(errors) == 0, errors
