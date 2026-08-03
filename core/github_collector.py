"""
GitHub 수집 모듈 (메인 흐름)
GraphQL로 수집 정책에서 도출된 수집 기간 동안 나와 claude가 한 커밋들을 모든 레포, 모든 브랜치에서 찾아온다
"""
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Tuple

# API 모듈 임포트
from api.github_graphql import GitHubGraphQLClient

# 정책 모듈 임포트
from policies.storage.json_saver import JSONSaver
from policies.storage.duplicate_checker import DuplicateChecker
from policies.collection_rules import CollectionRules
from core import structured_logger as slog

# 커밋별 REST 상세 조회 병렬 실행 수 (서로 독립적인 요청)
MAX_CONCURRENT_REST_FETCHES = 5

# 같은 레포에서 같은 파일 집합을 이 시간 안에 연속으로 고친 커밋은 사실상 하나의
# 즉흥 수정(오타/들여쓰기 재작업 등)으로 보고 마지막 것만 남긴다. Promtail YAML
# 들여쓰기를 8분 사이 3번 고친 커밋이 거의 동일한 블로그 글 3개로 이어졌던 사례가
# 있어서 도입함 — 각 커밋이 독립적으로 draft화되는 한 이런 군집은 계속 중복 포스팅된다.
RAPID_FOLLOWUP_WINDOW_SECONDS = 30 * 60


def _parse_committed_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.rstrip("Z"))
    except ValueError:
        return None


