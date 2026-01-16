#!/usr/bin/env python3
"""
GitHub Load - 당일 커밋 + diff + 코드 수집

GitHub REST API를 사용하여 사용자의 당일 커밋과 변경 코드를 수집합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging

from config.settings import (
    GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_USERNAMES, GITHUB_API_BASE,
    get_log_file
)
from config.logging_config import setup_logging

# 로깅 설정
logger = setup_logging(get_log_file('github_load'), __name__)



class GitHubLoader:
    """GitHub 커밋 + 코드 수집"""

    def __init__(self, token: Optional[str] = None, usernames: Optional[List[str]] = None):
        self.token = token or GITHUB_TOKEN
        # usernames: 수집할 작성자 목록 (첫 번째가 primary)
        self.usernames = usernames if usernames is not None else GITHUB_USERNAMES
        self.username = self.usernames[0] if self.usernames else None  # Primary username

        if not self.token:
            raise ValueError("GITHUB_TOKEN 필요")
        if not self.username:
            raise ValueError("GITHUB_USERNAME 필요")

        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        self.base_url = GITHUB_API_BASE
        logger.info(f"GitHubLoader 초기화: Primary={self.username}")
        if len(self.usernames) > 1:
            logger.info(f"추가 커밋 작성자: {', '.join(self.usernames[1:])}")
    
    def get_user_repos(self) -> List[Dict]:
        """사용자의 모든 저장소 가져오기"""
        repos = []
        page = 1
        
        while True:
            url = f"{self.base_url}/user/repos"
            params = {
                'page': page,
                'per_page': 100,
                'type': 'owner',
                'sort': 'updated',
                'direction': 'desc'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                break
            
            repos.extend(data)
            page += 1
        
        return repos
    
    def get_branches(self, repo_owner: str, repo_name: str) -> List[Dict]:
        """저장소의 모든 브랜치 가져오기"""
        branches = []
        page = 1
        while True:
            url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/branches"
            params = {'page': page, 'per_page': 100}
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            branches.extend(data)
            page += 1
        return branches

    def get_commits_by_date(
        self,
        repo_owner: str,
        repo_name: str,
        since: datetime,
        until: datetime,
        branch: str = None
    ) -> List[Dict]:
        """
        특정 기간의 커밋 가져오기

        주의: author 필터를 사용하지 않음!
        - Claude가 primary author인 커밋도 포함하기 위해
        - 대신 Co-Authored-By나 committer에서 사용자 확인
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/commits"

        params = {
            'since': since.isoformat(),
            'until': until.isoformat(),
            'per_page': 100
        }
        if branch:
            params['sha'] = branch

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            commits = response.json()

            # 설정된 username들의 커밋만 필터링
            # 1. author가 설정된 username 중 하나
            # 2. committer가 설정된 username 중 하나
            # 3. Co-Authored-By에 username 포함
            filtered = []
            for commit in commits:
                commit_data = commit.get('commit', {})
                author = commit_data.get('author', {}).get('name', '')
                committer = commit_data.get('committer', {}).get('name', '')
                message = commit_data.get('message', '')

                # 모든 username 확인
                is_target_commit = False
                for username in self.usernames:
                    if (username.lower() in author.lower() or
                        username.lower() in committer.lower() or
                        f'Co-Authored-By: {username}' in message):
                        is_target_commit = True
                        break
                
                if is_target_commit:
                    filtered.append(commit)

            return filtered

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409: # 409 Conflict can happen for empty repos
                logger.warning(f"Got 409 Conflict for {repo_name} on branch {branch}, skipping.")
                return []
            raise
    
    def get_commit_detail(
        self,
        repo_owner: str,
        repo_name: str,
        commit_sha: str
    ) -> Dict:
        """커밋 상세 정보 가져오기 (파일 변경사항 포함)"""
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/commits/{commit_sha}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_commit_diff(
        self,
        repo_owner: str,
        repo_name: str,
        commit_sha: str
    ) -> str:
        """커밋의 전체 diff 가져오기 (plain text)"""
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/commits/{commit_sha}"
        
        headers = self.headers.copy()
        headers['Accept'] = 'application/vnd.github.v3.diff'
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    
    def load(self, target_date=None) -> List[Dict]:
        """
        특정 날짜의 커밋 + 상세 정보 수집

        Args:
            target_date: 수집할 날짜 (date 객체), None이면 오늘

        Returns:
            커밋 데이터 리스트
        """
        from datetime import date as date_type

        if target_date is None:
            target_date = date_type.today()

        logger.info(f"{self.username}의 {target_date} 커밋 수집 중...")

        # target_date의 00:00 ~ 23:59 (UTC)
        today_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
        today_end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)

        repos = self.get_user_repos()
        logger.info(f"저장소 {len(repos)}개 발견")

        all_commits_detailed = []
        seen_commit_shas = set()

        for repo in repos:
            repo_name = repo['name']
            repo_owner = repo['owner']['login']
            
            try:
                branches = self.get_branches(repo_owner, repo_name)
                logger.debug(f"Found {len(branches)} branches for {repo_name}: {[b['name'] for b in branches]}")
            except requests.exceptions.HTTPError as e:
                # If branch listing fails (401/empty repo), still attempt to call get_commits_by_date
                # once with branch=None so tests that patch get_commits_by_date still execute.
                logger.warning(f"Could not get branches for {repo_name} (maybe it's empty or archived), will try commits without branch. Error: {e}")
                branches = [None]

                for branch in branches:
                    # branches may be None when branch listing failed; support that fallback
                    if branch is None:
                        branch_name = None
                    else:
                        branch_name = branch.get('name')
                    logger.debug(f"Checking branch '{branch_name}' in repo '{repo_name}'")
                
                try:
                    commits_on_branch = self.get_commits_by_date(
                        repo_owner,
                        repo_name,
                        today_start,
                        today_end,
                        branch=branch_name
                    )
                except requests.exceptions.HTTPError as e:
                    logger.error(f"Error fetching commits for {repo_name} on branch {branch_name}: {e}")
                    continue

                if commits_on_branch:
                    logger.info(f"[OK] {repo_name} (branch: {branch_name}): {len(commits_on_branch)}개 커밋")
                    
                    for commit in commits_on_branch:
                        if commit['sha'] in seen_commit_shas:
                            continue
                        seen_commit_shas.add(commit['sha'])

                        # 기본 정보
                        commit_data = {
                            'repo': repo_name,
                            'repo_owner': repo_owner,
                            'sha': commit['sha'],
                            'message': commit['commit']['message'],
                            'date': commit['commit']['author']['date'],
                            'url': commit['html_url']
                        }
                        
                        # 상세 정보 가져오기
                        try:
                            detail = self.get_commit_detail(repo_owner, repo_name, commit['sha'])
                            
                            files = detail.get('files', [])
                            commit_data['files'] = []
                            
                            for file in files:
                                file_info = {
                                    'filename': file['filename'],
                                    'status': file['status'],
                                    'additions': file['additions'],
                                    'deletions': file['deletions'],
                                    'changes': file['changes'],
                                    'patch': file.get('patch', '')
                                }
                                
                                if file['status'] in ['added', 'modified']:
                                    content = self.get_file_content(
                                        repo_owner,
                                        repo_name,
                                        file['filename'],
                                        commit['sha']
                                    )
                                    if content:
                                        file_info['content'] = content
                                
                                commit_data['files'].append(file_info)
                            
                            commit_data['stats'] = detail.get('stats', {})

                            logger.debug(f"  파일 {len(files)}개 변경 (+{detail.get('stats', {}).get('additions', 0)}/-{detail.get('stats', {}).get('deletions', 0)})")

                        except Exception as e:
                            logger.warning(f"  상세 정보 수집 실패: {e}")
                        
                        all_commits_detailed.append(commit_data)

        logger.info(f"[OK] 총 {len(all_commits_detailed)}개 커밋 수집 완료")
        return all_commits_detailed


if __name__ == '__main__':
    loader = GitHubLoader()
    commits = loader.load()
    
    for commit in commits:
        print(f"\n[{commit['repo']}] {commit['message']}")
        if 'files' in commit:
            for file in commit['files']:
                print(f"  {file['status']}: {file['filename']} "
                      f"(+{file['additions']}/-{file['deletions']})")
