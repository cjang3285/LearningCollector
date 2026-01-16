"""pytest 설정 및 공통 픽스처"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List
import pytest
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 테스트용 환경변수 설정
os.environ['GITHUB_USERNAME'] = 'testuser'
os.environ['GITHUB_TOKEN'] = 'test_github_token_12345'
os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key_12345'
os.environ['BLOG_API_URL'] = 'https://blog.example.com/api/posts'
os.environ['BLOG_API_TOKEN'] = 'test_blog_token_12345'
os.environ['BLOG_MOCK_MODE'] = 'true'

# 픽스처 디렉토리
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


# ============================================
# 공통 픽스처
# ============================================

@pytest.fixture
def test_date():
    """테스트용 날짜"""
    return date(2024, 1, 15)


@pytest.fixture
def fixtures_dir():
    """픽스처 디렉토리 경로"""
    return FIXTURES_DIR


@pytest.fixture
def temp_data_dir(tmp_path):
    """임시 데이터 디렉토리"""
    data_dir = tmp_path / 'data'
    collection_log_dir = data_dir / 'collection_log'
    draft_dir = data_dir / 'draft'

    collection_log_dir.mkdir(parents=True)
    draft_dir.mkdir(parents=True)

    return {
        'root': data_dir,
        'collection_log': collection_log_dir,
        'draft': draft_dir
    }


# ============================================
# AI Chat 픽스처
# ============================================

@pytest.fixture
def claude_markdown():
    """Claude 마크다운 샘플 파일"""
    return FIXTURES_DIR / 'ai_chat' / 'claude_sample.md'


@pytest.fixture
def chatgpt_markdown():
    """ChatGPT 마크다운 샘플 파일"""
    return FIXTURES_DIR / 'ai_chat' / 'chatgpt_sample.md'


@pytest.fixture
def gemini_markdown():
    """Gemini 마크다운 샘플 파일"""
    return FIXTURES_DIR / 'ai_chat' / 'gemini_sample.md'


@pytest.fixture
def claude_markdown_content(claude_markdown):
    """Claude 마크다운 내용"""
    return claude_markdown.read_text(encoding='utf-8')


@pytest.fixture
def chatgpt_markdown_content(chatgpt_markdown):
    """ChatGPT 마크다운 내용"""
    return chatgpt_markdown.read_text(encoding='utf-8')


@pytest.fixture
def gemini_markdown_content(gemini_markdown):
    """Gemini 마크다운 내용"""
    return gemini_markdown.read_text(encoding='utf-8')


# ============================================
# GitHub 픽스처
# ============================================

@pytest.fixture
def github_commits_response():
    """GitHub API 커밋 응답 샘플"""
    fixture_path = FIXTURES_DIR / 'github' / 'commits_response.json'
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def mock_github_api(github_commits_response):
    """Mock GitHub API 응답"""
    mock = Mock()
    mock.get_commits.return_value = github_commits_response
    return mock


# ============================================
# Baekjoon 픽스처
# ============================================

@pytest.fixture
def baekjoon_files():
    """Baekjoon 샘플 파일 경로"""
    return {
        '1000': FIXTURES_DIR / 'baekjoon' / '1000.py',
        '1260': FIXTURES_DIR / 'baekjoon' / '1260.py'
    }


@pytest.fixture
def baekjoon_repo_dir(tmp_path):
    """임시 Baekjoon 저장소 디렉토리"""
    repo_dir = tmp_path / 'BaekjoonHub'
    repo_dir.mkdir()

    # 샘플 파일 복사
    problem_1000 = repo_dir / '백준' / 'Bronze' / '1000.py'
    problem_1260 = repo_dir / '백준' / 'Silver' / '1260.py'

    problem_1000.parent.mkdir(parents=True)
    problem_1260.parent.mkdir(parents=True)

    # 내용 복사
    problem_1000.write_text((FIXTURES_DIR / 'baekjoon' / '1000.py').read_text())
    problem_1260.write_text((FIXTURES_DIR / 'baekjoon' / '1260.py').read_text())

    return repo_dir


# ============================================
# API Mock 픽스처
# ============================================

@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API 응답"""
    return {
        'id': 'msg_01ABC123',
        'type': 'message',
        'role': 'assistant',
        'content': [
            {
                'type': 'text',
                'text': '''# 2024-01-15 학습 정리

## 주요 학습 내용

### 1. 데이터베이스 스키마 설계
- **핵심 논점**: UUID vs Auto-incrementing Integer 선택
- **의사결정**: 블로그 플랫폼의 경우 auto-incrementing integer 선택
  - 이유: 더 나은 성능, 간단한 디버깅, 자연스러운 순서
  - 트레이드오프: 보안성은 낮지만 블로그에서는 문제되지 않음

### 2. React Hooks 최적화
- **핵심 논점**: useEffect 의존성 배열 관리의 중요성
- **학습 내용**:
  - 빠진 의존성은 버그의 원천
  - 불필요한 재렌더링 방지를 위한 useMemo 활용
  - 클린업 함수의 중요성 (메모리 누수 방지)

## 기술적 통찰

1. **데이터베이스 설계**: 비즈니스 요구사항에 맞는 ID 전략 선택
2. **React 성능**: 의존성 관리가 성능의 핵심
3. **그래프 알고리즘**: DFS/BFS 구현 이해'''
            }
        ],
        'model': 'claude-sonnet-4-20250514',
        'stop_reason': 'end_turn',
        'usage': {
            'input_tokens': 1500,
            'output_tokens': 500
        }
    }


@pytest.fixture
def mock_blog_api_response():
    """Mock Blog API 응답"""
    return {
        'success': True,
        'post_id': 'post_12345',
        'url': 'https://blog.example.com/posts/post_12345',
        'status': 'draft',
        'created_at': '2024-01-15T10:00:00Z'
    }


# ============================================
# Collection 데이터 픽스처
# ============================================

@pytest.fixture
def sample_collection_data(test_date):
    """샘플 수집 데이터"""
    return {
        'date': test_date.isoformat(),
        'github': {
            'commits': [
                {
                    'sha': 'abc123',
                    'message': 'Add authentication',
                    'author': 'testuser',
                    'date': '2024-01-15T10:30:00Z',
                    'additions': 150,
                    'deletions': 30,
                    'total_changes': 180,
                    'files': ['src/auth/jwt.js', 'src/middleware/auth.js']
                }
            ],
            'total_commits': 1,
            'total_additions': 150,
            'total_deletions': 30
        },
        'ai_chats': {
            'conversations': [
                {
                    'filename': 'claude_sample.md',
                    'provider': 'claude',
                    'timestamp': '2024-01-15T09:00:00',
                    'exchange_count': 4,
                    'total_length': 2500
                }
            ],
            'total_conversations': 1,
            'total_exchanges': 4
        },
        'baekjoon': {
            'problems': [
                {
                    'problem_number': '1000',
                    'filename': '1000.py',
                    'language': 'python',
                    'lines': 5
                }
            ],
            'total_problems': 1
        }
    }


@pytest.fixture
def mock_requests():
    """Mock requests 모듈"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        yield {
            'get': mock_get,
            'post': mock_post
        }
