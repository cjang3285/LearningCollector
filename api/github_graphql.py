"""
GitHub GraphQL API 클라이언트
모든 레포, 모든 브랜치에서 커밋 수집
"""
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List
from core import structured_logger as slog

# 레포별 GraphQL 조회 병렬 실행 수 (서로 독립적인 요청이라 동시 실행 가능,
# GitHub API에 과도한 동시 요청을 보내지 않도록 적당히 제한)
MAX_CONCURRENT_REPO_FETCHES = 5

# Claude Code로 커밋할 때 찍히는 고정 작성자 이메일 (실질적으로 본인 작업으로 취급)
CLAUDE_CODE_EMAIL = "noreply@anthropic.com"


class GitHubGraphQLClient:
    """GitHub GraphQL API 클라이언트"""

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_own_author_filter(self) -> dict:
        """
        GraphQL history(author: ...) 필터에 넘길 조건.

        id로 본인 GitHub 계정을 지정하면, 그 계정에 연결된(인증된) 어떤 이메일로
        커밋했든 전부 매칭된다 (예: 개인 이메일/학교 이메일을 섞어 썼어도 놓치지
        않음). emails에는 계정에 연결되지 않은 이메일로 커밋한 경우를 위해 본인
        이메일을 한 번 더 넣고, Claude Code로 커밋할 때 찍히는 고정 이메일도
        추가한다 (id와 emails는 OR로 매칭됨). 이렇게 해두면 팀원 커밋은 GitHub
        서버 단에서부터 응답에 실리지 않는다.
        """
        viewer = self._fetch_viewer_id_and_email()
        emails = [e for e in (viewer.get("email"), CLAUDE_CODE_EMAIL) if e]
        return {"id": viewer.get("id"), "emails": emails}

    def _fetch_viewer_id_and_email(self) -> dict:
        """토큰 소유자(본인) 계정의 node ID와 이메일 조회"""
        query = """
        query {
          viewer {
            id
            email
          }
        }
        """
        try:
            response = self._execute_query(query, {})
            return response.get("data", {}).get("viewer", {}) or {}
        except Exception:
            return {}

    def fetch_commits(
        self,
        username: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[dict]:
        """
        사용자의 모든 레포, 모든 브랜치에서 커밋 수집

        레포마다 "이번 기간에 푸시된 적 있는지(pushedAt)"로 먼저 걸러내고,
        살아있는 레포에 대해서만 브랜치+커밋을 조회한다 (그마저도 브랜치별로
        따로 요청하지 않고 레포당 요청 1번으로 묶음). 레포별 조회는 서로
        독립적이므로 병렬로 실행한다. 커밋 작성자가 본인(또는 Claude Code)이
        아니면 GraphQL author 필터로 서버 단에서부터 제외한다.

        Args:
            username: GitHub 사용자명
            start_date: 수집 시작 날짜
            end_date: 수집 종료 날짜

        Returns:
            List[dict]: 커밋 리스트
        """
        all_commits = []
        author_filter = self.get_own_author_filter()

        # 디버그: 수집 기간 출력
        print(f"    📅 수집 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. 사용자의 모든 레포지토리 조회 (pushedAt 포함)
        repositories = self.fetch_repositories(username)
        print(f"    → {len(repositories)}개 레포지토리 발견")

        # 2. 이번 수집 기간 이후로 푸시된 적 없는 레포는 브랜치/커밋 조회 자체를 스킵
        active_repos = []
        for repo in repositories:
            pushed_at = self.parse_github_timestamp(repo.get("pushedAt"))
            if pushed_at is not None and pushed_at < start_date:
                print(f"    {repo['name']}/ (수집 기간 내 변경 없음, 스킵)")
                continue
            active_repos.append(repo)

        # 3. 살아있는 레포만 병렬로 (브랜치+커밋을 레포당 요청 1번에) 조회
        results = {}
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REPO_FETCHES) as executor:
            future_to_repo = {
                executor.submit(
                    self.fetch_repo_branch_commits,
                    repo["owner"]["login"], repo["name"], start_date, end_date, author_filter
                ): repo["name"]
                for repo in active_repos
            }
            for future in as_completed(future_to_repo):
                repo_name = future_to_repo[future]
                try:
                    results[repo_name] = future.result()
                except Exception:
                    results[repo_name] = {}

        # 4. 레포 원래 순서대로 출력 + 결과 취합
        for repo in active_repos:
            repo_name = repo["name"]
            branch_commits = results.get(repo_name, {})
            print(f"    {repo_name}/")

            branch_names = list(branch_commits.keys())
            for idx, branch in enumerate(branch_names):
                commits = branch_commits[branch]
                is_last_branch = (idx == len(branch_names) - 1)
                branch_prefix = "    └─ " if is_last_branch else "    ├─ "

                if commits:
                    print(f"{branch_prefix}{branch}: {len(commits)}개")
                    # 첫 3개 커밋 메시지 출력
                    commit_prefix = "       " if is_last_branch else "    │  "
                    for i, commit in enumerate(commits[:3]):
                        message = commit["message"].split("\n")[0][:60]  # 첫 줄, 60자까지
                        sha_short = commit["oid"][:7]
                        print(f"{commit_prefix}  - {sha_short}: {message}")
                    if len(commits) > 3:
                        print(f"{commit_prefix}  ... ({len(commits) - 3}개 더)")
                else:
                    print(f"{branch_prefix}{branch}: 0개")

                all_commits.extend(commits)

        print(f"    ✅ 총 수집: {len(all_commits)}개 커밋")
        return all_commits

    def fetch_repositories(self, username: str) -> List[dict]:
        """
        개인 레포뿐 아니라 소속된 조직(organization)의 레포까지 포함해서 조회.

        `user(login: $username)`으로 조회하면 개인 소유 레포만 나오고 조직
        레포는 아예 빠지기 때문에, 토큰 소유자 기준(`viewer`) + affiliations로
        조회해서 "내가 커밋/PR을 올리는 조직 레포"도 잡히게 함.
        """
        query = """
        query($cursor: String) {
          viewer {
            repositories(
              first: 100, after: $cursor,
              ownerAffiliations: [OWNER, ORGANIZATION_MEMBER, COLLABORATOR]
            ) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                name
                pushedAt
                owner {
                  login
                }
              }
            }
          }
        }
        """

        repositories = []
        cursor = None

        while True:
            variables = {"cursor": cursor}
            response = self._execute_query(query, variables)

            repos_data = response["data"]["viewer"]["repositories"]
            repositories.extend(repos_data["nodes"])

            page_info = repos_data["pageInfo"]
            if not page_info["hasNextPage"]:
                break

            cursor = page_info["endCursor"]

        return repositories

    def parse_github_timestamp(self, timestamp: str):
        """GitHub GraphQL의 ISO 8601 타임스탬프(...Z)를 naive UTC datetime으로 변환"""
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            return None

    def fetch_repo_branch_commits(
        self,
        owner: str,
        repo_name: str,
        start_date: datetime,
        end_date: datetime,
        author_filter: dict = None
    ) -> dict:
        """
        레포의 모든 브랜치와 각 브랜치의 커밋을 요청 1번(페이지네이션 시 여러 번)으로 조회.
        기존에는 브랜치 목록 조회 1번 + 브랜치별 커밋 조회 N번이 필요했지만,
        GraphQL의 중첩 조회(refs → target → history)를 이용해 하나로 합침.

        author_filter({"id", "emails"})가 주어지면 history의 author 필터로
        넘겨서, 거기 해당 안 되는 작성자(팀원)의 커밋은 GitHub 서버 단에서부터
        제외하고 받아온다 (응답 자체에 안 실려 옴 - 네트워크/쿼터 절약).

        Returns:
            dict: {브랜치명: [커밋, ...]}
        """
        query = """
        query($owner: String!, $name: String!, $since: GitTimestamp!, $cursor: String, $authorId: ID, $authorEmails: [String!]) {
          repository(owner: $owner, name: $name) {
            refs(refPrefix: "refs/heads/", first: 100, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                name
                target {
                  ... on Commit {
                    history(first: 100, since: $since, author: {id: $authorId, emails: $authorEmails}) {
                      nodes {
                        oid
                        message
                        committedDate
                        additions
                        deletions
                        changedFiles
                        author {
                          name
                          email
                          user {
                            login
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        since_param = start_date.replace(microsecond=0).isoformat() + "Z"
        branch_commits = {}
        cursor = None
        author_filter = author_filter or {}

        try:
            while True:
                variables = {
                    "owner": owner, "name": repo_name,
                    "since": since_param, "cursor": cursor,
                    "authorId": author_filter.get("id"),
                    "authorEmails": author_filter.get("emails") or None
                }
                response = self._execute_query(query, variables)

                if "errors" in response:
                    break

                repo_data = response.get("data", {}).get("repository")
                if not repo_data:
                    break

                refs_data = repo_data["refs"]
                for node in refs_data["nodes"]:
                    branch_name = node["name"]
                    target = node.get("target") or {}
                    history = target.get("history")

                    if not history:
                        branch_commits[branch_name] = []
                        continue

                    filtered_commits = []
                    for commit in history["nodes"]:
                        commit_date_str = commit["committedDate"].replace("Z", "+00:00")
                        commit_date_naive = datetime.fromisoformat(commit_date_str).replace(tzinfo=None)

                        if commit_date_naive <= end_date:
                            commit["repository"] = repo_name
                            commit["repo_owner"] = owner
                            commit["branch"] = branch_name
                            filtered_commits.append(commit)

                    branch_commits[branch_name] = filtered_commits

                page_info = refs_data["pageInfo"]
                if not page_info["hasNextPage"]:
                    break

                cursor = page_info["endCursor"]

        except Exception:
            pass

        return branch_commits

    def fetch_pull_requests(
        self,
        owner: str,
        repo_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[dict]:
        """
        레포의 PR 목록 조회 (최근 업데이트 순으로 페이지네이션하다가, 이번
        수집 기간보다 오래된 PR이 나오면 그 이후는 조회할 필요가 없으므로 중단).

        Returns:
            List[dict]: PR 리스트 (병합되었거나 닫힌 PR만 - 아직 열려있는
                        PR은 나중에 커밋이 더 붙을 수 있으므로 여기서는 제외)
        """
        query = """
        query($owner: String!, $name: String!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            pullRequests(
              first: 30, after: $cursor,
              orderBy: {field: UPDATED_AT, direction: DESC}
            ) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                id
                number
                title
                body
                state
                url
                createdAt
                updatedAt
                mergedAt
                additions
                deletions
                changedFiles
                headRefName
                baseRefName
                author {
                  login
                }
                commits(first: 30) {
                  totalCount
                  nodes {
                    commit {
                      oid
                      message
                    }
                  }
                }
              }
            }
          }
        }
        """

        prs = []
        cursor = None

        try:
            while True:
                variables = {"owner": owner, "name": repo_name, "cursor": cursor}
                response = self._execute_query(query, variables)

                if "errors" in response:
                    break

                repo_data = response.get("data", {}).get("repository")
                if not repo_data:
                    break

                pr_data = repo_data["pullRequests"]
                stop_paging = False

                for node in pr_data["nodes"]:
                    updated_at = self.parse_github_timestamp(node.get("updatedAt"))

                    # UPDATED_AT DESC로 정렬했으므로, 수집 기간보다 오래 전에
                    # 업데이트된 PR이 나오면 그 이후는 전부 더 오래된 것 -> 중단
                    if updated_at is not None and updated_at < start_date:
                        stop_paging = True
                        break

                    # 아직 열려있는 PR은 나중에 커밋/설명이 더 바뀔 수 있으므로 제외
                    if node.get("state") == "OPEN":
                        continue

                    node["repository"] = repo_name
                    node["repo_owner"] = owner
                    prs.append(node)

                if stop_paging:
                    break

                page_info = pr_data["pageInfo"]
                if not page_info["hasNextPage"]:
                    break

                cursor = page_info["endCursor"]

        except Exception:
            pass

        return prs

    def fetch_branches(self, owner: str, repo_name: str) -> List[str]:
        """레포지토리의 모든 브랜치 조회 (public)"""
        query = """
        query($owner: String!, $name: String!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            refs(refPrefix: "refs/heads/", first: 100, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                name
              }
            }
          }
        }
        """

        branches = []
        cursor = None

        try:
            while True:
                variables = {"owner": owner, "name": repo_name, "cursor": cursor}
                response = self._execute_query(query, variables)

                repo_data = response.get("data", {}).get("repository")
                if not repo_data:
                    break

                refs_data = repo_data["refs"]
                branches.extend([node["name"] for node in refs_data["nodes"]])

                page_info = refs_data["pageInfo"]
                if not page_info["hasNextPage"]:
                    break

                cursor = page_info["endCursor"]

        except Exception:
            pass

        return branches

    def fetch_branch_commits(
        self,
        owner: str,
        repo_name: str,
        branch: str,
        start_date: datetime,
        end_date: datetime,
        author_filter: dict = None
    ) -> List[dict]:
        """
        특정 브랜치의 커밋 조회 (public).
        author_filter({"id", "emails"})가 주어지면 거기 해당 안 되는 작성자의
        커밋은 서버 단에서부터 제외하고 받아온다.
        """
        query = """
        query($owner: String!, $name: String!, $branch: String!, $since: GitTimestamp!, $authorId: ID, $authorEmails: [String!]) {
          repository(owner: $owner, name: $name) {
            ref(qualifiedName: $branch) {
              target {
                ... on Commit {
                  history(first: 100, since: $since, author: {id: $authorId, emails: $authorEmails}) {
                    nodes {
                      oid
                      message
                      committedDate
                      additions
                      deletions
                      changedFiles
                      author {
                        name
                        email
                        user {
                          login
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        # ISO 포맷 (마이크로초 제거)
        since_param = start_date.replace(microsecond=0).isoformat() + "Z"
        author_filter = author_filter or {}

        variables = {
            "owner": owner,
            "name": repo_name,
            "branch": f"refs/heads/{branch}",
            "since": since_param,
            "authorId": author_filter.get("id"),
            "authorEmails": author_filter.get("emails") or None
        }

        try:
            response = self._execute_query(query, variables)

            # 응답 확인
            if "errors" in response:
                return []

            repo_data = response.get("data", {}).get("repository")
            if not repo_data or not repo_data.get("ref"):
                return []

            commits = repo_data["ref"]["target"]["history"]["nodes"]

            # end_date 이후 커밋 필터링 (클라이언트 사이드)
            filtered_commits = []
            for commit in commits:
                commit_date_str = commit["committedDate"].replace("Z", "+00:00")
                commit_date = datetime.fromisoformat(commit_date_str)

                # 타임존 제거 (naive datetime으로 변환)
                commit_date_naive = commit_date.replace(tzinfo=None)

                if commit_date_naive <= end_date:
                    commit["repository"] = repo_name
                    commit["repo_owner"] = owner
                    commit["branch"] = branch  # 브랜치 정보 추가
                    filtered_commits.append(commit)

            return filtered_commits

        except Exception:
            return []

    def _execute_query(self, query: str, variables: dict) -> dict:
        """GraphQL 쿼리 실행"""
        payload = {
            "query": query,
            "variables": variables
        }

        # 쿼리 타입 추출 (query($...) { user / repository })
        query_type = "unknown"
        for keyword in ["repositories", "refs", "history"]:
            if keyword in query:
                query_type = keyword
                break

        t = slog.start_timer()
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload,
            timeout=30
        )
        duration = slog.elapsed_ms(t)

        if response.status_code != 200:
            slog.api_call("github_graphql", "POST", query_type,
                          response.status_code, duration, False)
            raise Exception(f"GitHub API 오류: HTTP {response.status_code}")

        slog.api_call("github_graphql", "POST", query_type,
                      response.status_code, duration, True)
        return response.json()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    from datetime import timedelta

    client = GitHubGraphQLClient()
    end = datetime.now()
    start = end - timedelta(days=7)

    username = os.getenv("GITHUB_USERNAME")
    commits = client.fetch_commits(username, start, end)
    print(f"\n총 {len(commits)}개 커밋 수집 완료")
