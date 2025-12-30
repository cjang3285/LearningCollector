#!/usr/bin/env python3
"""
Exporter 인터페이스 (SOLID - DIP)

모든 Exporter는 이 인터페이스를 구현해야 함
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import date


class IExporter(ABC):
    """데이터 추출 인터페이스"""

    @abstractmethod
    def export(self, target_date: date, **options) -> List[Dict[str, Any]]:
        """
        데이터 추출

        Args:
            target_date: 대상 날짜
            **options: 추출 옵션 (exporter별로 다름)

        Returns:
            추출된 원본 데이터 리스트

        Raises:
            ExportError: 추출 실패 시
        """
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        추출된 데이터 유효성 검증

        Args:
            data: 추출된 데이터

        Returns:
            유효하면 True, 아니면 False
        """
        pass


class ExportError(Exception):
    """추출 에러"""
    pass
