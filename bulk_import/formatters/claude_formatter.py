#!/usr/bin/env python3
"""
Claude conversation formatter.

SOLID Principles:
- SRP: Single Responsibility - only formats Claude conversations to markdown
- OCP: Open for extension - can be subclassed for custom formatting
- DIP: Implements IMarkdownFormatter interface
"""

import html
from typing import Dict, List
from .base_formatter import IMarkdownFormatter


class ClaudeMessageFormatter(IMarkdownFormatter):
    """
    Formats Claude conversations to markdown compatible with ai_chat_parse.py.

    This formatter produces markdown that matches the format expected by
    AIMarkdownParser, using the ## Prompt: / ## Response: pattern.
    """

    def format_conversation(self, conversation: Dict) -> str:
        """
        Convert Claude conversation to markdown format.

        Args:
            conversation: Dictionary with keys:
                - name: conversation title
                - created_at: ISO timestamp
                - updated_at: ISO timestamp
                - uuid: conversation ID
                - chat_messages: list of message dicts

        Returns:
            Markdown-formatted conversation string

        Raises:
            ValueError: If required fields are missing
        """
        if not conversation:
            raise ValueError("Conversation data is empty")

        if 'chat_messages' not in conversation:
            raise ValueError("Conversation missing 'chat_messages' field")

        lines = []

        # Title
        title = conversation.get('name', 'Untitled')
        lines.append(f"# {self._clean_text(title)}\n")

        # Metadata
        created_at = conversation.get('created_at', '')
        updated_at = conversation.get('updated_at', '')
        uuid = conversation.get('uuid', '')

        lines.append(f"**Created:** {created_at}")
        lines.append(f"**Updated:** {updated_at}")
        lines.append(f"**Link:** https://claude.ai/chat/{uuid}\n")

        # Messages
        messages = conversation.get('chat_messages', [])
        for msg in messages:
            formatted_msg = self.format_message(msg)
            if formatted_msg:
                lines.append(formatted_msg)
                lines.append("")  # Empty line after each message

        # Footer
        lines.append("---\n")
        lines.append("*Powered by Claude Exporter*")

        return "\n".join(lines)

    def format_message(self, message: Dict) -> str:
        """
        Format a single Claude message.

        Args:
            message: Dictionary with keys:
                - sender: 'human' or 'assistant'
                - text: message content

        Returns:
            Formatted message string with header
        """
        if not message:
            return ""

        sender = message.get('sender', 'unknown')
        text = message.get('text', '')

        # Clean and decode text
        text = self._clean_text(text)

        if sender == 'human':
            return f"## Prompt:\n\n{text}"
        elif sender == 'assistant':
            return f"## Response:\n\n{text}"
        else:
            # Unknown sender, skip
            return ""

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.

        - Decodes HTML entities
        - Normalizes Unicode characters
        - Strips excessive whitespace

        Args:
            text: Raw text content

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Decode HTML entities (e.g., &lt; -> <)
        text = html.unescape(text)

        # Normalize Unicode (important for Korean characters)
        import unicodedata
        text = unicodedata.normalize('NFC', text)

        # Strip excessive whitespace at start/end
        text = text.strip()

        return text
