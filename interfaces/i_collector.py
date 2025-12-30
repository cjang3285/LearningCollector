#!/usr/bin/env python3
"""
Collector 인터페이스 (SOLID - LSP, OCP)

모든 Collector는 이 인터페이스를 구현해야 함
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import date
from dataclasses import dataclass


@dataclass
class CollectionContext:
    """수집 컨텍스트 (수집 시 필요한 정보)"""
    target_date: date
    options: Dict[str, Any]  # collector별 옵션


@dataclass
class CollectionResult:
    """수집 결과"""
    success: bool
    date: date
    items_count: int
    artifact_ids: list
    metadata: Dict[str, Any]
    error: str = None


class ICollector(ABC):
    """데이터 수집 인터페이스 (워크플로우 조율)"""

    @abstractmethod
    def collect(self, context: CollectionContext) -> CollectionResult:
        """
        데이터 수집 실행

        Args:
            context: 수집 컨텍스트

        Returns:
            수집 결과

        Note:
            이 메서드는 Export → Parse → Save 워크플로우를 조율
        """
        pass

    @abstractmethod
    def should_run(self, context: CollectionContext) -> bool:
        """
        수집 실행 여부 판단

        Args:
            context: 수집 컨텍스트

        Returns:
            실행해야 하면 True, 아니면 False
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Collector 이름 반환

        Returns:
            Collector 이름 (예: "ai_chat", "github")
        """
        pass


class CollectionError(Exception):
    """수집 에러"""
    pass
