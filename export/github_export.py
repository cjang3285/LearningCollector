#!/usr/bin/env python3
"""
GitHub Export - 당일 커밋 + diff + 코드 수집

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
    GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_API_BASE,
    get_log_file
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('github_export')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GitHubExporter:
    """GitHub 커밋 + 코드 수집"""
    
    def __init__(self, token: Optional[str] = None, username: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.username = username or GITHUB_USERNAME

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
        logger.info(f"GitHubExporter 초기화: {self.username}")
    
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
    
    def get_commits_by_date(
        self,
        repo_owner: str,
        repo_name: str,
        since: datetime,
        until: datetime
    ) -> List[Dict]:
        """
        특정 기간의 커밋 가져오기

        주의: author 필터를 사용하지 않음!
        - Claude가 primary author인 커밋도 포함하기 위해
        - 대신 Co-Authored-By나 committer에서 사용자 확인
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/commits"

        params = {
            # author 필터 제거! Claude 커밋도 가져오기 위해
            'since': since.isoformat(),
            'until': until.isoformat(),
            'per_page': 100
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            commits = response.json()

            # 사용자가 관련된 커밋만 필터링
            # 1. author가 사용자
            # 2. committer가 사용자
            # 3. Co-Authored-By에 사용자 포함
            filtered = []
            for commit in commits:
                commit_data = commit.get('commit', {})
                author = commit_data.get('author', {}).get('name', '')
                committer = commit_data.get('committer', {}).get('name', '')
                message = commit_data.get('message', '')

                # 사용자 관련 커밋인지 확인
                is_user_commit = (
                    self.username.lower() in author.lower() or
                    self.username.lower() in committer.lower() or
                    f'Co-Authored-By:' in message  # Co-author 체크는 나중에 상세히
                )

                if is_user_commit:
                    filtered.append(commit)

            return filtered

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
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
    
    def get_file_content(
        self,
        repo_owner: str,
        repo_name: str,
        file_path: str,
        ref: str = 'main'
    ) -> str:
        """파일 내용 가져오기"""
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/contents/{file_path}"
        
        params = {'ref': ref}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Base64 디코딩
            import base64
            content = base64.b64decode(data['content']).decode('utf-8')
            return content
        except Exception as e:
            logger.warning(f"파일 읽기 실패: {e}")
            return ""
    
    def export(self, target_date=None) -> List[Dict]:
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

        all_commits = []

        for repo in repos:
            repo_name = repo['name']
            repo_owner = repo['owner']['login']

            commits = self.get_commits_by_date(
                repo_owner,
                repo_name,
                today_start,
                today_end
            )

            if commits:
                logger.info(f"[OK] {repo_name}: {len(commits)}개 커밋")
                
                for commit in commits:
                    # 기본 정보
                    commit_data = {
                        'repo': repo_name,
                        'repo_owner': repo_owner,  # 저장소 소유자 추가
                        'sha': commit['sha'],
                        'message': commit['commit']['message'],
                        'date': commit['commit']['author']['date'],
                        'url': commit['html_url']
                    }
                    
                    # 상세 정보 가져오기
                    try:
                        detail = self.get_commit_detail(repo_owner, repo_name, commit['sha'])
                        
                        # 파일 변경사항
                        files = detail.get('files', [])
                        commit_data['files'] = []
                        
                        for file in files:
                            file_info = {
                                'filename': file['filename'],
                                'status': file['status'],  # added, modified, removed, renamed
                                'additions': file['additions'],
                                'deletions': file['deletions'],
                                'changes': file['changes'],
                                'patch': file.get('patch', '')  # diff
                            }
                            
                            # 추가/수정된 파일의 전체 내용 가져오기
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
                        
                        # 통계
                        commit_data['stats'] = detail.get('stats', {})

                        logger.debug(f"  파일 {len(files)}개 변경 "
                              f"(+{detail['stats']['additions']}/-{detail['stats']['deletions']})")

                    except Exception as e:
                        logger.warning(f"  상세 정보 수집 실패: {e}")
                    
                    all_commits.append(commit_data)

        logger.info(f"[OK] 총 {len(all_commits)}개 커밋 수집 완료")
        return all_commits


if __name__ == '__main__':
    exporter = GitHubExporter()
    commits = exporter.export()
    
    for commit in commits:
        print(f"\n[{commit['repo']}] {commit['message']}")
        if 'files' in commit:
            for file in commit['files']:
                print(f"  {file['status']}: {file['filename']} "
                      f"(+{file['additions']}/-{file['deletions']})")
