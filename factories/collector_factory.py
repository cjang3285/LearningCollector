#!/usr/bin/env python3
"""
Collector Factory - Collector 인스턴스 생성 팩토리

OCP (Open/Closed Principle) 적용:
- 설정 기반으로 Collector 생성
- 새 Collector 추가 시 설정만 변경, 코드 수정 불필요
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Optional
import logging

from interfaces import ICollector
from collectors.github_collector import GitHubCollector
from collectors.baekjoon_collector import BaekjoonCollector
from collectors.ai_chat_collector import AIChatCollector
from migration.claude_collector import ClaudeMigrationCollector
from config.settings import COLLECT_GITHUB, COLLECT_BAEKJOON

logger = logging.getLogger(__name__)


class CollectorFactory:
    """
    Collector 생성 팩토리 (OCP 적용)

    새로운 Collector 추가 방법:
    1. COLLECTOR_REGISTRY에 등록
    2. 필요 시 config/settings.py에 활성화 플래그 추가
    3. 기존 코드는 수정 불필요!
    """

    # Collector 등록 레지스트리 (확장 포인트)
    COLLECTOR_REGISTRY = {
        'github': {
            'class': GitHubCollector,
            'enabled_by_default': False,
            'config_key': 'COLLECT_GITHUB',
            'description': 'GitHub 커밋 수집'
        },
        'baekjoon': {
            'class': BaekjoonCollector,
            'enabled_by_default': False,
            'config_key': 'COLLECT_BAEKJOON',
            'description': '백준 문제 풀이 수집'
        },
        'ai_chat': {
            'class': AIChatCollector,
            'enabled_by_default': True,  # 항상 활성화
            'config_key': None,
            'description': 'AI 채팅 마크다운 수집 (Claude, ChatGPT, Gemini)'
        },
        'claude_migration': {
            'class': ClaudeMigrationCollector,
            'enabled_by_default': False,  # 수동 실행만
            'config_key': None,
            'description': 'Claude ZIP 마이그레이션 (첫 이용 시)'
        }
    }

    @classmethod
    def create_collector(cls, collector_name: str) -> Optional[ICollector]:
        """
        단일 Collector 생성

        Args:
            collector_name: Collector 이름 ('github', 'baekjoon', 'ai_chat' 등)

        Returns:
            ICollector 인스턴스 또는 None
        """
        if collector_name not in cls.COLLECTOR_REGISTRY:
            logger.warning(f"알 수 없는 Collector: {collector_name}")
            return None

        config = cls.COLLECTOR_REGISTRY[collector_name]
        collector_class = config['class']

        try:
            return collector_class()
        except Exception as e:
            logger.error(f"{collector_name} Collector 생성 실패: {e}")
            return None

    @classmethod
    def create_all_collectors(
        cls,
        enabled_only: bool = True,
        exclude: Optional[List[str]] = None
    ) -> Dict[str, ICollector]:
        """
        모든 Collector 생성 (설정 기반)

        Args:
            enabled_only: 활성화된 Collector만 생성 (기본값: True)
            exclude: 제외할 Collector 이름 리스트

        Returns:
            {collector_name: ICollector} 딕셔너리
        """
        exclude = exclude or []
        collectors = {}

        for name, config in cls.COLLECTOR_REGISTRY.items():
            # 제외 리스트에 있으면 스킵
            if name in exclude:
                continue

            # enabled_only이고 활성화되지 않았으면 스킵
            if enabled_only and not cls._is_enabled(name, config):
                continue

            # Collector 생성
            collector = cls.create_collector(name)
            if collector:
                collectors[name] = collector
                logger.info(f"[Factory] {name} Collector 생성: {config['description']}")

        return collectors

    @classmethod
    def _is_enabled(cls, name: str, config: Dict) -> bool:
        """
        Collector 활성화 여부 확인

        Args:
            name: Collector 이름
            config: COLLECTOR_REGISTRY 설정

        Returns:
            활성화 여부
        """
        # 기본값으로 활성화된 경우
        if config['enabled_by_default']:
            return True

        # 설정 키가 있는 경우 환경변수 확인
        config_key = config.get('config_key')
        if config_key:
            # COLLECT_GITHUB, COLLECT_BAEKJOON 등의 값 확인
            if config_key == 'COLLECT_GITHUB':
                return COLLECT_GITHUB
            elif config_key == 'COLLECT_BAEKJOON':
                return COLLECT_BAEKJOON

        return False

    @classmethod
    def get_available_collectors(cls) -> List[str]:
        """
        사용 가능한 모든 Collector 이름 반환

        Returns:
            Collector 이름 리스트
        """
        return list(cls.COLLECTOR_REGISTRY.keys())

    @classmethod
    def get_collector_info(cls, collector_name: str) -> Optional[Dict]:
        """
        Collector 정보 조회

        Args:
            collector_name: Collector 이름

        Returns:
            Collector 설정 정보 또는 None
        """
        return cls.COLLECTOR_REGISTRY.get(collector_name)


if __name__ == '__main__':
    # Factory 테스트
    print("=== CollectorFactory 테스트 ===\n")

    # 사용 가능한 Collector 목록
    print("사용 가능한 Collector:")
    for name in CollectorFactory.get_available_collectors():
        info = CollectorFactory.get_collector_info(name)
        print(f"  - {name}: {info['description']}")

    print("\n활성화된 Collector 생성:")
    collectors = CollectorFactory.create_all_collectors(enabled_only=True)
    for name, collector in collectors.items():
        print(f"  ✓ {name}: {collector.get_name()}")

    print("\n단일 Collector 생성:")
    ai_chat = CollectorFactory.create_collector('ai_chat')
    if ai_chat:
        print(f"  ✓ ai_chat: {ai_chat.get_name()}")
