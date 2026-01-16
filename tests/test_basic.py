"""기본 기능 테스트"""

import pytest
import json
from datetime import date
from pathlib import Path


class TestBasicFunctionality:
    """기본 기능 테스트"""

    def test_fixture_files_exist(self, fixtures_dir):
        """픽스처 파일 존재 확인"""
        assert fixtures_dir.exists()
        assert (fixtures_dir / 'ai_chat').exists()
        assert (fixtures_dir / 'github').exists()
        assert (fixtures_dir / 'baekjoon').exists()

    def test_temp_directories(self, temp_data_dir):
        """임시 디렉토리 생성 확인"""
        assert temp_data_dir['collection_log'].exists()
        assert temp_data_dir['draft'].exists()

    def test_sample_data_structure(self, sample_collection_data):
        """샘플 데이터 구조 확인"""
        assert 'date' in sample_collection_data
        assert 'github' in sample_collection_data
        assert 'ai_chats' in sample_collection_data
        assert 'baekjoon' in sample_collection_data

    def test_json_serialization(self, sample_collection_data):
        """JSON 직렬화 가능 확인"""
        json_str = json.dumps(sample_collection_data)
        assert len(json_str) > 0

        loaded = json.loads(json_str)
        assert loaded['date'] == sample_collection_data['date']


class TestFileOperations:
    """파일 작업 테스트"""

    def test_read_write_json(self, temp_data_dir, sample_collection_data, test_date):
        """JSON 파일 읽기/쓰기"""
        collection_log_dir = temp_data_dir['collection_log']

        # 파일 쓰기
        file_path = collection_log_dir / f'test_{test_date}.json'
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_collection_data, f)

        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        assert loaded_data == sample_collection_data

    def test_read_write_markdown(self, temp_data_dir, test_date):
        """마크다운 파일 읽기/쓰기"""
        draft_dir = temp_data_dir['draft']

        content = f"# {test_date} 학습 정리\n\n테스트"

        # 파일 쓰기
        file_path = draft_dir / f'test_{test_date}.md'
        file_path.write_text(content, encoding='utf-8')

        # 파일 읽기
        loaded_content = file_path.read_text(encoding='utf-8')

        assert loaded_content == content


class TestProviderDetection:
    """제공자 감지 테스트"""

    def test_claude_detection(self):
        """Claude 파일명 감지"""
        from parse.ai_chat_parse import AIMarkdownParser
        parser = AIMarkdownParser()

        assert parser.detect_provider('claude_chat.md') == 'claude'
        assert parser.detect_provider('Claude_Export.md') == 'claude'

    def test_chatgpt_detection(self):
        """ChatGPT 파일명 감지"""
        from parse.ai_chat_parse import AIMarkdownParser
        parser = AIMarkdownParser()

        assert parser.detect_provider('chatgpt_conversation.md') == 'chatgpt'
        assert parser.detect_provider('ChatGPT_2024.md') == 'chatgpt'

    def test_gemini_detection(self):
        """Gemini 파일명 감지"""
        from parse.ai_chat_parse import AIMarkdownParser
        parser = AIMarkdownParser()

        assert parser.detect_provider('gemini_chat.md') == 'gemini'

    def test_unknown_detection(self):
        """알 수 없는 제공자"""
        from parse.ai_chat_parse import AIMarkdownParser
        parser = AIMarkdownParser()

        assert parser.detect_provider('random_file.md') == 'unknown'


class TestLanguageDetection:
    """프로그래밍 언어 감지 테스트"""

    def test_python_detection(self):
        """Python 파일 감지"""
        from parse.baekjoon_parse import BaekjoonParser
        parser = BaekjoonParser()

        assert parser.detect_language('solution.py') == 'python'

    def test_cpp_detection(self):
        """C++ 파일 감지"""
        from parse.baekjoon_parse import BaekjoonParser
        parser = BaekjoonParser()

        assert parser.detect_language('solution.cpp') == 'cpp'
        assert parser.detect_language('solution.cc') == 'cpp'

    def test_java_detection(self):
        """Java 파일 감지"""
        from parse.baekjoon_parse import BaekjoonParser
        parser = BaekjoonParser()

        assert parser.detect_language('Main.java') == 'java'

    def test_c_detection(self):
        """C 파일 감지"""
        from parse.baekjoon_parse import BaekjoonParser
        parser = BaekjoonParser()

        assert parser.detect_language('solution.c') == 'c'


class TestDateHandling:
    """날짜 처리 테스트"""

    def test_date_to_string(self, test_date):
        """날짜 → 문자열 변환"""
        date_str = test_date.isoformat()
        assert date_str == '2024-01-15'

    def test_string_to_date(self, test_date):
        """문자열 → 날짜 변환"""
        date_str = '2024-01-15'
        parsed_date = date.fromisoformat(date_str)
        assert parsed_date == test_date

    def test_filename_with_date(self, test_date):
        """날짜 포함 파일명"""
        filename = f'collect_result_{test_date}.json'
        assert '2024-01-15' in filename
