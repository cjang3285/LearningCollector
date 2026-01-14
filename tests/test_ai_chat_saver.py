"""
AI Chat Saver 날짜 파싱 테스트
"""
import unittest
from datetime import date
from storage.ai_chat_saver import AIChatSaver


class TestAIChatSaverDateParsing(unittest.TestCase):
    """날짜 파싱 기능 테스트"""

    def setUp(self):
        # DB 연결 없이 날짜 파싱만 테스트 (db_config=None이면 환경변수에서 로드)
        self.saver = AIChatSaver()

    def test_parse_chatgpt_exporter_format(self):
        """ChatGPT Exporter 형식 파싱"""
        result = self.saver._parse_date_string("1/13/2026 21:08:26")
        self.assertEqual(result, date(2026, 1, 13))

    def test_parse_claude_exporter_format(self):
        """Claude Exporter 형식 파싱"""
        result = self.saver._parse_date_string("1/4/2026 13:52:52")
        self.assertEqual(result, date(2026, 1, 4))

    def test_parse_simple_date_format(self):
        """간단한 날짜 형식 파싱"""
        result = self.saver._parse_date_string("12/30/2025")
        self.assertEqual(result, date(2025, 12, 30))

    def test_parse_iso_format(self):
        """ISO 8601 형식 파싱"""
        result = self.saver._parse_date_string("2024-01-01T12:00:00.000Z")
        self.assertEqual(result, date(2024, 1, 1))

    def test_parse_invalid_date(self):
        """잘못된 날짜 형식"""
        result = self.saver._parse_date_string("invalid date")
        self.assertIsNone(result)

    def test_parse_empty_string(self):
        """빈 문자열"""
        result = self.saver._parse_date_string("")
        self.assertIsNone(result)

    def test_parse_none(self):
        """None 입력"""
        result = self.saver._parse_date_string(None)
        self.assertIsNone(result)

    def test_conversation_date_with_created_at(self):
        """created_at이 있는 대화"""
        conversation = {
            'title': 'Test',
            'created_at': '1/13/2026 21:08:26',
        }
        result = self.saver._parse_conversation_date(conversation)
        self.assertEqual(result, date(2026, 1, 13))

    def test_conversation_date_with_updated_at_fallback(self):
        """created_at 없고 updated_at만 있는 경우"""
        conversation = {
            'title': 'Test',
            'updated_at': '1/4/2026 13:52:52',
        }
        result = self.saver._parse_conversation_date(conversation)
        self.assertEqual(result, date(2026, 1, 4))

    def test_conversation_date_with_fallback(self):
        """메타데이터 없는 경우 fallback 사용"""
        conversation = {'title': 'Test'}
        fallback = date(2025, 12, 30)
        result = self.saver._parse_conversation_date(conversation, fallback_date=fallback)
        self.assertEqual(result, fallback)

    def test_conversation_date_with_no_metadata(self):
        """메타데이터 없고 fallback도 없으면 오늘 날짜"""
        conversation = {'title': 'Test'}
        result = self.saver._parse_conversation_date(conversation)
        self.assertEqual(result, date.today())


if __name__ == '__main__':
    unittest.main()
