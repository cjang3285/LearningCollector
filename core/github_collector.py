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
from core.classifier import CommitClassifier


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
        duplicate_commits = []

        for commit in commits:
            sha = commit.get("oid")
            message = commit.get("message", "")[:50]  # 메시지 첫 50자

            # 백준/개발 구분 없이 SHA로 중복 체크
            if self.duplicate_checker.is_duplicate_baekjoon(sha) or self.duplicate_checker.is_duplicate_commit(sha):
                duplicate_commits.append(f"{sha[:7]} - {message}")
            else:
                new_commits.append(commit)

        # 중복 커밋 로깅
        if duplicate_commits:
            print(f"  ⚠️  중복 제외: {len(duplicate_commits)}개 (이미 저장됨)")
            if len(duplicate_commits) <= 10:
                # 10개 이하면 전부 출력
                for dup in duplicate_commits:
                    print(f"    - {dup}")
            else:
                # 10개 초과면 처음 5개, 마지막 5개만 출력
                print(f"    처음 5개:")
                for dup in duplicate_commits[:5]:
                    print(f"    - {dup}")
                print(f"    ... ({len(duplicate_commits) - 10}개 생략) ...")
                print(f"    마지막 5개:")
                for dup in duplicate_commits[-5:]:
                    print(f"    - {dup}")
        else:
            print(f"  ✓ 모든 커밋이 신규입니다")

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
        total = len(commits)

        for idx, commit in enumerate(commits, 1):
            print(f"    백준 처리 중: {idx}/{total}", end='\r', flush=True)

            # 백준 정보 추출
            baekjoon_data = {
                "문제_번호": self._extract_problem_number(commit),
                "문제명": self._extract_problem_name(commit),
                "티어": self._extract_tier(commit),
                "풀이_코드": self._extract_solution_code(commit),
                "실행_시간": self._extract_runtime(commit),
                "메모리": self._extract_memory(commit),
                "언어": self._extract_language(commit),
                "제출한_날짜": commit.get("committedDate"),
                "커밋_SHA": commit.get("oid")
            }

            # 중복 체크 및 저장
            filename = self.json_saver.save_baekjoon(baekjoon_data)
            if filename:
                saved_files.append(filename)

        if total > 0:
            print()  # 줄바꿈
        return saved_files

    def _save_dev_commits(self, commits: List[dict]) -> List[str]:
        """개발 커밋을 JSON으로 저장"""
        saved_files = []
        total = len(commits)

        for idx, commit in enumerate(commits, 1):
            print(f"    개발 커밋 처리 중: {idx}/{total}", end='\r', flush=True)

            # 개발 커밋 정보 추출
            dev_data = {
                "커밋_메시지": commit.get("message"),
                "SHA": commit.get("oid"),
                "변경된_파일_목록": self._get_changed_files(commit),
                "커밋_날짜": commit.get("committedDate"),
                "레포지토리": commit.get("repository"),
                "브랜치": commit.get("branch", "unknown")
            }

            # 중복 체크 및 저장
            filename = self.json_saver.save_commit(dev_data)
            if filename:
                saved_files.append(filename)

        if total > 0:
            print()  # 줄바꿈
        return saved_files

    def _extract_problem_number(self, commit: dict) -> str:
        """
        커밋에서 문제 번호 추출
        백준 레포 구조: 백준/{티어}/{번호. 문제명}/solution.py
        예: 백준/Gold/1202. 보석 도둑/solution.py
        """
        import re

        # REST API로 파일 목록 가져오기
        try:
            owner = os.getenv("GITHUB_USERNAME")
            repo = commit.get("repository")
            sha = commit.get("oid")

            if not all([owner, repo, sha]):
                return "Unknown"

            import requests
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            # 커밋의 파일 목록 가져오기
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                commit_data = response.json()
                files = commit_data.get("files", [])

                # 파일 경로에서 문제 번호 추출
                # 패턴: 백준/{티어}/{번호. 문제명}/
                for file in files:
                    filename = file.get("filename", "")

                    # 정규식: 백준/[^/]+/(\d+)\.
                    match = re.search(r'백준/[^/]+/(\d+)\.', filename)
                    if match:
                        return match.group(1)

            return "Unknown"

        except Exception:
            return "Unknown"

    def _extract_problem_name(self, commit: dict) -> str:
        """
        커밋 메시지에서 문제 이름 추출
        백준Hub 형식: [티어] Title: 문제명, Time: X ms, Memory: Y KB -BaekjoonHub
        """
        import re

        message = commit.get("message", "")

        # "Title: 문제명," 부분 추출
        match = re.search(r'Title:\s*([^,]+)', message)
        if match:
            return match.group(1).strip()

        return "Unknown"

    def _extract_tier(self, commit: dict) -> str:
        """
        티어 정보 추출
        백준Hub 형식: [티어] Title: 문제명, Time: X ms, Memory: Y KB -BaekjoonHub
        """
        import re

        message = commit.get("message", "")

        # [티어] 부분 추출
        match = re.search(r'\[(.*?)\]', message)
        if match:
            tier = match.group(1).strip()
            # 공백을 언더스코어로 변경
            return tier.replace(" ", "_")

        return "Unknown"

    def _extract_runtime(self, commit: dict) -> str:
        """커밋 메시지에서 실행 시간 추출 (Time: X ms)"""
        import re
        message = commit.get("message", "")

        # Time: X ms 패턴
        match = re.search(r'Time:\s*(\d+)\s*ms', message)
        if match:
            return f"{match.group(1)} ms"

        return ""

    def _extract_memory(self, commit: dict) -> str:
        """커밋 메시지에서 메모리 추출 (Memory: Y KB)"""
        import re
        message = commit.get("message", "")

        # Memory: Y KB 패턴
        match = re.search(r'Memory:\s*(\d+)\s*KB', message)
        if match:
            return f"{match.group(1)} KB"

        return ""

    def _extract_language(self, commit: dict) -> str:
        """파일 확장자에서 언어 추출"""
        import requests

        owner = os.getenv("GITHUB_USERNAME")
        repo = commit.get("repository")
        sha = commit.get("oid")

        if not all([owner, repo, sha]):
            return "Unknown"

        try:
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            # 커밋의 파일 목록 가져오기
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return "Unknown"

            commit_data = response.json()
            files = commit_data.get("files", [])

            # 백준 폴더 내의 코드 파일 확장자 찾기
            extension_to_language = {
                ".py": "Python",
                ".java": "Java",
                ".cpp": "C++",
                ".cc": "C++",
                ".c": "C",
                ".js": "JavaScript",
                ".go": "Go",
                ".kt": "Kotlin",
                ".rs": "Rust",
                ".swift": "Swift",
                ".rb": "Ruby",
                ".cs": "C#"
            }

            for file in files:
                filename = file.get("filename", "")
                if "백준/" in filename:
                    for ext, lang in extension_to_language.items():
                        if filename.endswith(ext):
                            return lang

            return "Unknown"

        except Exception:
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

    def _extract_solution_code(self, commit: dict) -> str:
        """풀이 코드 추출 (REST API 사용) - 전체 파일 내용 가져오기"""
        import requests

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

            # 백준 폴더 내의 코드 파일 찾기
            code_extensions = (".py", ".java", ".cpp", ".cc", ".c", ".js", ".go",
                             ".kt", ".rs", ".swift", ".rb", ".cs")

            for file in files:
                filename = file.get("filename", "")

                # 백준 폴더 내의 코드 파일인지 확인 (README.md 제외)
                if "백준/" in filename and not filename.endswith("README.md"):
                    if filename.endswith(code_extensions):
                        # raw_url로 전체 파일 내용 가져오기
                        raw_url = file.get("raw_url")
                        if raw_url:
                            raw_response = requests.get(raw_url, headers=headers, timeout=10)
                            if raw_response.status_code == 200:
                                return raw_response.text

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
