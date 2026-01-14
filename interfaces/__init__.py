"""
SOLID 원칙 기반 인터페이스 정의

- IParser: 파싱 인터페이스
- ISaver: 저장 인터페이스
- ICollector: 수집 인터페이스 (워크플로우 조율)
- ILoader: 로드 인터페이스
"""

from .i_parser import IParser, ParseError
from .i_saver import ISaver, SaveError
from .i_collector import (
    ICollector,
    CollectionContext,
    CollectionResult,
    CollectionError
)
from .i_loader import ILoader, LoadError

__all__ = [
    'IParser',
    'ISaver',
    'ICollector',
    'ILoader',
    'CollectionContext',
    'CollectionResult',
    'ParseError',
    'SaveError',
    'CollectionError',
    'LoadError',
]
