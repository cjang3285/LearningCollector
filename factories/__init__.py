"""
Factories - 객체 생성 팩토리

OCP (Open/Closed Principle) 적용:
- 새로운 Collector 추가 시 설정만 변경
- 기존 코드 수정 불필요
"""

from .collector_factory import CollectorFactory

__all__ = ['CollectorFactory']
