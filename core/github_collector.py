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
from policies.storage.duplicate_checker import DuplicateChecker
from collectors.classifier import CommitClassifier


class GitHubCollector:
    """GitHub 수집 클래스"""

    def __init__(self):
        self.github_client = GitHubGraphQLClient()
        self.classifier = CommitClassifier()
        self.duplicate_checker = DuplicateChecker()
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

        # 2. ⭐ 중복 체크 먼저 (SHA만으로 판단)
        new_commits = []
        for commit in commits:
            sha = commit.get("oid")
            # 백준/개발 구분 없이 SHA로 중복 체크
            if not (self.duplicate_checker.is_duplicate_baekjoon(sha) or
                    self.duplicate_checker.is_duplicate_commit(sha)):
                new_commits.append(commit)

        skipped = len(commits) - len(new_commits)
        if skipped > 0:
            print(f"  중복 제외: {skipped}개 (이미 저장됨)")

        # 3. 백준 / 개발 분류 (새 커밋만)
        baekjoon_commits = []
        dev_commits = []

        for commit in new_commits:
            if self.classifier.is_baekjoon_commit(commit):
                baekjoon_commits.append(commit)
            else:
                dev_commits.append(commit)

        print(f"  분류 완료 - 백준: {len(baekjoon_commits)}, 개발: {len(dev_commits)}")

        # 4. JSON 저장 (백준 커밋 → 즉시 REST 조회)
        baekjoon_files = self._save_baekjoon_commits(baekjoon_commits)
        dev_files = self._save_dev_commits(dev_commits)

        return baekjoon_files, dev_files

    def _save_baekjoon_commits(self, commits: List[dict]) -> List[str]:
        """백준 커밋을 JSON으로 저장"""
        saved_files = []

        for commit in commits:
            # 백준 정보 추출 (정책에 명시된 필드만)
            baekjoon_data = {
                "문제_번호": self._extract_problem_number(commit),
                "문제명": self._extract_problem_name(commit),
                "티어": self._extract_tier(commit),
                "풀이_코드": self._extract_solution_code(commit),
                "제출한_날짜": commit.get("committedDate")
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
            # 개발 커밋 정보 추출 (정책에 명시된 필드만)
            dev_data = {
                "커밋_메시지": commit.get("message"),
                "SHA": commit.get("oid"),
                "변경된_파일_목록": self._get_changed_files(commit),
                "핵심_변경사항": self._get_diff_summary(commit)
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

    def _get_changed_files(self, commit: dict) -> list:
        """REST API로 변경된 파일 목록 가져오기"""
        import requests

        owner = os.getenv("GITHUB_USERNAME")
        repo = commit.get("repository")
        sha = commit.get("oid")

        if not all([owner, repo, sha]):
            return []

        try:
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            # 커밋의 파일 목록 가져오기
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return []

            commit_data = response.json()
            files = commit_data.get("files", [])

            # 파일명 리스트 반환
            return [file.get("filename") for file in files]

        except Exception as e:
            print(f"  파일 목록 조회 실패 (SHA: {sha[:7]}): {str(e)}")
            return []

    def _get_diff_summary(self, commit: dict) -> str:
        """REST API로 diff 요약 생성"""
        import requests

        owner = os.getenv("GITHUB_USERNAME")
        repo = commit.get("repository")
        sha = commit.get("oid")

        if not all([owner, repo, sha]):
            return "요약 없음"

        try:
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return "요약 없음"

            commit_data = response.json()
            files = commit_data.get("files", [])

            total_additions = commit_data.get("stats", {}).get("additions", 0)
            total_deletions = commit_data.get("stats", {}).get("deletions", 0)

            # 파일별 변경사항 요약
            file_summaries = []
            for file in files[:5]:  # 최대 5개 파일만
                filename = file.get("filename", "")
                additions = file.get("additions", 0)
                deletions = file.get("deletions", 0)
                status = file.get("status", "modified")

                if status == "added":
                    file_summaries.append(f"{filename} 추가 (+{additions})")
                elif status == "removed":
                    file_summaries.append(f"{filename} 삭제 (-{deletions})")
                else:
                    file_summaries.append(f"{filename} 수정 (+{additions}/-{deletions})")

            summary_text = ", ".join(file_summaries)
            if len(files) > 5:
                summary_text += f" 외 {len(files) - 5}개 파일"

            # 전체 통계 추가
            summary_text += f" [총 +{total_additions}/-{total_deletions}]"

            return summary_text

        except Exception as e:
            print(f"  Diff 요약 생성 실패 (SHA: {sha[:7]}): {str(e)}")
            return "요약 생성 실패"

    def _extract_solution_code(self, commit: dict) -> str:
        """풀이 코드 추출 (REST API 사용)"""
        import requests

        # GitHub REST API로 커밋 상세 정보 가져오기
        owner = os.getenv("GITHUB_USERNAME")
        repo = commit.get("repository")
        sha = commit.get("oid")

        if not all([owner, repo, sha]):
            return ""

        try:
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            # 커밋의 파일 목록 가져오기
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return ""

            commit_data = response.json()
            files = commit_data.get("files", [])

            # 코드 파일 찾기
            for file in files:
                filename = file.get("filename", "")
                if filename.endswith((".py", ".java", ".cpp", ".c", ".js", ".go")):
                    # patch에서 코드 추출 또는 raw_url로 파일 내용 가져오기
                    patch = file.get("patch", "")
                    if patch:
                        # patch에서 추가된 코드만 추출
                        code_lines = [line[1:] for line in patch.split("\n") if line.startswith("+") and not line.startswith("+++")]
                        return "\n".join(code_lines)

            return ""

        except Exception as e:
            print(f"  코드 추출 실패 (SHA: {sha[:7]}): {str(e)}")
            return ""


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    from datetime import timedelta
    collector = GitHubCollector()
    end = datetime.now()
    start = end - timedelta(days=30)
    collector.collect(start, end)
