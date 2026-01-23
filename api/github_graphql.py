"""
GitHub GraphQL API 클라이언트
모든 레포, 모든 브랜치에서 커밋 수집
"""
import os
import requests
from datetime import datetime
from typing import List


class GitHubGraphQLClient:
    """GitHub GraphQL API 클라이언트"""

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def fetch_commits(
        self,
        username: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[dict]:
        """
        사용자의 모든 레포, 모든 브랜치에서 커밋 수집

        Args:
            username: GitHub 사용자명
            start_date: 수집 시작 날짜
            end_date: 수집 종료 날짜

        Returns:
            List[dict]: 커밋 리스트
        """
        all_commits = []

        # 디버그: 수집 기간 출력
        print(f"    📅 수집 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. 사용자의 모든 레포지토리 조회
        repositories = self._fetch_repositories(username)
        print(f"    → {len(repositories)}개 레포지토리 발견")

        # 2. 각 레포지토리의 모든 브랜치에서 커밋 수집
        for repo in repositories:
            repo_name = repo["name"]

            # 레포의 모든 브랜치 조회
            branches = self._fetch_branches(username, repo_name)
            print(f"    {repo_name}/")

            # 각 브랜치에서 커밋 수집
            for idx, branch in enumerate(branches):
                is_last_branch = (idx == len(branches) - 1)
                branch_prefix = "    └─ " if is_last_branch else "    ├─ "

                commits = self._fetch_branch_commits(
                    username, repo_name, branch, start_date, end_date
                )

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

    def _fetch_repositories(self, username: str) -> List[dict]:
        """사용자의 모든 레포지토리 조회"""
        query = """
        query($username: String!, $cursor: String) {
          user(login: $username) {
            repositories(first: 100, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                name
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
            variables = {"username": username, "cursor": cursor}
            response = self._execute_query(query, variables)

            repos_data = response["data"]["user"]["repositories"]
            repositories.extend(repos_data["nodes"])

            page_info = repos_data["pageInfo"]
            if not page_info["hasNextPage"]:
                break

            cursor = page_info["endCursor"]

        return repositories

    def _fetch_branches(self, owner: str, repo_name: str) -> List[str]:
        """레포지토리의 모든 브랜치 조회"""
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

    def _fetch_branch_commits(
        self,
        owner: str,
        repo_name: str,
        branch: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[dict]:
        """특정 브랜치의 커밋 조회 (since만 사용)"""
        query = """
        query($owner: String!, $name: String!, $branch: String!, $since: GitTimestamp!) {
          repository(owner: $owner, name: $name) {
            ref(qualifiedName: $branch) {
              target {
                ... on Commit {
                  history(first: 100, since: $since) {
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

        variables = {
            "owner": owner,
            "name": repo_name,
            "branch": f"refs/heads/{branch}",
            "since": since_param
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

        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"GitHub API 오류: HTTP {response.status_code}")

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
