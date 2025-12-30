#!/usr/bin/env python3
"""
Saver 인터페이스 (SOLID - DIP)

모든 Saver는 이 인터페이스를 구현해야 함
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date


class ISaver(ABC):
    """데이터 저장 인터페이스"""

    @abstractmethod
    def save(self, data: Dict[str, Any], artifact_date: date) -> Optional[int]:
        """
        단일 데이터 저장

        Args:
            data: 저장할 데이터
            artifact_date: 아티팩트 날짜

        Returns:
            artifact_id (성공 시), None (중복/실패 시)

        Raises:
            SaveError: 저장 실패 시
        """
        pass

    @abstractmethod
    def save_all(self, data_list: List[Dict[str, Any]], artifact_date: date) -> List[int]:
        """
        여러 데이터 일괄 저장

        Args:
            data_list: 저장할 데이터 리스트
            artifact_date: 아티팩트 날짜

        Returns:
            성공한 artifact_id 리스트

        Raises:
            SaveError: 저장 실패 시
        """
        pass

    @abstractmethod
    def check_duplicate(self, data: Dict[str, Any]) -> bool:
        """
        중복 체크

        Args:
            data: 체크할 데이터

        Returns:
            중복이면 True, 아니면 False
        """
        pass


class SaveError(Exception):
    """저장 에러"""
    pass
