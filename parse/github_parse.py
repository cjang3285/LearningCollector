#!/usr/bin/env python3
"""
GitHub 파서

수집된 GitHub 커밋 데이터를 파싱하여 구조화합니다.
변경된 코드에서 주석을 추출하고 분석합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import re
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass, asdict, field
import logging

from config.settings import get_log_file

# 백준 파서의 주석 추출기 재사용
from parse.baekjoon_parse import CommentExtractor, CodeComment

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('github_parse')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """파일 변경 정보"""
    filename: str
    status: str  # added, modified, removed, renamed
    additions: int
    deletions: int
    changes: int
    patch: str  # diff
    content: str = ""  # 전체 파일 내용 (있는 경우)
    language: str = ""  # 파일 확장자 기반 언어
    comments: List[CodeComment] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'filename': self.filename,
            'status': self.status,
            'additions': self.additions,
            'deletions': self.deletions,
            'changes': self.changes,
            'patch': self.patch,
            'content': self.content,
            'language': self.language,
            'comments': [c.to_dict() for c in self.comments]
        }


@dataclass
class CommitData:
    """파싱된 커밋 데이터"""
    repo: str
    sha: str
    message: str
    date: str
    url: str
    files: List[FileChange] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            'repo': self.repo,
            'sha': self.sha,
            'message': self.message,
            'date': self.date,
            'url': self.url,
            'files': [f.to_dict() for f in self.files],
            'stats': self.stats
        }


class GitHubParser:
    """GitHub 데이터 파서"""
    
    # 파일 확장자 → 언어 매핑
    LANGUAGE_MAP = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React',
        '.tsx': 'TypeScript React',
        '.cpp': 'C++',
        '.cc': 'C++',
        '.cxx': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.java': 'Java',
        '.rs': 'Rust',
        '.go': 'Go',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.sh': 'Shell',
        '.bash': 'Bash',
        '.zsh': 'Zsh',
    }
    
    @classmethod
    def detect_language(cls, filename: str) -> str:
        """파일 확장자로 언어 감지"""
        import os
        _, ext = os.path.splitext(filename)
        return cls.LANGUAGE_MAP.get(ext.lower(), 'Unknown')
    
    def parse_file_change(self, file_data: Dict) -> FileChange:
        """파일 변경사항 파싱"""
        language = self.detect_language(file_data['filename'])
        
        # 주석 추출 (content가 있는 경우)
        comments = []
        if file_data.get('content'):
            try:
                comments = CommentExtractor.extract(
                    file_data['content'],
                    language
                )
            except Exception as e:
                print(f"      ⚠️ 주석 추출 실패: {e}")
        
        return FileChange(
            filename=file_data['filename'],
            status=file_data['status'],
            additions=file_data['additions'],
            deletions=file_data['deletions'],
            changes=file_data['changes'],
            patch=file_data.get('patch', ''),
            content=file_data.get('content', ''),
            language=language,
            comments=comments
        )
    
    def parse_commits(self, commits: List[Dict]) -> List[CommitData]:
        """커밋 리스트를 CommitData로 변환"""
        parsed = []
        
        for commit in commits:
            # 파일 변경사항 파싱
            files = []
            if 'files' in commit:
                for file_data in commit['files']:
                    files.append(self.parse_file_change(file_data))
            
            parsed.append(CommitData(
                repo=commit['repo'],
                sha=commit['sha'],
                message=commit['message'],
                date=commit['date'],
                url=commit['url'],
                files=files,
                stats=commit.get('stats', {})
            ))
        
        return parsed
    
    def group_by_repo(self, commits: List[CommitData]) -> Dict[str, List[CommitData]]:
        """저장소별로 커밋 그룹화"""
        grouped = {}
        
        for commit in commits:
            if commit.repo not in grouped:
                grouped[commit.repo] = []
            grouped[commit.repo].append(commit)
        
        return grouped
    
    def group_by_language(self, commits: List[CommitData]) -> Dict[str, List[FileChange]]:
        """언어별로 파일 변경사항 그룹화"""
        grouped = {}
        
        for commit in commits:
            for file_change in commit.files:
                lang = file_change.language
                if lang not in grouped:
                    grouped[lang] = []
                grouped[lang].append(file_change)
        
        return grouped
    
    def get_summary(self, commits: List[CommitData]) -> Dict:
        """커밋 통계 요약"""
        if not commits:
            return {
                'total_commits': 0,
                'total_repos': 0,
                'total_additions': 0,
                'total_deletions': 0,
                'total_files': 0,
                'languages': {},
                'total_comments': 0
            }
        
        repos = set(c.repo for c in commits)
        total_additions = 0
        total_deletions = 0
        total_files = 0
        language_count = {}
        total_comments = 0
        
        for commit in commits:
            if commit.stats:
                total_additions += commit.stats.get('additions', 0)
                total_deletions += commit.stats.get('deletions', 0)
            
            for file_change in commit.files:
                total_files += 1
                lang = file_change.language
                if lang != 'Unknown':
                    language_count[lang] = language_count.get(lang, 0) + 1
                total_comments += len(file_change.comments)
        
        return {
            'total_commits': len(commits),
            'total_repos': len(repos),
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'total_files': total_files,
            'languages': language_count,
            'total_comments': total_comments,
            'repos': list(repos)
        }


if __name__ == '__main__':
    # 테스트
    sample_commits = [
        {
            'repo': 'test-repo',
            'sha': 'abc123',
            'message': 'Add feature',
            'date': '2025-12-26T10:00:00Z',
            'url': 'https://github.com/user/test-repo/commit/abc123',
            'files': [
                {
                    'filename': 'main.py',
                    'status': 'modified',
                    'additions': 10,
                    'deletions': 5,
                    'changes': 15,
                    'patch': '...',
                    'content': '# Main module\ndef main():\n    pass'
                }
            ],
            'stats': {'additions': 10, 'deletions': 5}
        }
    ]
    
    parser = GitHubParser()
    parsed = parser.parse_commits(sample_commits)
    summary = parser.get_summary(parsed)
    
    print(f"커밋: {summary['total_commits']}개")
    print(f"저장소: {summary['total_repos']}개")
    print(f"파일: {summary['total_files']}개")
    print(f"언어: {summary['languages']}")
    print(f"주석: {summary['total_comments']}개")

