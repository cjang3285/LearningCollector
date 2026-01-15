#!/usr/bin/env python3
"""
Bulk Import 컴포넌트 테스트 스크립트

각 bulk_import 모듈의 기능을 독립적으로 테스트합니다.
"""

import sys
import json
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_claude_json_parser():
    """ClaudeJsonParser 테스트"""
    print("\n" + "="*60)
    print("TEST 1: ClaudeJsonParser")
    print("="*60)

    from bulk_import.parsers.claude_json_parser import ClaudeJsonParser

    parser = ClaudeJsonParser()

    # 샘플 JSON 데이터
    sample_data = json.dumps([
        {
            "uuid": "test-uuid-001",
            "name": "Test Conversation",
            "created_at": "2024-01-15T10:00:00.000Z",
            "updated_at": "2024-01-15T10:30:00.000Z",
            "chat_messages": [
                {
                    "uuid": "msg-001",
                    "sender": "human",
                    "text": "Hello Claude!",
                    "created_at": "2024-01-15T10:00:00.000Z"
                },
                {
                    "uuid": "msg-002",
                    "sender": "assistant",
                    "text": "Hello! How can I help you today?",
                    "created_at": "2024-01-15T10:00:05.000Z"
                }
            ]
        }
    ])

    # 파싱 실행
    conversations = parser.parse_json(sample_data)

    print(f"✓ Parsed {len(conversations)} conversation(s)")
    print(f"✓ Conversation UUID: {conversations[0]['uuid']}")
    print(f"✓ Conversation name: {conversations[0]['name']}")
    print(f"✓ Messages count: {len(conversations[0]['chat_messages'])}")

    return True


def test_claude_formatter():
    """ClaudeMessageFormatter 테스트"""
    print("\n" + "="*60)
    print("TEST 2: ClaudeMessageFormatter")
    print("="*60)

    from bulk_import.formatters.claude_formatter import ClaudeMessageFormatter

    formatter = ClaudeMessageFormatter()

    # 샘플 대화 데이터
    conversation = {
        "uuid": "test-uuid-001",
        "name": "Test Conversation",
        "created_at": "2024-01-15T10:00:00.000Z",
        "updated_at": "2024-01-15T10:30:00.000Z",
        "chat_messages": [
            {
                "uuid": "msg-001",
                "sender": "human",
                "text": "What is 2+2?",
                "created_at": "2024-01-15T10:00:00.000Z"
            },
            {
                "uuid": "msg-002",
                "sender": "assistant",
                "text": "2 + 2 = 4",
                "created_at": "2024-01-15T10:00:05.000Z"
            }
        ]
    }

    # 마크다운 변환
    markdown = formatter.format_conversation(conversation)

    print(f"✓ Generated markdown ({len(markdown)} chars)")
    print(f"✓ Markdown preview (first 200 chars):")
    print(f"  {markdown[:200]}...")

    # 마크다운 검증
    assert "Test Conversation" in markdown
    assert "What is 2+2?" in markdown
    assert "2 + 2 = 4" in markdown
    assert "## Prompt:" in markdown
    assert "## Response:" in markdown

    print(f"✓ Markdown validation passed")

    return True


def test_claude_zip_converter():
    """ClaudeZipConverter 테스트 (ZIP 파일 없이)"""
    print("\n" + "="*60)
    print("TEST 3: ClaudeZipConverter (Mock ZIP)")
    print("="*60)

    from bulk_import.converters.claude_zip_converter import ClaudeZipConverter

    # 임시 ZIP 파일 생성
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "test_claude.zip"

        # 샘플 conversations.json 생성
        conversations_data = [
            {
                "uuid": "test-uuid-001",
                "name": "Sample Conversation",
                "created_at": "2024-01-15T10:00:00.000Z",
                "updated_at": "2024-01-15T10:30:00.000Z",
                "chat_messages": [
                    {
                        "uuid": "msg-001",
                        "sender": "human",
                        "text": "Test message",
                        "created_at": "2024-01-15T10:00:00.000Z"
                    },
                    {
                        "uuid": "msg-002",
                        "sender": "assistant",
                        "text": "Test response",
                        "created_at": "2024-01-15T10:00:05.000Z"
                    }
                ]
            }
        ]

        # ZIP 파일 생성
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('conversations.json', json.dumps(conversations_data))

        print(f"✓ Created test ZIP: {zip_path}")

        # Converter 테스트
        converter = ClaudeZipConverter()
        markdowns = converter.convert_zip(str(zip_path))

        print(f"✓ Converted {len(markdowns)} conversation(s) to markdown")
        print(f"✓ First markdown preview (first 200 chars):")
        print(f"  {markdowns[0][:200]}...")

        # 날짜 필터링 테스트
        after = datetime(2024, 1, 15, 9, 0, 0)
        before = datetime(2024, 1, 15, 11, 0, 0)

        filtered = converter.filter_by_date(markdowns, after=after, before=before)
        print(f"✓ Filtered conversations: {len(filtered)}")

    return True


