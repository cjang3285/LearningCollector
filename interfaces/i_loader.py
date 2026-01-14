#!/usr/bin/env python3
"""
Loader 인터페이스 (SOLID - DIP)

모든 Loader는 이 인터페이스를 구현해야 함
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import date


class ILoader(ABC):
    """데이터 로드 인터페이스"""

    @abstractmethod
    def load(self, target_date: date, **options) -> List[Dict[str, Any]]:
        """
        데이터 로드

        Args:
            target_date: 대상 날짜
            **options: 로드 옵션 (loader별로 다름)

        Returns:
            로드된 원본 데이터 리스트

        Raises:
            LoadError: 로드 실패 시
        """
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        로드된 데이터 유효성 검증

        Args:
            data: 로드된 데이터

        Returns:
            유효하면 True, 아니면 False
        """
        pass


class LoadError(Exception):
    """로드 에러"""
    pass
