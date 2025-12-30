#!/usr/bin/env python3
"""
Claude Migration Parser - Claude ZIP → 마크다운 어댑터

Claude.ai ZIP 파일을 마크다운 형식으로 변환하여
ai_chat_parse.py와 호환되도록 합니다.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import zipfile
import logging
from datetime import datetime
from typing import List, Dict, Optional

from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('claude_migration')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClaudeMigrationParser:
    """Claude ZIP 파일을 마크다운 형식으로 변환하는 어댑터"""

    def convert_to_markdown(self, conversation: Dict) -> str:
        """
        Claude ZIP의 JSON 대화를 마크다운 형식으로 변환

        Args:
            conversation: ZIP에서 추출한 대화 JSON

        Returns:
            마크다운 형식의 문자열 (ai_chat_parse.py 호환)
        """
        lines = []

        # 제목
        title = conversation.get('name', 'Untitled')
        lines.append(f"# {title}\n")

        # 메타데이터 (ai_chat_parse.py의 Claude 형식과 동일)
        created_at = conversation.get('created_at', '')
        updated_at = conversation.get('updated_at', '')
        uuid = conversation.get('uuid', '')

        lines.append(f"**Created:** {created_at}")
        lines.append(f"**Updated:** {updated_at}")
        lines.append(f"**Link:** https://claude.ai/chat/{uuid}\n")

        # 메시지들 변환
        messages = conversation.get('chat_messages', [])
        for msg in messages:
            sender = msg.get('sender', 'unknown')
            text = msg.get('text', '')

            if sender == 'human':
                lines.append("## Prompt:\n")
                lines.append(text)
                lines.append("")  # 빈 줄
            elif sender == 'assistant':
                lines.append("## Response:\n")
                lines.append(text)
                lines.append("")  # 빈 줄

        # Footer
        lines.append("---\n")
        lines.append("*Powered by Claude Exporter*")

        return "\n".join(lines)

    def parse_zip(self, zip_path: str) -> List[str]:
        """
        ZIP 파일에서 대화들을 추출하여 마크다운 리스트로 변환

        Args:
            zip_path: ZIP 파일 경로

        Returns:
            마크다운 문자열 리스트
        """
        zip_path = Path(zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP 파일을 찾을 수 없음: {zip_path}")

        markdowns = []

        with zipfile.ZipFile(zip_path, 'r') as zf:
            # conversations.json 찾기
            json_files = [f for f in zf.namelist() if f.endswith('.json')]

            for json_file in json_files:
                try:
                    with zf.open(json_file) as f:
                        data = json.load(f)

                        # 단일 대화인 경우
                        if isinstance(data, dict) and 'chat_messages' in data:
                            markdown = self.convert_to_markdown(data)
                            markdowns.append(markdown)

                        # 여러 대화가 배열인 경우
                        elif isinstance(data, list):
                            for conversation in data:
                                if 'chat_messages' in conversation:
                                    markdown = self.convert_to_markdown(conversation)
                                    markdowns.append(markdown)

                except Exception as e:
                    logger.error(f"JSON 파싱 실패 ({json_file}): {e}")
                    continue

        logger.info(f"ZIP에서 {len(markdowns)}개 대화를 마크다운으로 변환 완료")
        return markdowns

    def filter_by_date(
        self,
        markdowns: List[str],
        after: datetime = None,
        before: datetime = None
    ) -> List[str]:
        """
        날짜로 마크다운 필터링

        Args:
            markdowns: 마크다운 리스트
            after: 시작 날짜
            before: 종료 날짜

        Returns:
            필터링된 마크다운 리스트
        """
        if not after and not before:
            return markdowns

        filtered = []

        for md in markdowns:
            # Created 날짜 추출
            import re
            match = re.search(r'\*\*Created:\*\*\s+(.+)', md)
            if not match:
                continue

            created_str = match.group(1).strip()

            try:
                # ISO 형식 파싱
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))

                # 날짜 필터링
                if after and created_dt < after:
                    continue
                if before and created_dt > before:
                    continue

                filtered.append(md)

            except Exception as e:
                logger.warning(f"날짜 파싱 실패: {created_str}")
                continue

        logger.info(f"날짜 필터링: {len(markdowns)}개 → {len(filtered)}개")
        return filtered


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("사용법: python claude_parse.py <zip_file>")
        sys.exit(1)

    parser = ClaudeMigrationParser()
    markdowns = parser.parse_zip(sys.argv[1])

    print(f"\n변환된 마크다운 {len(markdowns)}개:")
    for i, md in enumerate(markdowns[:3], 1):
        print(f"\n[{i}] 미리보기:")
        print(md[:500] + "..." if len(md) > 500 else md)
