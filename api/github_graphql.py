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

        # 1. 사용자의 모든 레포지토리 조회
        repositories = self._fetch_repositories(username)
        print(f"    → {len(repositories)}개 레포지토리 발견")

        # 2. 각 레포지토리의 모든 브랜치에서 커밋 수집
        for repo in repositories:
            repo_name = repo["name"]

            # 레포의 모든 브랜치 조회
            branches = self._fetch_branches(username, repo_name)

            # 각 브랜치에서 커밋 수집
            for branch in branches:
                commits = self._fetch_branch_commits(
                    username, repo_name, branch, start_date, end_date
                )
                all_commits.extend(commits)

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

        except Exception as e:
            print(f"    경고: {repo_name} 브랜치 조회 실패 - {str(e)}")

        return branches

    def _fetch_branch_commits(
        self,
        owner: str,
        repo_name: str,
        branch: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[dict]:
        """특정 브랜치의 커밋 조회"""
        query = """
        query($owner: String!, $name: String!, $branch: String!, $since: GitTimestamp!, $until: GitTimestamp!) {
          repository(owner: $owner, name: $name) {
            ref(qualifiedName: $branch) {
              target {
                ... on Commit {
                  history(first: 100, since: $since, until: $until) {
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

        variables = {
            "owner": owner,
            "name": repo_name,
            "branch": f"refs/heads/{branch}",
            "since": start_date.isoformat(),
            "until": end_date.isoformat()
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

            # 레포지토리 정보 추가
            for commit in commits:
                commit["repository"] = repo_name

            return commits

        except Exception as e:
            return []

    def _fetch_repo_commits(
        self,
        owner: str,
        repo_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[dict]:
        """특정 레포지토리의 커밋 조회"""
        query = """
        query($owner: String!, $name: String!, $since: GitTimestamp!, $until: GitTimestamp!) {
          repository(owner: $owner, name: $name) {
            defaultBranchRef {
              target {
                ... on Commit {
                  history(first: 100, since: $since, until: $until) {
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

        variables = {
            "owner": owner,
            "name": repo_name,
            "since": start_date.isoformat(),
            "until": end_date.isoformat()
        }

        try:
            response = self._execute_query(query, variables)

            # 응답 확인
            if "errors" in response:
                print(f"    경고: {repo_name} - {response['errors']}")
                return []

            repo_data = response.get("data", {}).get("repository")
            if not repo_data or not repo_data.get("defaultBranchRef"):
                return []

            commits = repo_data["defaultBranchRef"]["target"]["history"]["nodes"]

            # 레포지토리 정보 추가
            for commit in commits:
                commit["repository"] = repo_name

            return commits

        except Exception as e:
            print(f"    오류: {repo_name} 커밋 조회 실패 - {str(e)}")
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

    def fetch_commit_details(self, owner: str, repo: str, commit_sha: str) -> dict:
        """특정 커밋의 상세 정보 조회 (파일 변경 내용 포함)"""
        query = """
        query($owner: String!, $name: String!, $oid: GitObjectID!) {
          repository(owner: $owner, name: $name) {
            object(oid: $oid) {
              ... on Commit {
                oid
                message
                committedDate
                additions
                deletions
                changedFiles
                files(first: 10) {
                  nodes {
                    path
                    additions
                    deletions
                  }
                }
              }
            }
          }
        }
        """

        variables = {
            "owner": owner,
            "name": repo,
            "oid": commit_sha
        }

        response = self._execute_query(query, variables)
        return response["data"]["repository"]["object"]


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
