"""
수집 정책 정의
수집 대상 및 필드 정의
"""


class CollectionRules:
    """수집 규칙 정의 클래스"""

    # AI Chat MD 파일 접두사
    AI_CHAT_PREFIXES = ["ChatGPT-", "Gemini-", "Claude-"]

    # 백준 커밋 식별자
    BAEKJOON_SUFFIX = "-BaekjoonHub"

    # AI Chat JSON 필수 필드
    AI_CHAT_FIELDS = [
        "대화_제목",
        "모든_대화_내용",
        "Exported_시간",
        "AI_종류"
    ]

    # 백준 JSON 필수 필드
    BAEKJOON_FIELDS = [
        "문제_번호",
        "문제명",
        "티어",
        "풀이_코드",
        "제출한_날짜"
    ]

    # GitHub 커밋 JSON 필수 필드
    GITHUB_COMMIT_FIELDS = [
        "커밋_메시지",
        "SHA",
        "변경된_파일_목록",
        "핵심_변경사항"
    ]

    @classmethod
    def is_ai_chat_file(cls, filename: str) -> bool:
        """AI Chat 파일 여부 확인"""
        return any(filename.startswith(prefix) for prefix in cls.AI_CHAT_PREFIXES)

    @classmethod
    def is_baekjoon_commit(cls, commit_message: str) -> bool:
        """백준 커밋 여부 확인"""
        return commit_message.strip().endswith(cls.BAEKJOON_SUFFIX)

    @classmethod
    def validate_ai_chat_data(cls, data: dict) -> bool:
        """AI Chat 데이터 유효성 검증"""
        return all(field in data for field in cls.AI_CHAT_FIELDS)

    @classmethod
    def validate_baekjoon_data(cls, data: dict) -> bool:
        """백준 데이터 유효성 검증"""
        return all(field in data for field in cls.BAEKJOON_FIELDS)

    @classmethod
    def validate_commit_data(cls, data: dict) -> bool:
        """커밋 데이터 유효성 검증"""
        return all(field in data for field in cls.GITHUB_COMMIT_FIELDS)


if __name__ == "__main__":
    # 테스트
    print("AI Chat 파일 체크:")
    print(CollectionRules.is_ai_chat_file("ChatGPT-example.md"))  # True
    print(CollectionRules.is_ai_chat_file("normal-file.md"))  # False

    print("\n백준 커밋 체크:")
    print(CollectionRules.is_baekjoon_commit("1234: 문제 -BaekjoonHub"))  # True
    print(CollectionRules.is_baekjoon_commit("feat: Add feature"))  # False
