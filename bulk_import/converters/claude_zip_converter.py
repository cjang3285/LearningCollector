#!/usr/bin/env python3
"""
Claude ZIP to Markdown converter.

SOLID Principles:
- SRP: Coordinates ZIP extraction, JSON parsing, and markdown formatting
- OCP: Can be extended for new formats without modification
- DIP: Depends on IJsonParser and IMarkdownFormatter abstractions
"""

import zipfile
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from bulk_import.parsers import IJsonParser, ClaudeJsonParser
from bulk_import.formatters import IMarkdownFormatter, ClaudeMessageFormatter

logger = logging.getLogger(__name__)


class ClaudeZipConverter:
    """
    Converts Claude ZIP exports to markdown format.

    This class follows the Dependency Inversion Principle by depending on
    abstractions (IJsonParser, IMarkdownFormatter) rather than concrete classes.
    """

    def __init__(
        self,
        json_parser: Optional[IJsonParser] = None,
        markdown_formatter: Optional[IMarkdownFormatter] = None
    ):
        """
        Initialize converter with dependencies.

        Args:
            json_parser: JSON parser instance (defaults to ClaudeJsonParser)
            markdown_formatter: Markdown formatter (defaults to ClaudeMessageFormatter)
        """
        # Dependency Injection (DIP)
        self.json_parser = json_parser or ClaudeJsonParser()
        self.markdown_formatter = markdown_formatter or ClaudeMessageFormatter()

    def convert_zip(self, zip_path: str) -> List[str]:
        """
        Convert Claude ZIP file to list of markdown strings.

        Args:
            zip_path: Path to Claude export ZIP file

        Returns:
            List of markdown-formatted conversation strings

        Raises:
            FileNotFoundError: If ZIP file doesn't exist
            ValueError: If ZIP is invalid or contains no conversations
        """
        zip_path = Path(zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        logger.info(f"Processing ZIP file: {zip_path}")

        markdowns = []

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Find all JSON files in ZIP
                json_files = [f for f in zf.namelist() if f.endswith('.json')]

                if not json_files:
                    logger.warning("No JSON files found in ZIP")
                    return markdowns

                logger.info(f"Found {len(json_files)} JSON files in ZIP")

                # Process each JSON file
                for json_file in json_files:
                    try:
                        # Extract and read JSON
                        with zf.open(json_file) as f:
                            json_data = f.read().decode('utf-8')

                        # Parse JSON to conversations
                        conversations = self.json_parser.parse_json(json_data)

                        # Convert each conversation to markdown
                        for conv in conversations:
                            try:
                                markdown = self.markdown_formatter.format_conversation(conv)
                                markdowns.append(markdown)
                            except Exception as e:
                                logger.error(f"Failed to format conversation: {e}")
                                continue

                    except Exception as e:
                        logger.error(f"Failed to process {json_file}: {e}")
                        continue

        except zipfile.BadZipFile as e:
            raise ValueError(f"Invalid ZIP file: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to process ZIP: {e}") from e

        logger.info(f"Converted {len(markdowns)} conversations to markdown")
        return markdowns

    def filter_by_date(
        self,
        markdowns: List[str],
        after: Optional[datetime] = None,
        before: Optional[datetime] = None
    ) -> List[str]:
        """
        Filter markdown conversations by date.

        Extracts the Created date from each markdown and filters by date range.

        Args:
            markdowns: List of markdown strings
            after: Include only conversations created after this datetime
            before: Include only conversations created before this datetime

        Returns:
            Filtered list of markdown strings
        """
        if not after and not before:
            return markdowns

        filtered = []

        for md in markdowns:
            # Extract Created date from markdown
            import re
            match = re.search(r'\*\*Created:\*\*\s+(.+)', md)
            if not match:
                logger.warning("Could not extract Created date from markdown")
                continue

            created_str = match.group(1).strip()

            try:
                # Parse ISO format datetime
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))

                # Apply filters
                if after and created_dt < after:
                    continue
                if before and created_dt > before:
                    continue

                filtered.append(md)

            except Exception as e:
                logger.warning(f"Failed to parse date '{created_str}': {e}")
                continue

        logger.info(f"Date filter: {len(markdowns)} -> {len(filtered)} conversations")
        return filtered
