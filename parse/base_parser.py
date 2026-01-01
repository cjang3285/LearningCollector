#!/usr/bin/env python3
"""
Base parser for project parsers. Provides an abstract interface and helpers.
"""
from abc import ABC, abstractmethod
from typing import List, Any


class BaseParser(ABC):
    """Abstract base parser. Parsers may override specific methods as needed."""

    @abstractmethod
    def parse(self, item: Any) -> dict:
        """Parse a single item into a dict."""

    def parse_many(self, items: List[Any]) -> List[dict]:
        """Default implementation: iterate and call `parse` for each item."""
        parsed = []
        for it in items:
            parsed.append(self.parse(it))
        return parsed

    def validate(self, parsed: dict) -> bool:
        """Optional validation hook. Default accepts everything."""
        return True
