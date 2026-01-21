"""
GitHub 수집 모듈 (메인 흐름)
GraphQL로 수집 정책에서 도출된 수집 기간 동안 나와 claude가 한 커밋들을 모든 레포, 모든 브랜치에서 찾아온다
"""
import os
from datetime import datetime
from typing import List, Tuple

# API 모듈 임포트
from api.github_graphql import GitHubGraphQLClient

# 정책 모듈 임포트
from policies.storage.json_saver import JSONSaver
from collectors.classifier import CommitClassifier


class GitHubCollector:
    """GitHub 수집 클래스"""

    def __init__(self):
        self.github_client = GitHubGraphQLClient()
        self.classifier = CommitClassifier()
        self.json_saver = JSONSaver()

    def collect(self, start_date: datetime, end_date: datetime) -> Tuple[List[str], List[str]]:
        """
        GitHub에서 커밋 수집

        Returns:
            Tuple[List[str], List[str]]: (백준 JSON 파일명 리스트, 개발 JSON 파일명 리스트)
        """
        username = os.getenv("GITHUB_USERNAME")

        # 1. GitHub GraphQL로 커밋 수집
        print(f"  GitHub 사용자 {username}의 모든 레포, 모든 브랜치 조회 중...")
        commits = self.github_client.fetch_commits(username, start_date, end_date)
        print(f"  총 {len(commits)}개의 커밋 발견")

        # 2. 백준 / 개발 분류
        baekjoon_commits = []
        dev_commits = []

        for commit in commits:
            if self.classifier.is_baekjoon_commit(commit):
                baekjoon_commits.append(commit)
            else:
                dev_commits.append(commit)

        print(f"  분류 완료 - 백준: {len(baekjoon_commits)}, 개발: {len(dev_commits)}")

        # 3. JSON 저장
        baekjoon_files = self._save_baekjoon_commits(baekjoon_commits)
        dev_files = self._save_dev_commits(dev_commits)

        return baekjoon_files, dev_files

    def _save_baekjoon_commits(self, commits: List[dict]) -> List[str]:
        """백준 커밋을 JSON으로 저장"""
        saved_files = []

        for commit in commits:
            # 백준 정보 추출
            baekjoon_data = {
                "문제_번호": self._extract_problem_number(commit),
                "문제명": self._extract_problem_name(commit),
                "티어": self._extract_tier(commit),
                "풀이_코드": self._extract_solution_code(commit),
                "제출한_날짜": commit.get("committedDate"),
                "커밋_SHA": commit.get("oid")
            }

            # 중복 체크 및 저장
            filename = self.json_saver.save_baekjoon(baekjoon_data)
            if filename:
                saved_files.append(filename)

        return saved_files

    def _save_dev_commits(self, commits: List[dict]) -> List[str]:
        """개발 커밋을 JSON으로 저장"""
        saved_files = []

        for commit in commits:
            # 개발 커밋 정보 추출
            dev_data = {
                "커밋_메시지": commit.get("message"),
                "SHA": commit.get("oid"),
                "변경된_파일_목록": commit.get("changedFiles", []),
                "핵심_변경사항": commit.get("additions", 0) + commit.get("deletions", 0),
                "커밋_날짜": commit.get("committedDate"),
                "레포지토리": commit.get("repository")
            }

            # 중복 체크 및 저장
            filename = self.json_saver.save_commit(dev_data)
            if filename:
                saved_files.append(filename)

        return saved_files

    def _extract_problem_number(self, commit: dict) -> str:
        """커밋 메시지에서 문제 번호 추출"""
        message = commit.get("message", "")
        # 예: "1234: 문제 이름" 형식에서 번호 추출
        parts = message.split(":")
        if len(parts) > 0:
            return parts[0].strip()
        return "Unknown"

    def _extract_problem_name(self, commit: dict) -> str:
        """커밋 메시지에서 문제 이름 추출"""
        message = commit.get("message", "")
        # 예: "1234: 문제 이름" 형식에서 이름 추출
        parts = message.split(":")
        if len(parts) > 1:
            # -BaekjoonHub 제거
            name = parts[1].replace("-BaekjoonHub", "").strip()
            return name
        return "Unknown"

    def _extract_tier(self, commit: dict) -> str:
        """티어 정보 추출 (파일명이나 커밋 메시지에서)"""
        # 실제 구현에서는 백준 API나 파일명에서 추출
        return "Unknown"

    def _extract_solution_code(self, commit: dict) -> str:
        """풀이 코드 추출"""
        # 변경된 파일 중 코드 파일 내용 가져오기
        files = commit.get("changedFiles", [])
        for file in files:
            if file.get("path", "").endswith((".py", ".java", ".cpp", ".c")):
                return file.get("content", "")
        return ""


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    from datetime import timedelta
    collector = GitHubCollector()
    end = datetime.now()
    start = end - timedelta(days=30)
    collector.collect(start, end)
