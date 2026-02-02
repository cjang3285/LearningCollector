"""
커밋 분류 모듈
백준 / 개발 분류:
- 커밋 메시지 마지막에 -BaekjoonHub가 붙어있으면 백준
- 백준 레포의 다른 커밋은 무시 (개발로 분류 안 함)
- 나머지는 개발
"""


class CommitClassifier:
    """커밋 분류 클래스"""

    BAEKJOON_SUFFIX = "-BaekjoonHub"
    # 백준 레포 패턴 (소문자로 비교)
    BAEKJOON_REPO_PATTERNS = ["baekjoon", "백준", "boj", "algorithm"]

    def is_baekjoon_commit(self, commit: dict) -> bool:
        """
        백준 커밋 여부 판단

        Args:
            commit: 커밋 정보 딕셔너리

        Returns:
            bool: 백준 커밋이면 True, 개발 커밋이면 False
        """
        message = commit.get("message", "")
        return message.strip().endswith(self.BAEKJOON_SUFFIX)

    def is_baekjoon_repo(self, commit: dict) -> bool:
        """
        백준 관련 레포인지 판단

        Args:
            commit: 커밋 정보 딕셔너리

        Returns:
            bool: 백준 관련 레포면 True
        """
        repo = commit.get("repository", "").lower()
        return any(pattern in repo for pattern in self.BAEKJOON_REPO_PATTERNS)

    def classify_commits(self, commits: list) -> tuple:
        """
        커밋 리스트를 백준/개발로 분류

        Args:
            commits: 커밋 정보 딕셔너리 리스트

        Returns:
            tuple: (백준 커밋 리스트, 개발 커밋 리스트)
        """
        baekjoon_commits = []
        dev_commits = []

        for commit in commits:
            if self.is_baekjoon_commit(commit):
                # -BaekjoonHub 접미사 있으면 백준 커밋
                baekjoon_commits.append(commit)
            elif self.is_baekjoon_repo(commit):
                # 백준 레포의 다른 커밋은 무시 (개발로 분류 안 함)
                pass
            else:
                # 나머지는 개발 커밋
                dev_commits.append(commit)

        return baekjoon_commits, dev_commits


if __name__ == "__main__":
    # 테스트
    classifier = CommitClassifier()

    test_commits = [
        {"message": "1234: 두 수의 합 -BaekjoonHub", "repository": "Baekjoon_solutions"},
        {"message": "feat: Add user authentication", "repository": "MyProject"},
        {"message": "5678: 스택 구현 -BaekjoonHub", "repository": "Baekjoon_solutions"},
        {"message": "fix: Fix login bug", "repository": "MyProject"},
        {"message": "Fix formatting", "repository": "Baekjoon_solutions"},  # 백준 레포의 수동 커밋 → 무시됨
    ]

    baekjoon, dev = classifier.classify_commits(test_commits)
    print(f"백준 커밋: {len(baekjoon)}개")  # 2개
    print(f"개발 커밋: {len(dev)}개")  # 2개 (백준 레포 수동 커밋 제외)
