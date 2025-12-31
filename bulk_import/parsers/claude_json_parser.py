#!/usr/bin/env python3
"""
Claude JSON parser with Unicode handling.

SOLID Principles:
- SRP: Only responsible for parsing Claude JSON format
- DIP: Implements IJsonParser interface
"""

import json
import logging
from typing import List, Dict
from .base_parser import IJsonParser

logger = logging.getLogger(__name__)


class ClaudeJsonParser(IJsonParser):
    """
    Parser for Claude conversations.json format.

    Handles:
    - Unicode escape sequences (\\uXXXX)
    - HTML entities
    - Both single conversation and array formats
    """

    def parse_json(self, json_data: str) -> List[Dict]:
        """
        Parse Claude JSON data to conversation list.

        Args:
            json_data: Raw JSON string from Claude export

        Returns:
            List of conversation dictionaries

        Raises:
            ValueError: If JSON is invalid or malformed
        """
        if not json_data:
            raise ValueError("JSON data is empty")

        try:
            # Parse JSON (automatically handles \\uXXXX escape sequences)
            data = json.loads(json_data)

            conversations = []

            # Handle single conversation object
            if isinstance(data, dict):
                if self.validate_conversation(data):
                    conversations.append(data)
                else:
                    logger.warning("Conversation failed validation, skipping")

            # Handle array of conversations
            elif isinstance(data, list):
                for conv in data:
                    if isinstance(conv, dict) and self.validate_conversation(conv):
                        conversations.append(conv)
                    else:
                        logger.warning("Skipping invalid conversation")

            else:
                raise ValueError(f"Unexpected JSON root type: {type(data)}")

            logger.info(f"Parsed {len(conversations)} conversations from JSON")

            # 첫 번째 대화 미리보기 출력
            if conversations:
                self._log_conversation_preview(conversations[0])

            return conversations

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to parse JSON: {e}") from e

    def validate_conversation(self, conversation: Dict) -> bool:
        """
        Validate Claude conversation structure.

        Required fields:
        - chat_messages: list of messages

        Optional fields:
        - name, created_at, updated_at, uuid

        Args:
            conversation: Conversation dictionary

        Returns:
            True if valid structure
        """
        if not isinstance(conversation, dict):
            return False

        # Must have chat_messages
        if 'chat_messages' not in conversation:
            logger.warning("Conversation missing 'chat_messages' field")
            return False

        messages = conversation['chat_messages']
        if not isinstance(messages, list):
            logger.warning("'chat_messages' is not a list")
            return False

        # Skip empty conversations
        if len(messages) == 0:
            logger.debug("Conversation has no messages, skipping")
            return False

        # Validate each message has required fields
        for msg in messages:
            if not isinstance(msg, dict):
                logger.warning("Message is not a dictionary")
                return False

            if 'sender' not in msg or 'text' not in msg:
                logger.warning("Message missing 'sender' or 'text' field")
                return False

        return True

    def _log_conversation_preview(self, conversation: Dict) -> None:
        """
        로그에 대화 미리보기 출력 (디버깅용).

        Args:
            conversation: 대화 딕셔너리
        """
        try:
            title = conversation.get('name', 'Untitled')
            created_at = conversation.get('created_at', 'Unknown')
            messages = conversation.get('chat_messages', [])

            logger.info("=" * 60)
            logger.info("JSON 파싱 결과 미리보기:")
            logger.info(f"  제목: {title}")
            logger.info(f"  생성일: {created_at}")
            logger.info(f"  메시지 수: {len(messages)}")

            if messages:
                first_msg = messages[0]
                sender = first_msg.get('sender', 'unknown')
                text = first_msg.get('text', '')

                # 텍스트 미리보기 (처음 200자)
                preview = text[:200] + "..." if len(text) > 200 else text

                logger.info(f"  첫 메시지 ({sender}):")
                logger.info(f"    {preview}")

            logger.info("=" * 60)

        except Exception as e:
            logger.debug(f"미리보기 출력 실패: {e}")
