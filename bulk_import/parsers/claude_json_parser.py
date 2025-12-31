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

        # Validate each message has required fields
        for msg in messages:
            if not isinstance(msg, dict):
                logger.warning("Message is not a dictionary")
                return False

            if 'sender' not in msg or 'text' not in msg:
                logger.warning("Message missing 'sender' or 'text' field")
                return False

        return True
