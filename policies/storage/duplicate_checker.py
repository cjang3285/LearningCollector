"""
중복 체크 모듈
- 백준: 커밋 SHA
- 개발: 커밋 SHA
- AI Chat: 원본 파일명
- PR: PR ID (GraphQL 전역 고유 ID)

각 소스별 키 값(SHA/파일명)을 인스턴스당 한 번만 폴더에서 스캔해 메모리에
캐싱해두고, 이후 조회는 집합(set) 조회로 처리한다. 데이터 파일이 수백~수천개로
쌓여도 커밋 1건 확인할 때마다 폴더 전체를 다시 읽지 않도록 하기 위함.
"""
import json
from pathlib import Path


class DuplicateChecker:
    """중복 체크 클래스"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self._baekjoon_shas = None
        self._commit_shas = None
        self._ai_chat_files = None
        self._pr_ids = None

    def _scan_field_values(self, subdir: str, field: str) -> set:
        """지정된 폴더의 모든 JSON에서 특정 필드 값을 모아 집합으로 반환 (최초 1회만 디스크 스캔)"""
        result = set()
        target_dir = self.data_dir / subdir
        if not target_dir.exists():
            return result

        for json_file in target_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    value = data.get(field)
                    if value:
                        result.add(value)
            except Exception:
                continue

        return result

    def is_duplicate_baekjoon(self, commit_sha: str) -> bool:
        """
        백준 JSON 중복 체크

        Args:
            commit_sha: 커밋 SHA

        Returns:
            bool: 중복이면 True
        """
        if self._baekjoon_shas is None:
            self._baekjoon_shas = self._scan_field_values("baekjoon", "커밋_SHA")

        if commit_sha in self._baekjoon_shas:
            return True

        # 같은 커밋이 여러 브랜치에 걸쳐 있어도 이번 실행에서 한 번만 처리되도록
        # 확인 즉시 캐시에 반영 (뒤이어 저장될 것이므로)
        self._baekjoon_shas.add(commit_sha)
        return False

    def is_duplicate_commit(self, commit_sha: str) -> bool:
        """
        개발 커밋 JSON 중복 체크

        Args:
            commit_sha: 커밋 SHA

        Returns:
            bool: 중복이면 True
        """
        if self._commit_shas is None:
            self._commit_shas = self._scan_field_values("commits", "SHA")

        if commit_sha in self._commit_shas:
            return True

        self._commit_shas.add(commit_sha)
        return False

    def is_duplicate_ai_chat(self, original_filename: str) -> bool:
        """
        AI Chat JSON 중복 체크 (원본 파일명 기반)

        Args:
            original_filename: 원본 마크다운 파일명

        Returns:
            bool: 중복이면 True
        """
        if self._ai_chat_files is None:
            self._ai_chat_files = self._scan_field_values("ai_chat", "원본_파일")

        if original_filename in self._ai_chat_files:
            return True

        self._ai_chat_files.add(original_filename)
        return False

    def is_duplicate_pr(self, pr_id: str) -> bool:
        """
        PR JSON 중복 체크 (GraphQL PR ID 기반)

        Args:
            pr_id: PR의 GraphQL 전역 고유 ID

        Returns:
            bool: 중복이면 True
        """
        if self._pr_ids is None:
            self._pr_ids = self._scan_field_values("prs", "PR_ID")

        if pr_id in self._pr_ids:
            return True

        self._pr_ids.add(pr_id)
        return False


if __name__ == "__main__":
    checker = DuplicateChecker()

    # 테스트
    print("중복 체크 테스트:")
    print(f"백준 중복: {checker.is_duplicate_baekjoon('abc123')}")
    print(f"커밋 중복: {checker.is_duplicate_commit('def456')}")
    print(f"AI Chat 중복: {checker.is_duplicate_ai_chat('ChatGPT-example.md')}")
