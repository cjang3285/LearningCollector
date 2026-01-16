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
import unicodedata
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from config.settings import get_log_file
from config.logging_config import setup_logging
from parse.base_parser import BaseParser

# 로깅 설정 (INFO/WARNING → stdout, ERROR → stderr, ms 제거)
logger = setup_logging(get_log_file('ai_chat_parse'), __name__)


class ParseError(Exception):
    """파싱 에러"""
    pass


@dataclass
class AIConversationData:
    """파싱된 AI 대화 데이터 (간소화)"""
    provider: str  # claude, chatgpt, gemini
    messages: List[Dict]
    code_blocks: List[Dict]

    def to_dict(self):
        return asdict(self)


class AIMarkdownParser(BaseParser):
    """
    AI 채팅 마크다운 파서 (간소화)

    책임: AI Chat 마크다운 파일 파싱
    """

    def detect_provider(self, filename: str) -> str:
        """파일명에서 AI 제공자 감지 (간소화)"""
        name_lower = filename.lower()

        # 파일명으로 감지
        if 'claude' in name_lower:
            return 'claude'
        elif 'chatgpt' in name_lower or 'gpt' in name_lower:
            return 'chatgpt'
        elif 'gemini' in name_lower:
            return 'gemini'

        return 'unknown'

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

        # 유니코드 정규화 (NFD → NFC 변환으로 한글 자모 분리 문제 해결)
        content = unicodedata.normalize('NFC', content)

        # 제공자 감지 (파일명만 사용)
        provider = self.detect_provider(file_path.name)
        logger.info(f"감지된 제공자: {provider}")

        # 메시지 추출
        messages = self.extract_messages(content)

        # 코드 블록 추출
        code_blocks = self.extract_code_blocks(content)

        return AIConversationData(
            provider=provider,
            messages=messages,
            code_blocks=code_blocks
        )

    # ========================================
    # IParser 인터페이스 구현
    # ========================================

    def parse(self, file_path: str) -> Dict:
        """
        단일 파일 파싱 (IParser 인터페이스 구현)

        Args:
            file_path: 파일 경로

        Returns:
            Dict: 파싱된 데이터 (딕셔너리)

        Raises:
            ParseError: 파싱 실패 시
        """
        try:
            result = self.parse_file(file_path)
            return result.to_dict()
        except Exception as e:
            raise ParseError(f"파싱 실패 ({file_path}): {e}") from e

    def parse_multiple(self, file_paths: List[str]) -> List[Dict]:
        """
        여러 파일 일괄 파싱 (IParser 인터페이스 구현)

        Args:
            file_paths: 파일 경로 리스트

        Returns:
            List[Dict]: 파싱된 데이터 리스트 (딕셔너리)

        Note:
            기존 코드와의 하위 호환성:
            - 이전: List[AIConversationData] 반환
            - 현재: List[Dict] 반환 (to_dict() 자동 적용)
        """
        results = []

        for file_path in file_paths:
            try:
                data = self.parse(file_path)
                results.append(data)
                # 로깅을 위해 메시지 개수 출력
                logger.info(f"[OK] {Path(file_path).name}: {data.get('total_messages', 0)}개 메시지")
            except Exception as e:
                # 모든 예외 catch (ParseError뿐 아니라 다른 에러도)
                logger.error(f"[FAIL] {Path(file_path).name}: {type(e).__name__}: {e}")
                # 개별 파일 실패는 무시하고 계속 진행
                continue

        logger.info(f"파싱 완료: {len(results)}/{len(file_paths)}개 성공")
        return results

    def validate(self, data: Dict) -> bool:
        """
        파싱된 데이터 유효성 검증 (간소화)

        Args:
            data: 파싱된 데이터

        Returns:
            bool: 유효하면 True, 아니면 False
        """
        required_fields = ['provider', 'messages', 'code_blocks']

        # 필수 필드 확인
        for field in required_fields:
            if field not in data:
                logger.warning(f"필수 필드 누락: {field}")
                return False

        # 메시지 리스트 검증
        messages = data.get('messages', [])
        if not isinstance(messages, list) or len(messages) == 0:
            logger.warning("메시지가 없거나 리스트가 아닙니다")
            return False

        # 각 메시지 검증
        for msg in messages:
            if 'role' not in msg or 'content' not in msg:
                logger.warning("메시지 형식 오류: role, content 필요")
                return False

        return True


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("사용법: python ai_chat_parse.py <markdown_file>")
        sys.exit(1)

    parser = AIMarkdownParser()
    result = parser.parse_file(sys.argv[1])

    print(f"\n제공자: {result.provider}")
    print(f"메시지: {len(result.messages)}개")
    print(f"코드 블록: {len(result.code_blocks)}개")
    print(f"\n첫 메시지 미리보기:")
    if result.messages:
        first_msg = result.messages[0]
        preview = first_msg['content'][:200] + '...' if len(first_msg['content']) > 200 else first_msg['content']
        print(f"[{first_msg['role']}] {preview}")
