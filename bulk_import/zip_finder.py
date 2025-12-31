#!/usr/bin/env python3
"""
Claude ZIP file finder.

Automatically locates Claude export ZIP files in common directories.
"""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ClaudeZipFinder:
    """
    Finds Claude export ZIP files in specified directories.
    """

    DEFAULT_SEARCH_DIRS = [
        "~/Downloads",
        "../shared",  # 라즈베리파이의 공유 폴더
        ".",
    ]

    def __init__(self, search_dirs: Optional[List[str]] = None):
        """
        Initialize ZIP finder.

        Args:
            search_dirs: List of directories to search (defaults to DEFAULT_SEARCH_DIRS)
        """
        self.search_dirs = search_dirs or self.DEFAULT_SEARCH_DIRS

    def find_latest_zip(self) -> Optional[Path]:
        """
        Find the most recent Claude ZIP file.

        Returns:
            Path to latest ZIP file, or None if not found
        """
        all_zips = self.find_all_zips()

        if not all_zips:
            return None

        # Sort by modification time (most recent first)
        all_zips.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        latest = all_zips[0]
        logger.info(f"Found latest ZIP: {latest}")
        return latest

    def find_all_zips(self) -> List[Path]:
        """
        Find all Claude ZIP files in search directories.

        Returns:
            List of ZIP file paths
        """
        found_zips = []

        for search_dir in self.search_dirs:
            # Expand user home directory
            dir_path = Path(search_dir).expanduser()

            if not dir_path.exists():
                logger.debug(f"Search directory does not exist: {dir_path}")
                continue

            # Find ZIP files that match Claude export naming pattern
            # Pattern: data-YYYY-MM-DD-HH-MM-SS-batch-NNNN.zip
            for zip_file in dir_path.glob("*.zip"):
                # Check if it's a Claude export (contains "data-" or "claude" in name)
                if "data-" in zip_file.name.lower() or "claude" in zip_file.name.lower():
                    found_zips.append(zip_file)
                    logger.debug(f"Found ZIP: {zip_file}")

        logger.info(f"Found {len(found_zips)} Claude ZIP files")
        return found_zips

    def find_by_date(self, target_date: datetime) -> Optional[Path]:
        """
        Find ZIP file created on specific date.

        Args:
            target_date: Target date

        Returns:
            Path to ZIP file, or None if not found
        """
        all_zips = self.find_all_zips()

        target_date_str = target_date.strftime("%Y-%m-%d")

        for zip_file in all_zips:
            # Check if filename contains the date
            if target_date_str in zip_file.name:
                logger.info(f"Found ZIP for date {target_date_str}: {zip_file}")
                return zip_file

        logger.warning(f"No ZIP file found for date {target_date_str}")
        return None


if __name__ == '__main__':
    import sys

    # Test ZIP finder
    finder = ClaudeZipFinder()

    print("\nAll Claude ZIP files:")
    for zip_file in finder.find_all_zips():
        print(f"  - {zip_file}")

    print("\nLatest ZIP file:")
    latest = finder.find_latest_zip()
    if latest:
        print(f"  {latest}")
    else:
        print("  None found")
