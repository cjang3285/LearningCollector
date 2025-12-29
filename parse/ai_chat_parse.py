#!/usr/bin/env python3
"""
AI Chat Markdown Parser

Parses markdown exports from AI chat browser extensions:
- Claude Exporter
- ChatGPT Exporter
- Gemini Exporter
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('ai_chat_parse')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class AIConversationData:
    """파싱된 AI 대화 데이터"""
    provider: str  # claude, chatgpt, gemini
    title: str
    created_at: Optional[str]
    updated_at: Optional[str]
    link: Optional[str]
    user: Optional[str]
    total_messages: int
    user_messages: int
    assistant_messages: int
    total_chars: int
    has_code: bool
    code_blocks: List[Dict]
    messages: List[Dict]

    def to_dict(self):
        return asdict(self)


class AIMarkdownParser:
    """AI 채팅 마크다운 파서"""

    def detect_provider(self, filename: str, content: str) -> str:
        """파일명과 내용에서 AI 제공자 감지"""
        name_lower = filename.lower()
        content_lower = content.lower()

        # 파일명으로 감지
        if 'claude' in name_lower:
            return 'claude'
        elif 'chatgpt' in name_lower or 'gpt' in name_lower:
            return 'chatgpt'
        elif 'gemini' in name_lower:
            return 'gemini'

        # 내용으로 감지 (footer 확인)
        if 'powered by claude exporter' in content_lower:
            return 'claude'
        elif 'powered by chatgpt exporter' in content_lower:
            return 'chatgpt'
        elif 'powered by gemini exporter' in content_lower:
            return 'gemini'

        return 'unknown'

    def extract_metadata(self, content: str, provider: str) -> Dict:
        """메타데이터 추출"""
        metadata = {}

        # 제목 추출 (첫 번째 # 헤더)
        title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        metadata['title'] = title_match.group(1).strip() if title_match else 'Untitled'

        # Claude 메타데이터
        if provider == 'claude':
            created_match = re.search(r'\*\*Created:\*\*\s+(.+?)(?:\n|$)', content)
            updated_match = re.search(r'\*\*Updated:\*\*\s+(.+?)(?:\n|$)', content)
            link_match = re.search(r'\*\*Link:\*\*\s+\[.+?\]\((.+?)\)', content)

            metadata['created_at'] = created_match.group(1).strip() if created_match else None
            metadata['updated_at'] = updated_match.group(1).strip() if updated_match else None
            metadata['link'] = link_match.group(1).strip() if link_match else None

        # ChatGPT 메타데이터
        elif provider == 'chatgpt':
            created_match = re.search(r'\*\*Created:\*\*\s+(.+?)(?:\n|$)', content)
            updated_match = re.search(r'\*\*Updated:\*\*\s+(.+?)(?:\n|$)', content)
            link_match = re.search(r'\*\*Link:\*\*\s+\[.+?\]\((.+?)\)', content)
            user_match = re.search(r'\*\*User:\*\*\s+(.+?)(?:\n|$)', content)

            metadata['created_at'] = created_match.group(1).strip() if created_match else None
            metadata['updated_at'] = updated_match.group(1).strip() if updated_match else None
            metadata['link'] = link_match.group(1).strip() if link_match else None
            metadata['user'] = user_match.group(1).strip() if user_match else None

        # Gemini 메타데이터 (간단한 구조)
        elif provider == 'gemini':
            # Gemini는 메타데이터가 적음, 파일명에서 날짜 추출 시도
            metadata['created_at'] = None
            metadata['updated_at'] = None
            metadata['link'] = None

        return metadata

    def extract_messages(self, content: str) -> List[Dict]:
        """Prompt/Response 쌍 추출"""
        messages = []

        # ## Prompt: / ## Response: 패턴으로 분리
        # re.split으로 구분자도 함께 캡처
        sections = re.split(r'## (Prompt|Response):\s*\n', content)

        # sections[0]은 헤더 부분이므로 제외
        # sections[1:]부터 (Prompt/Response, 내용) 쌍으로 처리
        i = 1
        while i < len(sections) - 1:
            msg_type = sections[i].lower()  # 'prompt' or 'response'
            msg_content = sections[i + 1].strip()

            # 다음 섹션 시작 전까지가 내용
            # 이미 split으로 분리되었으므로 그대로 사용

            role = 'user' if msg_type == 'prompt' else 'assistant'
            messages.append({
                'role': role,
                'content': msg_content
            })

            i += 2

        return messages

    def extract_code_blocks(self, content: str) -> List[Dict]:
        """코드 블록 추출"""
        blocks = []

        # ```language\ncode\n``` 패턴 매칭
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            language = match.group(1) or ''
            code = match.group(2).strip()

            blocks.append({
                'language': language,
                'code': code,
                'lines': code.count('\n') + 1
            })

        return blocks

    def parse_file(self, file_path: str) -> AIConversationData:
        """마크다운 파일 파싱"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없음: {file_path}")

        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 제공자 감지
        provider = self.detect_provider(file_path.name, content)
        logger.info(f"감지된 제공자: {provider}")

        # 메타데이터 추출
        metadata = self.extract_metadata(content, provider)

        # 메시지 추출
        messages = self.extract_messages(content)

        # 코드 블록 추출
        code_blocks = self.extract_code_blocks(content)

        # 통계 계산
        user_msgs = sum(1 for msg in messages if msg['role'] == 'user')
        assistant_msgs = sum(1 for msg in messages if msg['role'] == 'assistant')
        total_chars = sum(len(msg['content']) for msg in messages)
        has_code = len(code_blocks) > 0

        return AIConversationData(
            provider=provider,
            title=metadata['title'],
            created_at=metadata.get('created_at'),
            updated_at=metadata.get('updated_at'),
            link=metadata.get('link'),
            user=metadata.get('user'),
            total_messages=len(messages),
            user_messages=user_msgs,
            assistant_messages=assistant_msgs,
            total_chars=total_chars,
            has_code=has_code,
            code_blocks=code_blocks,
            messages=messages
        )

    def parse_multiple(self, file_paths: List[str]) -> List[AIConversationData]:
        """여러 파일 일괄 파싱"""
        results = []
        for file_path in file_paths:
            try:
                result = self.parse_file(file_path)
                results.append(result)
                logger.info(f"[OK] {Path(file_path).name}: {result.total_messages}개 메시지")
            except Exception as e:
                logger.error(f"[FAIL] {Path(file_path).name}: {e}")

        return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("사용법: python ai_chat_parse.py <markdown_file>")
        sys.exit(1)

    parser = AIMarkdownParser()
    result = parser.parse_file(sys.argv[1])

    print(f"\n제공자: {result.provider}")
    print(f"제목: {result.title}")
    print(f"생성일: {result.created_at}")
    print(f"수정일: {result.updated_at}")
    print(f"메시지: {result.total_messages}개 (사용자: {result.user_messages}, AI: {result.assistant_messages})")
    print(f"코드 블록: {len(result.code_blocks)}개")
    print(f"\n첫 메시지 미리보기:")
    if result.messages:
        first_msg = result.messages[0]
        preview = first_msg['content'][:200] + '...' if len(first_msg['content']) > 200 else first_msg['content']
        print(f"[{first_msg['role']}] {preview}")
