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

    def collect_interactive(self, start_date: datetime, end_date: datetime) -> Tuple[List[str], List[str]]:
        """
        대화형으로 레포/브랜치 선택하여 커밋 수집

        Returns:
            Tuple[List[str], List[str]]: (백준 JSON 파일명 리스트, 개발 JSON 파일명 리스트)
        """
        username = os.getenv("GITHUB_USERNAME")

        # 1. 레포 선택
        print(f"\n📦 {username}의 레포지토리 조회 중...")
        repos = self.github_client.fetch_repositories(username)

        if not repos:
            print("레포지토리가 없습니다.")
            return [], []

        print(f"\n총 {len(repos)}개의 레포지토리:")
        for i, repo in enumerate(repos, 1):
            print(f"  {i}. {repo['name']}")

        # 레포 선택
        while True:
            try:
                selection = input(f"\n레포 번호 입력 (1-{len(repos)}, 또는 'all'): ").strip()

                if selection.lower() == 'all':
                    selected_repos = repos
                    break
                else:
                    idx = int(selection) - 1
                    if 0 <= idx < len(repos):
                        selected_repos = [repos[idx]]
                        break
                    else:
                        print(f"1부터 {len(repos)} 사이의 숫자를 입력하세요.")
            except ValueError:
                print("올바른 숫자를 입력하세요.")

        # 2. 선택된 레포별로 브랜치 선택
        all_commits = []

        for repo in selected_repos:
            repo_name = repo['name']
            owner = repo['owner']['login']

            print(f"\n📂 {repo_name}의 브랜치 조회 중...")
            branches = self.github_client.fetch_branches(owner, repo_name)

            if not branches:
                print(f"  브랜치가 없습니다.")
                continue

            print(f"\n  총 {len(branches)}개의 브랜치:")
            for i, branch in enumerate(branches, 1):
                print(f"    {i}. {branch}")

            # 브랜치 선택
            while True:
                try:
                    selection = input(f"  브랜치 번호 입력 (1-{len(branches)}, 또는 'all'): ").strip()

                    if selection.lower() == 'all':
                        selected_branches = branches
                        break
                    else:
                        idx = int(selection) - 1
                        if 0 <= idx < len(branches):
                            selected_branches = [branches[idx]]
                            break
                        else:
                            print(f"  1부터 {len(branches)} 사이의 숫자를 입력하세요.")
                except ValueError:
                    print("  올바른 숫자를 입력하세요.")

            # 3. 선택된 브랜치에서 커밋 수집
            for branch in selected_branches:
                print(f"\n  🔍 {repo_name}/{branch} 커밋 수집 중...")
                commits = self.github_client.fetch_branch_commits(
                    owner, repo_name, branch, start_date, end_date
                )

                if commits:
                    print(f"    {len(commits)}개 커밋 발견")
                    all_commits.extend(commits)
                else:
                    print(f"    커밋 없음")

        print(f"\n총 {len(all_commits)}개의 커밋 수집 완료")

        # 4. 중복 체크
        new_commits = []
        duplicate_commits = []

        for commit in all_commits:
            sha = commit.get("oid")
            message = commit.get("message", "")[:50]

            if self.duplicate_checker.is_duplicate_baekjoon(sha) or self.duplicate_checker.is_duplicate_commit(sha):
                duplicate_commits.append(f"{sha[:7]} - {message}")
            else:
                new_commits.append(commit)

        if duplicate_commits:
            print(f"\n  ⚠️  중복 제외: {len(duplicate_commits)}개 (이미 저장됨)")
        else:
            print(f"\n  ✓ 모든 커밋이 신규입니다")

        # 5. 백준 / 개발 분류
        baekjoon_commits = []
        dev_commits = []

        for commit in new_commits:
            if self.classifier.is_baekjoon_commit(commit):
                baekjoon_commits.append(commit)
            else:
                dev_commits.append(commit)

        print(f"  분류 완료 - 백준: {len(baekjoon_commits)}, 개발: {len(dev_commits)}")

        # 6. JSON 저장
        baekjoon_files = self._save_baekjoon_commits(baekjoon_commits)
        dev_files = self._save_dev_commits(dev_commits)

        return baekjoon_files, dev_files

    def _save_baekjoon_commits(self, commits: List[dict]) -> List[str]:
        """백준 커밋을 JSON으로 저장"""
        saved_files = []
        total = len(commits)

        for idx, commit in enumerate(commits, 1):
            print(f"    백준 처리 중: {idx}/{total}", end='\r', flush=True)

            # 1. 커밋 메시지에서 추출 (로컬 작업, API 호출 없음)
            problem_name = self._extract_problem_name(commit)
            tier = self._extract_tier(commit)
            runtime = self._extract_runtime(commit)
            memory = self._extract_memory(commit)

            # 2. REST API 1-2번 호출로 나머지 정보 추출
            rest_info = self._fetch_baekjoon_rest_info(commit)

            # 백준 정보 구성
            baekjoon_data = {
                "문제_번호": rest_info.get("문제_번호", "Unknown"),
                "문제명": problem_name,
                "티어": tier,
                "풀이_코드": rest_info.get("풀이_코드", ""),
                "실행_시간": runtime,
                "메모리": memory,
                "언어": rest_info.get("언어", "Unknown"),
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

            # REST API 1번 호출로 파일 목록 가져오기
            changed_files = self._fetch_changed_files(commit)

            # 개발 커밋 정보 추출
            dev_data = {
                "커밋_메시지": commit.get("message"),
                "SHA": commit.get("oid"),
                "변경된_파일_목록": changed_files,
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

    def _fetch_baekjoon_rest_info(self, commit: dict) -> dict:
        """
        REST API 호출로 백준 정보 추출 (1-2번 호출)
        - 문제 번호 (파일 경로에서)
        - 언어 (확장자에서)
        - 풀이 코드 (raw_url에서)
        """
        import re
        import requests

        owner = os.getenv("GITHUB_USERNAME")
        repo = commit.get("repository")
        sha = commit.get("oid")

        result = {
            "문제_번호": "Unknown",
            "언어": "Unknown",
            "풀이_코드": ""
        }

        if not all([owner, repo, sha]):
            return result

        try:
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            # REST API 호출 #1: 커밋 상세 정보 (파일 목록)
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return result

            commit_data = response.json()
            files = commit_data.get("files", [])

            # 언어별 확장자 매핑
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

            # files 배열을 한 번만 순회하며 모든 정보 추출
            for file in files:
                filename = file.get("filename", "")

                # 백준 폴더 내의 코드 파일인지 확인 (README.md 제외)
                if "백준/" in filename and not filename.endswith("README.md"):
                    # 문제 번호 추출 (여러 패턴 시도)
                    problem_number = self._extract_problem_number_from_path(filename)
                    if problem_number:
                        result["문제_번호"] = problem_number

                    # 언어 추출 (확장자)
                    for ext, lang in extension_to_language.items():
                        if filename.endswith(ext):
                            result["언어"] = lang
                            break

                    # 풀이 코드 추출 (raw_url로 별도 요청)
                    raw_url = file.get("raw_url")
                    if raw_url:
                        # REST API 호출 #2: 파일 내용
                        raw_response = requests.get(raw_url, headers=headers, timeout=10)
                        if raw_response.status_code == 200:
                            result["풀이_코드"] = raw_response.text

                    # 코드 파일 찾았으면 종료
                    break

            return result

        except Exception as e:
            print(f"  REST API 호출 실패 (SHA: {sha[:7]}): {str(e)}")
            return result

    def _fetch_changed_files(self, commit: dict) -> list:
        """REST API로 변경된 파일 목록 가져오기 (1번 호출)"""
        import requests

        owner = os.getenv("GITHUB_USERNAME")
        repo = commit.get("repository")
        sha = commit.get("oid")

        if not all([owner, repo, sha]):
            return []

        try:
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            # REST API 호출: 커밋 상세 정보
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

    def _extract_problem_name(self, commit: dict) -> str:
        """
        커밋 메시지에서 문제 이름 추출 (로컬 작업)
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
        티어 정보 추출 (로컬 작업)
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
        """커밋 메시지에서 실행 시간 추출 (로컬 작업)"""
        import re
        message = commit.get("message", "")

        # Time: X ms 패턴
        match = re.search(r'Time:\s*(\d+)\s*ms', message)
        if match:
            return f"{match.group(1)} ms"

        return ""

    def _extract_memory(self, commit: dict) -> str:
        """커밋 메시지에서 메모리 추출 (로컬 작업)"""
        import re
        message = commit.get("message", "")

        # Memory: Y KB 패턴
        match = re.search(r'Memory:\s*(\d+)\s*KB', message)
        if match:
            return f"{match.group(1)} KB"

        return ""

    def _extract_problem_number_from_path(self, filepath: str) -> str:
        """
        파일 경로에서 백준 문제 번호 추출 (여러 패턴 지원)

        지원 형식:
        - 백준/티어/12345. 문제명/solution.py
        - 백준/티어/12345/solution.py
        - 백준/티어/12345/문제명.py
        - 백준/티어/12345_문제명/solution.py
        """
        import re

        # 다양한 패턴 시도 (우선순위 순)
        patterns = [
            r'백준/[^/]+/(\d+)\.',      # 백준/티어/12345.문제명/
            r'백준/[^/]+/(\d+)/',       # 백준/티어/12345/
            r'백준/[^/]+/(\d+)_',       # 백준/티어/12345_문제명/
            r'/(\d{4,5})\.',            # 아무 경로에서 4-5자리 숫자.
            r'/(\d{4,5})/',             # 아무 경로에서 4-5자리 숫자/
            r'/(\d{4,5})_',             # 아무 경로에서 4-5자리 숫자_
        ]

        for pattern in patterns:
            match = re.search(pattern, filepath)
            if match:
                return match.group(1)

        return None


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    from datetime import timedelta
    collector = GitHubCollector()
    end = datetime.now()
    start = end - timedelta(days=30)
    collector.collect(start, end)
