"""통합 테스트"""

import pytest
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch, Mock
import main
import generate_post_draft
import publish_to_blog


class TestDataCollection:
    """데이터 수집 통합 테스트"""

    def test_save_and_load_data(self, temp_data_dir, sample_collection_data, test_date):
        """데이터 저장 및 로드"""
        collection_log_dir = temp_data_dir['collection_log']

        # 데이터 저장
        with patch.object(main, 'COLLECTION_LOG_DIR', collection_log_dir):
            saved_path = main.save_daily_data(test_date, sample_collection_data)
            assert saved_path.exists()

        # 데이터 로드
        with patch.object(generate_post_draft, 'COLLECTION_LOG_DIR', collection_log_dir):
            loaded_data = generate_post_draft.load_daily_data(test_date)
            assert loaded_data['date'] == test_date.isoformat()


class TestDraftGeneration:
    """블로그 초안 생성 통합 테스트"""

    @patch('generate_post_draft.anthropic.Anthropic')
    def test_generate_and_save_draft(
        self,
        mock_anthropic_class,
        temp_data_dir,
        sample_collection_data,
        mock_anthropic_response,
        test_date
    ):
        """초안 생성 및 저장"""
        collection_log_dir = temp_data_dir['collection_log']
        draft_dir = temp_data_dir['draft']

        # 수집 데이터 저장
        data_file = collection_log_dir / f'collect_result_{test_date}.json'
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(sample_collection_data, f)

        # Claude API Mock
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock(text=mock_anthropic_response['content'][0]['text'])]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_class.return_value = mock_client

        # 초안 생성 및 저장
        with patch.object(generate_post_draft, 'COLLECTION_LOG_DIR', collection_log_dir), \
             patch.object(generate_post_draft, 'DRAFT_DIR', draft_dir):

            data = generate_post_draft.load_daily_data(test_date)
            draft = generate_post_draft.generate_with_claude(data)
            saved_path = generate_post_draft.save_draft(draft, test_date)

            assert saved_path.exists()
            assert saved_path.name == f'post_draft_{test_date}.md'


class TestBlogPublishing:
    """블로그 게시 통합 테스트"""

    def test_load_and_publish_mock(self, temp_data_dir, test_date):
        """초안 로드 및 Mock 모드 게시"""
        draft_dir = temp_data_dir['draft']

        # 초안 파일 생성
        draft_content = f'''# {test_date} 학습 정리

테스트 초안입니다.
'''
        draft_file = draft_dir / f'post_draft_{test_date}.md'
        draft_file.write_text(draft_content, encoding='utf-8')

        # 초안 로드 및 게시
        with patch.object(publish_to_blog, 'DRAFT_DIR', draft_dir), \
             patch.object(publish_to_blog, 'MOCK_MODE', True):

            content = publish_to_blog.load_draft(test_date)
            assert content == draft_content

            title = publish_to_blog.extract_title(content)
            assert title is not None

            result = publish_to_blog.publish_via_api(test_date)
            assert result['success'] is True


class TestEndToEnd:
    """전체 파이프라인 E2E 테스트"""

    @patch('main.GitHubLoader')
    @patch('main.AILoadWatcher')
    @patch('main.BaekjoonLoader')
    @patch('generate_post_draft.anthropic.Anthropic')
    def test_full_pipeline(
        self,
        mock_anthropic_class,
        mock_baekjoon_loader_class,
        mock_ai_watcher_class,
        mock_github_loader_class,
        temp_data_dir,
        mock_anthropic_response,
        test_date
    ):
        """전체 파이프라인 테스트"""

        collection_log_dir = temp_data_dir['collection_log']
        draft_dir = temp_data_dir['draft']

        # 1. Mock 수집 데이터 설정
        mock_github = Mock()
        mock_github.get_all_commits.return_value = []
        mock_github_loader_class.return_value = mock_github

        mock_ai = Mock()
        mock_ai.collect_existing.return_value = 0
        mock_ai_watcher_class.return_value = mock_ai

        mock_baekjoon = Mock()
        mock_baekjoon.load.return_value = []
        mock_baekjoon_loader_class.return_value = mock_baekjoon

        # 2. 데이터 수집
        with patch.object(main, 'COLLECTION_LOG_DIR', collection_log_dir):
            # collect_all 대신 직접 데이터 저장
            sample_data = {
                'date': test_date.isoformat(),
                'github': {'commits': [], 'total_commits': 0},
                'ai_chats': {'conversations': [], 'total_conversations': 0},
                'baekjoon': {'problems': [], 'total_problems': 0}
            }
            main.save_daily_data(test_date, sample_data)

        # 3. Claude API Mock
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock(text=mock_anthropic_response['content'][0]['text'])]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_class.return_value = mock_client

        # 4. 초안 생성
        with patch.object(generate_post_draft, 'COLLECTION_LOG_DIR', collection_log_dir), \
             patch.object(generate_post_draft, 'DRAFT_DIR', draft_dir):

            data = generate_post_draft.load_daily_data(test_date)
            draft = generate_post_draft.generate_with_claude(data)
            generate_post_draft.save_draft(draft, test_date)

        # 5. 블로그 게시 (Mock 모드)
        with patch.object(publish_to_blog, 'DRAFT_DIR', draft_dir), \
             patch.object(publish_to_blog, 'MOCK_MODE', True):

            content = publish_to_blog.load_draft(test_date)
            result = publish_to_blog.publish_via_api(test_date)

            assert result['success'] is True

        # 6. 모든 파일 생성 확인
        assert (collection_log_dir / f'collect_result_{test_date}.json').exists()
        assert (draft_dir / f'post_draft_{test_date}.md').exists()
