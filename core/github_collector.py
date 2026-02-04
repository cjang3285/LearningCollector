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
from policies.collection_rules import CollectionRules


class GitHubCollector:
    """GitHub 수집 클래스"""

    def __init__(self):
        self.github_client = GitHubGraphQLClient()
        self.duplicate_checker = DuplicateChecker()
        self.json_saver = JSONSaver()

    def collect(self, start_date: datetime, end_date: datetime) -> Tuple[List[str], List[str]]:
        """
        GitHub에서 커밋 수집 (auto 모드)

        Returns:
            Tuple[List[str], List[str]]: (백준 JSON 파일명 리스트, 개발 JSON 파일명 리스트)
        """
        username = os.getenv("GITHUB_USERNAME")

        # 1. GitHub GraphQL로 커밋 수집
        print(f"  GitHub 사용자 {username}의 모든 레포, 모든 브랜치 조회 중...")
        commits = self.github_client.fetch_commits(username, start_date, end_date)
        print(f"  총 {len(commits)}개의 커밋 발견")

        # 2. 레포 기반으로 백준/개발 분류 + 중복 체크
        baekjoon_commits = []
        dev_commits = []
        duplicate_count = 0

        for commit in commits:
            sha = commit.get("oid")
            repo_name = commit.get("repository", "")

            # 레포 이름으로 백준/개발 판단
            is_baekjoon_repo = CollectionRules.is_baekjoon_repo(repo_name)

            if is_baekjoon_repo:
                # 백준 레포 커밋 → 백준 중복 체크
                if self.duplicate_checker.is_duplicate_baekjoon(sha):
                    duplicate_count += 1
                else:
                    baekjoon_commits.append(commit)
            else:
                # 개발 레포 커밋 → 개발 중복 체크
                if self.duplicate_checker.is_duplicate_commit(sha):
                    duplicate_count += 1
                else:
                    dev_commits.append(commit)

        # 3. 결과 출력
        print(f"  분류 완료 - 백준: {len(baekjoon_commits)}, 개발: {len(dev_commits)}")
        if duplicate_count > 0:
            print(f"  ⚠️  중복 제외: {duplicate_count}개 (이미 저장됨)")

        # 4. JSON 저장
        baekjoon_files = self._save_baekjoon_commits(baekjoon_commits)
        dev_files = self._save_dev_commits(dev_commits)

        return baekjoon_files, dev_files

    def collect_interactive(self, start_date: datetime, end_date: datetime) -> Tuple[List[str], List[str]]:
        """
        대화형으로 레포/브랜치 선택하여 커밋 수집
        백준 레포는 자동 수집하고, 개발 레포만 선택지에 표시

        Returns:
            Tuple[List[str], List[str]]: (백준 JSON 파일명 리스트, 개발 JSON 파일명 리스트)
        """
        username = os.getenv("GITHUB_USERNAME")

        # 1. 레포 조회 및 백준/개발 분리
        print(f"\n📦 {username}의 레포지토리 조회 중...")
        repos = self.github_client.fetch_repositories(username)

        if not repos:
            print("레포지토리가 없습니다.")
            return [], []

        # 백준 레포와 개발 레포 분리
        baekjoon_repos = []
        dev_repos = []
        for repo in repos:
            if CollectionRules.is_baekjoon_repo(repo['name']):
                baekjoon_repos.append(repo)
            else:
                dev_repos.append(repo)

        # 레포 분리 시점에서 바로 백준/개발 커밋 분리
        baekjoon_commits = []
        dev_commits = []
        duplicate_count = 0

        # 2. 백준 레포 자동 수집 (모든 브랜치)
        if baekjoon_repos:
            print(f"\n🎯 백준 레포 자동 수집 ({len(baekjoon_repos)}개)")
            for repo in baekjoon_repos:
                repo_name = repo['name']
                owner = repo['owner']['login']
                print(f"  📂 {repo_name} 수집 중...")

                branches = self.github_client.fetch_branches(owner, repo_name)
                for branch in branches:
                    commits = self.github_client.fetch_branch_commits(
                        owner, repo_name, branch, start_date, end_date
                    )
                    if commits:
                        print(f"    {branch}: {len(commits)}개 커밋")
                        # 중복 체크 후 바로 백준 커밋에 추가
                        for commit in commits:
                            sha = commit.get("oid")
                            if self.duplicate_checker.is_duplicate_baekjoon(sha):
                                duplicate_count += 1
                            else:
                                baekjoon_commits.append(commit)

        # 3. 개발 레포 선택
        if not dev_repos:
            print("\n개발 레포가 없습니다.")
        else:
            print(f"\n📦 개발 레포지토리 ({len(dev_repos)}개):")
            for i, repo in enumerate(dev_repos, 1):
                print(f"  {i}. {repo['name']}")

            # 레포 선택
            while True:
                try:
                    selection = input(f"\n레포 번호 입력 (1-{len(dev_repos)}, 'all', 또는 'n' 스킵): ").strip()

                    if selection.lower() == 'n':
                        selected_repos = []
                        break
                    elif selection.lower() == 'all':
                        selected_repos = dev_repos
                        break
                    else:
                        idx = int(selection) - 1
                        if 0 <= idx < len(dev_repos):
                            selected_repos = [dev_repos[idx]]
                            break
                        else:
                            print(f"1부터 {len(dev_repos)} 사이의 숫자를 입력하세요.")
                except ValueError:
                    print("올바른 숫자를 입력하세요.")

            # 4. 선택된 레포별로 브랜치 선택
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

                # 5. 선택된 브랜치에서 커밋 수집
                for branch in selected_branches:
                    print(f"\n  🔍 {repo_name}/{branch} 커밋 수집 중...")
                    commits = self.github_client.fetch_branch_commits(
                        owner, repo_name, branch, start_date, end_date
                    )

                    if commits:
                        print(f"    {len(commits)}개 커밋 발견")
                        # 중복 체크 후 바로 개발 커밋에 추가
                        for commit in commits:
                            sha = commit.get("oid")
                            if self.duplicate_checker.is_duplicate_commit(sha):
                                duplicate_count += 1
                            else:
                                dev_commits.append(commit)
                    else:
                        print(f"    커밋 없음")

        # 6. 결과 출력
        total_new = len(baekjoon_commits) + len(dev_commits)
        print(f"\n수집 완료 - 백준: {len(baekjoon_commits)}, 개발: {len(dev_commits)}")
        if duplicate_count > 0:
            print(f"  ⚠️  중복 제외: {duplicate_count}개 (이미 저장됨)")

        # 7. JSON 저장
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

            # REST API 1번 호출로 파일 상세 정보 가져오기
            file_details = self._fetch_changed_files(commit)

            # 개발 커밋 정보 추출
            dev_data = {
                "커밋_메시지": commit.get("message"),
                "SHA": commit.get("oid"),
                "변경된_파일_목록": file_details["파일_목록"],
                "추가_라인": file_details["추가_라인"],
                "삭제_라인": file_details["삭제_라인"],
                "변경_내용": file_details["변경_내용"],
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

            # 코드 파일과 README 분리
            code_file = None
            readme_file = None

            for file in files:
                filename = file.get("filename", "")
                if "백준/" in filename:
                    if filename.endswith("README.md"):
                        readme_file = file
                    elif not code_file:  # 첫 번째 코드 파일만
                        for ext in extension_to_language:
                            if filename.endswith(ext):
                                code_file = file
                                break

            # 코드 파일에서 언어, 풀이 코드 추출
            if code_file:
                filename = code_file.get("filename", "")

                # 문제 번호 추출 (경로에서 시도)
                problem_number = self._extract_problem_number_from_path(filename)
                if problem_number:
                    result["문제_번호"] = problem_number

                # 언어 추출 (확장자)
                for ext, lang in extension_to_language.items():
                    if filename.endswith(ext):
                        result["언어"] = lang
                        break

                # 풀이 코드 추출
                raw_url = code_file.get("raw_url")
                if raw_url:
                    raw_response = requests.get(raw_url, headers=headers, timeout=10)
                    if raw_response.status_code == 200:
                        result["풀이_코드"] = raw_response.text

            # 경로에서 번호 못 찾으면 README에서 추출
            if result["문제_번호"] == "Unknown" and readme_file:
                raw_url = readme_file.get("raw_url")
                if raw_url:
                    raw_response = requests.get(raw_url, headers=headers, timeout=10)
                    if raw_response.status_code == 200:
                        readme_content = raw_response.text
                        # README 형식: # [티어] 문제명 - 1629
                        match = re.search(r'#\s*\[.*?\].*?-\s*(\d+)', readme_content)
                        if match:
                            result["문제_번호"] = match.group(1)

            return result

        except Exception as e:
            print(f"  REST API 호출 실패 (SHA: {sha[:7]}): {str(e)}")
            return result

    def _fetch_changed_files(self, commit: dict) -> dict:
        """
        REST API로 변경된 파일 상세 정보 가져오기 (1번 호출)

        Returns:
            dict: {
                "파일_목록": List[str],      # 전체 변경 파일명 리스트
                "추가_라인": int,             # 총 추가 라인
                "삭제_라인": int,             # 총 삭제 라인
                "변경_내용": List[dict]       # 상위 5개 코드 파일의 패치
            }
        """
        import requests

        owner = os.getenv("GITHUB_USERNAME")
        repo = commit.get("repository")
        sha = commit.get("oid")

        result = {
            "파일_목록": [],
            "추가_라인": 0,
            "삭제_라인": 0,
            "변경_내용": []
        }

        if not all([owner, repo, sha]):
            return result

        try:
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            # REST API 호출: 커밋 상세 정보
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return result

            commit_data = response.json()
            files = commit_data.get("files", [])

            # 전체 파일명 리스트
            result["파일_목록"] = [file.get("filename") for file in files]

            # 코드 파일 확장자 (바이너리/비코드 제외)
            code_extensions = {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".kt", ".go",
                ".cpp", ".cc", ".c", ".h", ".hpp", ".cs", ".rb", ".rs",
                ".swift", ".scala", ".php", ".vue", ".svelte", ".html",
                ".css", ".scss", ".sass", ".less", ".sql", ".sh", ".bash",
                ".zsh", ".yaml", ".yml", ".json", ".xml", ".md", ".txt"
            }

            # 코드 파일만 필터링 및 변경량 기준 정렬
            code_files = []
            for file in files:
                filename = file.get("filename", "")
                # 확장자 체크
                ext = ""
                if "." in filename:
                    ext = "." + filename.rsplit(".", 1)[-1].lower()

                if ext in code_extensions:
                    additions = file.get("additions", 0)
                    deletions = file.get("deletions", 0)
                    patch = file.get("patch", "")

                    # 패치가 있는 파일만 추가
                    if patch:
                        code_files.append({
                            "파일명": filename,
                            "추가": additions,
                            "삭제": deletions,
                            "패치": patch
                        })

            # 변경량 기준 정렬 (additions + deletions)
            code_files.sort(key=lambda x: x["추가"] + x["삭제"], reverse=True)

            # 상위 5개만 선택
            top_files = code_files[:5]

            # 총 라인 수 계산 (전체 파일 기준)
            for file in files:
                result["추가_라인"] += file.get("additions", 0)
                result["삭제_라인"] += file.get("deletions", 0)

            # 변경 내용 구성
            result["변경_내용"] = top_files

            return result

        except Exception as e:
            print(f"  파일 목록 조회 실패 (SHA: {sha[:7]}): {str(e)}")
            return result

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
