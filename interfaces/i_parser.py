#!/usr/bin/env python3
"""
Parser 인터페이스 (SOLID - DIP)

모든 Parser는 이 인터페이스를 구현해야 함
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path


class IParser(ABC):
    """데이터 파싱 인터페이스"""

    @abstractmethod
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        단일 파일 파싱

        Args:
            file_path: 파일 경로

        Returns:
            파싱된 데이터 (딕셔너리)

        Raises:
            ParseError: 파싱 실패 시
        """
        pass

    @abstractmethod
    def parse_multiple(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        여러 파일 일괄 파싱

        Args:
            file_paths: 파일 경로 리스트

        Returns:
            파싱된 데이터 리스트

        Raises:
            ParseError: 파싱 실패 시
        """
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        파싱된 데이터 유효성 검증

        Args:
            data: 파싱된 데이터

        Returns:
            유효하면 True, 아니면 False
        """
        pass


class ParseError(Exception):
    """파싱 에러"""
    pass
