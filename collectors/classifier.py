"""
커밋 분류 모듈
백준 / 개발 분류: 커밋 메시지 마지막에 -BaekjoonHub가 붙어있으면 백준, 아니면 개발
"""


class CommitClassifier:
    """커밋 분류 클래스"""

    BAEKJOON_SUFFIX = "-BaekjoonHub"

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
                baekjoon_commits.append(commit)
            else:
                dev_commits.append(commit)

        return baekjoon_commits, dev_commits


if __name__ == "__main__":
    # 테스트
    classifier = CommitClassifier()

    test_commits = [
        {"message": "1234: 두 수의 합 -BaekjoonHub"},
        {"message": "feat: Add user authentication"},
        {"message": "5678: 스택 구현 -BaekjoonHub"},
        {"message": "fix: Fix login bug"}
    ]

    baekjoon, dev = classifier.classify_commits(test_commits)
    print(f"백준 커밋: {len(baekjoon)}개")
    print(f"개발 커밋: {len(dev)}개")