def test_zip_finder():
    """ZipFinder 테스트 (파일 없어도 OK)"""
    print("\n" + "="*60)
    print("TEST 4: ClaudeZipFinder")
    print("="*60)

    from bulk_import.zip_finder import ClaudeZipFinder

    finder = ClaudeZipFinder()

    # 기본 디렉토리 확인
    print(f"✓ Search directories configured:")
    for dir_path in [Path.home() / "Downloads", Path.home() / "shared"]:
        exists = "EXISTS" if dir_path.exists() else "NOT FOUND"
        print(f"  - {dir_path}: {exists}")

    # ZIP 파일 찾기 (없어도 OK)
    try:
        zip_file = finder.find_latest_zip()
        if zip_file:
            print(f"✓ Found Claude ZIP: {zip_file}")
        else:
            print(f"✓ No Claude ZIP found (this is OK for testing)")
    except ValueError as e:
        print(f"✓ Expected behavior: {e}")

    return True


def test_integration():
    """통합 테스트 - 전체 워크플로우"""
    print("\n" + "="*60)
    print("TEST 5: Full Integration Test")
    print("="*60)

    from bulk_import.claude_parse import ClaudeMigrationParser

    # 임시 ZIP 파일 생성
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "test_full.zip"

        # 여러 대화가 포함된 ZIP 생성
        conversations_data = [
            {
                "uuid": f"conv-{i:03d}",
                "name": f"Conversation {i+1}",
                "created_at": f"2024-01-{15+i:02d}T10:00:00.000Z",
                "updated_at": f"2024-01-{15+i:02d}T11:00:00.000Z",
                "chat_messages": [
                    {
                        "uuid": f"msg-{i:03d}-001",
                        "sender": "human",
                        "text": f"Question {i+1}",
                        "created_at": f"2024-01-{15+i:02d}T10:00:00.000Z"
                    },
                    {
                        "uuid": f"msg-{i:03d}-002",
                        "sender": "assistant",
                        "text": f"Answer {i+1}",
                        "created_at": f"2024-01-{15+i:02d}T10:00:05.000Z"
                    }
                ]
            }
            for i in range(3)  # 3개의 대화
        ]

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('conversations.json', json.dumps(conversations_data))

        print(f"✓ Created test ZIP with {len(conversations_data)} conversations")

        # Parser로 변환
        parser = ClaudeMigrationParser()
        markdowns = parser.parse_zip(str(zip_path))

        print(f"✓ Converted to {len(markdowns)} markdown files")

        # 날짜 필터링 테스트
        after = datetime(2024, 1, 16, 0, 0, 0)
        before = datetime(2024, 1, 16, 23, 59, 59)

        filtered = parser.filter_by_date(markdowns, after=after, before=before)
        print(f"✓ Filtered by date (2024-01-16): {len(filtered)} conversation(s)")

        # 마크다운 내용 검증
        for i, md in enumerate(markdowns):
            assert f"Conversation {i+1}" in md
            assert "## Prompt:" in md
            assert "## Response:" in md
            print(f"✓ Markdown {i+1} validation passed")

    return True


def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("BULK IMPORT COMPONENTS TEST SUITE")
    print("="*60)

    tests = [
        ("ClaudeJsonParser", test_claude_json_parser),
        ("ClaudeMessageFormatter", test_claude_formatter),
        ("ClaudeZipConverter", test_claude_zip_converter),
        ("ClaudeZipFinder", test_zip_finder),
        ("Full Integration", test_integration),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {name}: PASSED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name}: FAILED")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed/len(tests)*100:.1f}%")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
