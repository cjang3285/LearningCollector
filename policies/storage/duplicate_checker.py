"""
중복 체크 모듈
- 백준: 커밋 SHA
- 개발: 커밋 SHA
- AI Chat: exported 시간
"""
import json
from pathlib import Path


class DuplicateChecker:
    """중복 체크 클래스"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"

    def is_duplicate_baekjoon(self, commit_sha: str) -> bool:
        """
        백준 JSON 중복 체크

        Args:
            commit_sha: 커밋 SHA

        Returns:
            bool: 중복이면 True
        """
        baekjoon_dir = self.data_dir / "baekjoon"
        if not baekjoon_dir.exists():
            return False

        for json_file in baekjoon_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("커밋_SHA") == commit_sha:
                        return True
            except Exception:
                continue

        return False

    def is_duplicate_commit(self, commit_sha: str) -> bool:
        """
        개발 커밋 JSON 중복 체크

        Args:
            commit_sha: 커밋 SHA

        Returns:
            bool: 중복이면 True
        """
        commits_dir = self.data_dir / "commits"
        if not commits_dir.exists():
            return False

        for json_file in commits_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("SHA") == commit_sha:
                        return True
            except Exception:
                continue

        return False

    def is_duplicate_ai_chat(self, ai_type: str, exported_time: str) -> bool:
        """
        AI Chat JSON 중복 체크

        Args:
            ai_type: AI 종류 (ChatGPT, Gemini, Claude)
            exported_time: exported 시간

        Returns:
            bool: 중복이면 True
        """
        ai_chat_dir = self.data_dir / "ai_chat"
        if not ai_chat_dir.exists():
            return False

        for json_file in ai_chat_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if (data.get("AI_종류") == ai_type and
                        data.get("Exported_시간") == exported_time):
                        return True
            except Exception:
                continue

        return False


if __name__ == "__main__":
    checker = DuplicateChecker()

    # 테스트
    print("중복 체크 테스트:")
    print(f"백준 중복: {checker.is_duplicate_baekjoon('abc123')}")
    print(f"커밋 중복: {checker.is_duplicate_commit('def456')}")
    print(f"AI Chat 중복: {checker.is_duplicate_ai_chat('ChatGPT', '2024-01-01 12:00:00')}")
