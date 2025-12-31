#!/usr/bin/env python3
"""
Base formatter interface for markdown conversion.

SOLID Principles:
- ISP: Interface Segregation - minimal interface
- DIP: Depend on abstractions, not concretions
"""

from abc import ABC, abstractmethod
from typing import Dict


class IMarkdownFormatter(ABC):
    """Interface for converting conversation data to markdown format."""

    @abstractmethod
    def format_conversation(self, conversation: Dict) -> str:
        """
        Convert a conversation dict to markdown format.

        Args:
            conversation: Conversation data dictionary

        Returns:
            Markdown-formatted string

        Raises:
            ValueError: If conversation data is invalid
        """
        pass

    @abstractmethod
    def format_message(self, message: Dict) -> str:
        """
        Format a single message.

        Args:
            message: Message data dictionary

        Returns:
            Formatted message string
        """
        pass
