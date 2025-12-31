#!/usr/bin/env python3
"""
Base parser interface for JSON conversation data.

SOLID Principles:
- ISP: Minimal interface
- DIP: Abstractions for parsers
"""

from abc import ABC, abstractmethod
from typing import List, Dict


class IJsonParser(ABC):
    """Interface for parsing JSON conversation data."""

    @abstractmethod
    def parse_json(self, json_data: str) -> List[Dict]:
        """
        Parse JSON string to list of conversation dictionaries.

        Args:
            json_data: Raw JSON string

        Returns:
            List of conversation dictionaries

        Raises:
            ValueError: If JSON is invalid
        """
        pass

    @abstractmethod
    def validate_conversation(self, conversation: Dict) -> bool:
        """
        Validate a conversation dictionary.

        Args:
            conversation: Conversation data

        Returns:
            True if valid, False otherwise
        """
        pass