class GitHubCollector:
    """GitHub 수집 클래스"""

    def __init__(self):
        self.github_client = GitHubGraphQLClient()
        self.duplicate_checker = DuplicateChecker()
        self.json_saver = JSONSaver()

    def collect(self, start_date: datetime, end_date: datetime) -> Tuple[List[str], List[str], List[str]]:
        """
        GitHub에서 커밋 수집 (auto 모드)

        Returns:
            Tuple[List[str], List[str], List[str]]:
                (백준 JSON 파일명 리스트, 개발 JSON 파일명 리스트, PR JSON 파일명 리스트)
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

            # 백준 서비스 종료로 백준 레포 수집을 비활성화함 (아래 원래 분류 로직은
            # 주석 처리만 해두고 남겨둠. 필요해지면 이 블록을 되살리면 됨)
            # is_baekjoon_repo = CollectionRules.is_baekjoon_repo(repo_name)
            # if is_baekjoon_repo:
            #     # 백준 레포 커밋 → 백준 중복 체크
            #     if self.duplicate_checker.is_duplicate_baekjoon(sha):
            #         duplicate_count += 1
            #     else:
            #         baekjoon_commits.append(commit)
            # else:
            #     # 개발 레포 커밋 → 개발 중복 체크
            #     if self.duplicate_checker.is_duplicate_commit(sha):
            #         duplicate_count += 1
            #     else:
            #         dev_commits.append(commit)
            if CollectionRules.is_baekjoon_repo(repo_name):
                continue  # 백준 레포는 더 이상 수집하지 않음

            # 개발 레포 커밋 → 개발 중복 체크
            if self.duplicate_checker.is_duplicate_commit(sha):
                duplicate_count += 1
            else:
                dev_commits.append(commit)

        # 3. 결과 출력
        print(f"  분류 완료 - 백준: {len(baekjoon_commits)}, 개발: {len(dev_commits)}")
        if duplicate_count > 0:
            print(f"  ⚠️  중복 제외: {duplicate_count}개 (이미 저장됨)")

        slog.info("github_classify", "github_collector",
                  total_commits=len(commits),
                  baekjoon=len(baekjoon_commits), dev=len(dev_commits),
                  duplicates=duplicate_count)

        # 4. JSON 저장
        # 개발 커밋은 더 이상 개별 포스팅하지 않는다. 임시 파일 정리/검증용 커밋처럼
        # 자잘한 단위까지 그대로 블로그 글이 되어 너무 잘게 쪼개진 포스팅이 쌓였고,
        # website 레포처럼 PR로 병합되는 워크플로에서는 PR 요약 draft가 이미 그
        # 작업 전체를 한 번에 설명하므로 개별 커밋 포스팅이 불필요한 중복이었다.
        # 이제 auto 모드에서는 PR 요약만 포스팅 대상으로 삼는다.
        baekjoon_files = self._save_baekjoon_commits(baekjoon_commits)
        dev_files = []

        slog.json_save_summary("baekjoon", saved=len(baekjoon_files),
                               duplicates=0)
        slog.json_save_summary("commits", saved=len(dev_files),
                               duplicates=0)

        # 5. PR 수집 (병합/닫힌 PR만 - 조직 레포 포함)
        prs = self._collect_prs(username, start_date, end_date)
        pr_files = self._save_prs(prs)

        slog.json_save_summary("prs", saved=len(pr_files), duplicates=0)

        return baekjoon_files, dev_files, pr_files

    def _collect_prs(self, username: str, start_date: datetime, end_date: datetime) -> List[dict]:
        """
        이번 수집 기간에 활동이 있었던 레포들의 병합/닫힌 PR을 조회
        (열려있는 PR은 나중에 커밋이 더 붙을 수 있어서 fetch_pull_requests에서 이미 제외됨)
        """
        print("  PR 조회 중...")
        repositories = self.github_client.fetch_repositories(username)

        active_repos = []
        for repo in repositories:
            pushed_at = self.github_client.parse_github_timestamp(repo.get("pushedAt"))
            if pushed_at is not None and pushed_at < start_date:
                continue
            active_repos.append(repo)

        all_prs = []
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REST_FETCHES) as executor:
            future_to_repo = {
                executor.submit(
                    self.github_client.fetch_pull_requests,
                    repo["owner"]["login"], repo["name"], start_date, end_date
                ): repo["name"]
                for repo in active_repos
            }
            for future in as_completed(future_to_repo):
                try:
                    all_prs.extend(future.result())
                except Exception:
                    pass

        print(f"  → {len(all_prs)}개의 PR(병합/닫힘) 발견")
        return all_prs

    def collect_interactive(self, start_date: datetime, end_date: datetime) -> Tuple[List[str], List[str], List[str]]:
        """
        대화형으로 레포/브랜치 선택하여 커밋 수집
        백준 레포는 자동 수집하고, 개발 레포만 선택지에 표시

        Returns:
            Tuple[List[str], List[str], List[str]]:
                (백준 JSON 파일명 리스트, 개발 JSON 파일명 리스트, PR JSON 파일명 리스트)
        """
        username = os.getenv("GITHUB_USERNAME")
        author_filter = self.github_client.get_own_author_filter()

        # 1. 레포 조회 및 백준/개발 분리
        print(f"\n📦 {username}의 레포지토리 조회 중...")
        repos = self.github_client.fetch_repositories(username)

        if not repos:
            print("레포지토리가 없습니다.")
            return [], [], []

        # 백준 서비스 종료로 백준 레포는 수집 대상에서 완전히 제외함
        # (원래는 아래처럼 baekjoon_repos/dev_repos로 나눠서 백준 레포를 자동 수집했음.
        #  그 블록은 통째로 주석 처리해두고, dev_repos만 남김. 필요해지면 복구하면 됨)
        # baekjoon_repos = []
        # dev_repos = []
        # for repo in repos:
        #     if CollectionRules.is_baekjoon_repo(repo['name']):
        #         baekjoon_repos.append(repo)
        #     else:
        #         dev_repos.append(repo)
        dev_repos = [r for r in repos if not CollectionRules.is_baekjoon_repo(r['name'])]

        # 레포 분리 시점에서 바로 백준/개발 커밋 분리
        baekjoon_commits = []
        dev_commits = []
        prs = []
        duplicate_count = 0

        # 2. 백준 레포 자동 수집 (모든 브랜치) - 백준 서비스 종료로 비활성화
        # if baekjoon_repos:
        #     print(f"\n🎯 백준 레포 자동 수집 ({len(baekjoon_repos)}개)")
        #     for repo in baekjoon_repos:
        #         repo_name = repo['name']
        #         owner = repo['owner']['login']
        #         print(f"  📂 {repo_name} 수집 중...")
        #
        #         branches = self.github_client.fetch_branches(owner, repo_name)
        #         for branch in branches:
        #             commits = self.github_client.fetch_branch_commits(
        #                 owner, repo_name, branch, start_date, end_date
        #             )
        #             if commits:
        #                 print(f"    {branch}: {len(commits)}개 커밋")
        #                 # 중복 체크 후 바로 백준 커밋에 추가
        #                 for commit in commits:
        #                     sha = commit.get("oid")
        #                     if self.duplicate_checker.is_duplicate_baekjoon(sha):
        #                         duplicate_count += 1
        #                     else:
        #                         baekjoon_commits.append(commit)

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
                        owner, repo_name, branch, start_date, end_date, author_filter
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

                # 선택된 레포의 병합/닫힌 PR도 함께 수집
                print(f"  🔀 {repo_name}의 PR 조회 중...")
                repo_prs = self.github_client.fetch_pull_requests(owner, repo_name, start_date, end_date)
                if repo_prs:
                    print(f"    {len(repo_prs)}개 PR(병합/닫힘) 발견")
                    prs.extend(repo_prs)

        # 6. 결과 출력
        total_new = len(baekjoon_commits) + len(dev_commits)
        print(f"\n수집 완료 - 백준: {len(baekjoon_commits)}, 개발: {len(dev_commits)}")
        if duplicate_count > 0:
            print(f"  ⚠️  중복 제외: {duplicate_count}개 (이미 저장됨)")

        slog.info("github_classify", "github_collector",
                  total_commits=len(baekjoon_commits) + len(dev_commits) + duplicate_count,
                  baekjoon=len(baekjoon_commits), dev=len(dev_commits),
                  duplicates=duplicate_count)

        # 7. JSON 저장
        baekjoon_files = self._save_baekjoon_commits(baekjoon_commits)
        dev_files = self._save_dev_commits(dev_commits)
        pr_files = self._save_prs(prs)

        slog.json_save_summary("baekjoon", saved=len(baekjoon_files),
                               duplicates=0)
        slog.json_save_summary("commits", saved=len(dev_files),
                               duplicates=0)
        slog.json_save_summary("prs", saved=len(pr_files), duplicates=0)

        return baekjoon_files, dev_files, pr_files

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

    def _is_own_author(self, author: str) -> bool:
        """
        본인 작성으로 취급할 작성자인지 판단.
        본인 GitHub 계정 또는 "claude"(Claude Code로 커밋 시 찍히는 이름 - 실질적으로
        본인 작업)면 True. 그 외(팀원 계정)는 False.
        """
        if not author:
            return False
        my_username = os.getenv("GITHUB_USERNAME", "")
        return author.lower() in (my_username.lower(), "claude")

    def _collapse_rapid_followups(self, commits: List[dict], file_details_list: List[dict]) -> set:
        """
        같은 레포·같은 파일 집합을 RAPID_FOLLOWUP_WINDOW_SECONDS 안에 연속으로
        건드린 커밋들을 하나의 군집으로 묶어, 군집당 마지막 커밋(최종 상태)의
        인덱스만 남긴다. 파일 목록을 못 가져온 커밋(빈 리스트)은 묶을 근거가
        없으므로 항상 그대로 유지한다.

        Returns:
            set: 유지할 commits 인덱스 집합
        """
        groups = defaultdict(list)
        keep = set()

        for idx, commit in enumerate(commits):
            files = tuple(sorted(file_details_list[idx].get("파일_목록", [])))
            if not files:
                keep.add(idx)
                continue
            key = (commit.get("repository"), files)
            groups[key].append(idx)

        dropped = 0
        for key, idxs in groups.items():
            if len(idxs) == 1:
                keep.add(idxs[0])
                continue

            idxs_sorted = sorted(idxs, key=lambda i: commits[i].get("committedDate") or "")
            cluster_last = idxs_sorted[0]
            for i in idxs_sorted[1:]:
                prev_dt = _parse_committed_date(commits[cluster_last].get("committedDate"))
                cur_dt = _parse_committed_date(commits[i].get("committedDate"))
                if prev_dt and cur_dt and (cur_dt - prev_dt).total_seconds() <= RAPID_FOLLOWUP_WINDOW_SECONDS:
                    dropped += 1
                    cluster_last = i
                else:
                    keep.add(cluster_last)
                    cluster_last = i
            keep.add(cluster_last)

        if dropped:
            window_min = RAPID_FOLLOWUP_WINDOW_SECONDS // 60
            print(f"    ⚠️  같은 파일 연속 수정 묶음 제외: {dropped}개 (같은 파일을 {window_min}분 이내 연속 수정 — 마지막 커밋만 유지)")

        return keep

    def _save_dev_commits(self, commits: List[dict]) -> List[str]:
        """개발 커밋을 JSON으로 저장 (팀원이 작성한 커밋은 블로그에 올리지 않으므로 스킵)"""
        own_commits = []
        skipped = 0
        for commit in commits:
            author_info = commit.get("author") or {}
            author_login = (author_info.get("user") or {}).get("login")
            author_display = author_login or author_info.get("name") or author_info.get("email") or "Unknown"
            if self._is_own_author(author_display):
                own_commits.append(commit)
            else:
                skipped += 1
        if skipped:
            print(f"    팀원 작성 커밋 {skipped}개 스킵 (본인 작성만 블로그에 포스팅)")
        commits = own_commits

        saved_files = []
        total = len(commits)

        # 커밋별 REST 상세 조회는 서로 완전히 독립적이므로 병렬로 먼저 가져온 뒤,
        # 저장(중복 체크 포함)은 순서대로 처리한다 (중복 체크 캐시를 동시에
        # 건드리지 않도록 저장 단계는 순차 실행 유지).
        file_details_list = [None] * total
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REST_FETCHES) as executor:
            future_to_idx = {
                executor.submit(self._fetch_changed_files, commit): idx
                for idx, commit in enumerate(commits)
            }
            done = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                done += 1
                print(f"    개발 커밋 상세 조회 중: {done}/{total}", end='\r', flush=True)
                try:
                    file_details_list[idx] = future.result()
                except Exception:
                    file_details_list[idx] = {
                        "파일_목록": [], "추가_라인": 0, "삭제_라인": 0, "변경_내용": []
                    }
        if total > 0:
            print()  # 줄바꿈

        keep_indices = self._collapse_rapid_followups(commits, file_details_list)
        if len(keep_indices) < total:
            commits = [c for i, c in enumerate(commits) if i in keep_indices]
            file_details_list = [d for i, d in enumerate(file_details_list) if i in keep_indices]
            total = len(commits)

        for idx, commit in enumerate(commits, 1):
            print(f"    개발 커밋 처리 중: {idx}/{total}", end='\r', flush=True)

            file_details = file_details_list[idx - 1]

            # 커밋 작성자 (GitHub 로그인 우선, 연결 안 된 계정이면 이름/이메일로 폴백)
            author_info = commit.get("author") or {}
            author_login = (author_info.get("user") or {}).get("login")
            author_display = author_login or author_info.get("name") or author_info.get("email") or "Unknown"

            # 개발 커밋 정보 추출
            dev_data = {
                "커밋_메시지": commit.get("message"),
                "SHA": commit.get("oid"),
                "작성자": author_display,
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

    def _save_prs(self, prs: List[dict]) -> List[str]:
        """PR을 JSON으로 저장 (병합/닫힌 PR만 넘어옴, 팀원이 작성한 PR은 블로그에 올리지 않으므로 스킵)"""
        own_prs = []
        skipped = 0
        for pr in prs:
            author = (pr.get("author") or {}).get("login", "")
            if self._is_own_author(author):
                own_prs.append(pr)
            else:
                skipped += 1
        if skipped:
            print(f"    팀원 작성 PR {skipped}개 스킵 (본인 작성만 블로그에 포스팅)")
        prs = own_prs

        saved_files = []
        total = len(prs)

        # PR별 파일 diff 조회(REST)도 서로 독립적이므로 병렬로 먼저 가져옴
        file_details_list = [None] * total
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REST_FETCHES) as executor:
            future_to_idx = {
                executor.submit(self._fetch_pr_changed_files, pr): idx
                for idx, pr in enumerate(prs)
            }
            done = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                done += 1
                print(f"    PR 상세 조회 중: {done}/{total}", end='\r', flush=True)
                try:
                    file_details_list[idx] = future.result()
                except Exception:
                    file_details_list[idx] = {"파일_목록": [], "변경_내용": []}
        if total > 0:
            print()  # 줄바꿈

        for idx, pr in enumerate(prs, 1):
            print(f"    PR 처리 중: {idx}/{total}", end='\r', flush=True)

            file_details = file_details_list[idx - 1]
            commit_nodes = pr.get("commits", {}).get("nodes", [])

            pr_data = {
                "PR_번호": pr.get("number"),
                "제목": pr.get("title"),
                "설명": pr.get("body") or "",
                "상태": "merged" if pr.get("mergedAt") else "closed",
                "레포지토리": pr.get("repository"),
                "브랜치": pr.get("headRefName"),
                "베이스_브랜치": pr.get("baseRefName"),
                "작성자": (pr.get("author") or {}).get("login", "unknown"),
                "생성일": pr.get("createdAt"),
                "병합일": pr.get("mergedAt"),
                "PR_URL": pr.get("url"),
                "추가_라인": pr.get("additions", 0),
                "삭제_라인": pr.get("deletions", 0),
                "변경된_파일_목록": file_details["파일_목록"],
                "변경_내용": file_details["변경_내용"],
                "커밋_메시지_목록": [c["commit"]["message"] for c in commit_nodes if c.get("commit")],
                "PR_ID": pr.get("id"),
            }

            filename = self.json_saver.save_pr(pr_data)
            if filename:
                saved_files.append(filename)

        if total > 0:
            print()  # 줄바꿈
        return saved_files

    def _fetch_pr_changed_files(self, pr: dict) -> dict:
        """
        REST API로 PR의 변경 파일 상세 정보 가져오기 (패치/diff 포함).
        GraphQL의 PR files 커넥션은 patch를 안 주기 때문에 REST를 사용.

        Returns:
            dict: {"파일_목록": List[str], "변경_내용": List[dict]}
        """
        import requests

        owner = pr.get("repo_owner")
        repo = pr.get("repository")
        number = pr.get("number")

        result = {"파일_목록": [], "변경_내용": []}

        if not all([owner, repo, number]):
            return result

        try:
            token = os.getenv("GITHUB_TOKEN")
            headers = {"Authorization": f"token {token}"}

            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files"
            t = slog.start_timer()
            response = requests.get(url, headers=headers, timeout=10, params={"per_page": 100})
            slog.api_call("github_rest", "GET",
                          f"/repos/{owner}/{repo}/pulls/{number}/files",
                          response.status_code, slog.elapsed_ms(t),
                          response.status_code == 200)

            if response.status_code != 200:
                return result

            files = response.json()
            result["파일_목록"] = [f.get("filename") for f in files]

            # 변경량 기준 정렬 후 상위 5개 파일만 patch 포함
            files_sorted = sorted(
                files, key=lambda f: f.get("additions", 0) + f.get("deletions", 0), reverse=True
            )
            for f in files_sorted[:5]:
                patch = f.get("patch")
                if patch:
                    result["변경_내용"].append({
                        "파일명": f.get("filename"),
                        "추가": f.get("additions", 0),
                        "삭제": f.get("deletions", 0),
                        "패치": patch
                    })

            return result

        except Exception as e:
            slog.api_error("github_rest", "GET",
                           f"/repos/{owner}/{repo}/pulls/{number}/files",
                           0, str(e))
            print(f"  PR 파일 목록 조회 실패 (PR #{number}): {str(e)}")
            return result

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
            t = slog.start_timer()
            response = requests.get(url, headers=headers, timeout=10)
            slog.api_call("github_rest", "GET",
                          f"/repos/{owner}/{repo}/commits/{sha[:7]}",
                          response.status_code, slog.elapsed_ms(t),
                          response.status_code == 200)

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
                    t = slog.start_timer()
                    raw_response = requests.get(raw_url, headers=headers, timeout=10)
                    slog.api_call("github_rest", "GET", "raw_content/code",
                                  raw_response.status_code, slog.elapsed_ms(t),
                                  raw_response.status_code == 200)
                    if raw_response.status_code == 200:
                        result["풀이_코드"] = raw_response.text

            # 경로에서 번호 못 찾으면 README에서 추출
            if result["문제_번호"] == "Unknown" and readme_file:
                raw_url = readme_file.get("raw_url")
                if raw_url:
                    t = slog.start_timer()
                    raw_response = requests.get(raw_url, headers=headers, timeout=10)
                    slog.api_call("github_rest", "GET", "raw_content/readme",
                                  raw_response.status_code, slog.elapsed_ms(t),
                                  raw_response.status_code == 200)
                    if raw_response.status_code == 200:
                        readme_content = raw_response.text
                        # README 형식: # [티어] 문제명 - 1629
                        match = re.search(r'#\s*\[.*?\].*?-\s*(\d+)', readme_content)
                        if match:
                            result["문제_번호"] = match.group(1)

            return result

        except Exception as e:
            slog.api_error("github_rest", "GET",
                           f"/repos/{owner}/{repo}/commits/{sha[:7]}",
                           0, str(e))
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

        # 조직 레포는 소유자가 GITHUB_USERNAME(개인 계정)이 아니므로, 커밋에
        # 붙여둔 실제 소유자(repo_owner)를 우선 사용 (없으면 개인 계정으로 폴백)
        owner = commit.get("repo_owner") or os.getenv("GITHUB_USERNAME")
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
            t = slog.start_timer()
            response = requests.get(url, headers=headers, timeout=10)
            slog.api_call("github_rest", "GET",
                          f"/repos/{owner}/{repo}/commits/{sha[:7]}",
                          response.status_code, slog.elapsed_ms(t),
                          response.status_code == 200)

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
            slog.api_error("github_rest", "GET",
                           f"/repos/{owner}/{repo}/commits/{sha[:7]}",
                           0, str(e))
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
