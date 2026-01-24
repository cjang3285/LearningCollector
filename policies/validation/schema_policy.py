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

    # 백준 정책
    BAEKJOON_SCHEMA = {
        "문제_번호": {
            "required": True,
            "type": str,
            "pattern": r'^\d+$',  # 숫자만
            "description": "백준 문제 번호 (예: 1234, 14425)"
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
            "pattern": r'^(Bronze|Silver|Gold|Platinum|Diamond|Ruby)(_[IVX]+)?$',
            "description": "난이도 티어 (예: Silver_III, Gold_II)"
        },
        "풀이_코드": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',  # 비어있지 않음
            "description": "전체 풀이 코드"
        },
        "실행_시간": {
            "required": False,
            "type": str,
            "pattern": r'^\d+\s*ms$',
            "description": "실행 시간 (예: 120 ms)"
        },
        "메모리": {
            "required": False,
            "type": str,
            "pattern": r'^\d+\s*KB$',
            "description": "메모리 사용량 (예: 2048 KB)"
        },
        "언어": {
            "required": True,
            "type": str,
            "pattern": r'^(Python|Java|C\+\+|C|JavaScript|Go|Kotlin|Rust|Swift|Ruby|C#)$',
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
        }
    }

    # 개발 커밋 정책
    COMMITS_SCHEMA = {
        "커밋_메시지": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',
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
        }
    }

    # AI Chat 정책
    AI_CHAT_SCHEMA = {
        "대화_제목": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',
            "description": "대화 제목"
        },
        "모든_대화_내용": {
            "required": True,
            "type": str,
            "pattern": r'^.+$',
            "description": "대화 전체 내용"
        },
        "Exported_시간": {
            "required": True,
            "type": str,
            "pattern": ISO_8601_PATTERN,
            "description": "내보낸 시각 (ISO 8601 형식)"
        },
        "AI_종류": {
            "required": True,
            "type": str,
            "pattern": r'^(ChatGPT|Gemini|Claude)$',
            "description": "AI 종류 (ChatGPT, Gemini, Claude)"
        },
        "원본_파일": {
            "required": True,
            "type": str,
            "pattern": r'^(ChatGPT|Gemini|Claude)-.+\.md$',
            "description": "원본 MD 파일명"
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
            if not value:  # 빈 리스트 체크
                return False, "빈 리스트"
            for item in value:
                if not isinstance(item, str):
                    return False, f"리스트 항목이 문자열이 아님: {type(item).__name__}"
            return True, ""

        # 정규식 검증
        pattern = field_schema.get("pattern")
        if pattern:
            if not re.match(pattern, str(value)):
                description = field_schema.get("description", "")
                return False, f"패턴 불일치 ({description})"

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
