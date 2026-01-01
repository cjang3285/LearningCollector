#!/usr/bin/env python3
"""
Collector Factory - Collector 인스턴스 생성 팩토리
Phase 6: 설정 기반 Collector 관리 (SOLID - OCP)

기능:
- YAML 설정 파일 기반 Collector 생성
- 동적 클래스 로딩 (importlib)
- 런타임 활성화/비활성화
- 새 Collector 추가 시 코드 수정 불필요!
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Optional, Type
import logging
import importlib

from interfaces import ICollector
from config.collector_config import CollectorConfig

logger = logging.getLogger(__name__)


class CollectorFactory:
    """
    Collector 생성 팩토리 (Phase 6: 설정 기반)

    새로운 Collector 추가 방법:
    1. config/collectors.yaml에 collector 정의 추가
    2. enabled: true/false로 활성화 제어
    3. 기존 코드는 수정 불필요! ✨

    사용 예시:
        # 클래스 메서드 방식 (하위 호환성)
        collectors = CollectorFactory.create_all_collectors(enabled_only=True)

        # 인스턴스 방식 (새로운 방식, 설정 주입 가능)
        factory = CollectorFactory(custom_config)
        collectors = factory.create_all_collectors_instance(enabled_only=True)
    """

    # 싱글톤 기본 인스턴스 (클래스 메서드용)
    _default_instance: Optional['CollectorFactory'] = None

    def __init__(self, config: Optional[CollectorConfig] = None):
        """
        Args:
            config: CollectorConfig 인스턴스 (기본값: 자동 생성)
        """
        self.config = config or CollectorConfig()
        self._cache: Dict[str, Type[ICollector]] = {}  # 클래스 캐시

    @classmethod
    def _get_default_instance(cls) -> 'CollectorFactory':
        """기본 싱글톤 인스턴스 반환 (클래스 메서드용)"""
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    # ============================================
    # 내부 구현 메서드 (인스턴스 메서드)
    # ============================================

    def _import_collector_class(self, class_path: str) -> Optional[Type[ICollector]]:
        """
        클래스 경로에서 Collector 클래스 동적 임포트

        Args:
            class_path: 클래스 경로 (예: "collectors.github_collector.GitHubCollector")

        Returns:
            Collector 클래스 또는 None
        """
        # 캐시 확인
        if class_path in self._cache:
            return self._cache[class_path]

        try:
            # "collectors.github_collector.GitHubCollector" → 모듈, 클래스 분리
            module_path, class_name = class_path.rsplit('.', 1)

            # 모듈 임포트
            module = importlib.import_module(module_path)

            # 클래스 가져오기
            collector_class = getattr(module, class_name)

            # ICollector 인터페이스 구현 확인
            if not issubclass(collector_class, ICollector):
                logger.error(f"{class_path}는 ICollector를 구현하지 않습니다")
                return None

            # 캐시 저장
            self._cache[class_path] = collector_class
            return collector_class

        except (ImportError, AttributeError) as e:
            logger.error(f"클래스 임포트 실패 ({class_path}): {e}")
            return None
        except Exception as e:
            logger.error(f"예상치 못한 오류 ({class_path}): {e}")
            return None

    def _import_class_by_path(self, class_path: str):
        """
        Import any class by full path 'module.submodule.ClassName'. Returns the class or None.
        """
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception as e:
            logger.error(f"클래스 임포트 실패 ({class_path}): {e}")
            return None

    def _create_collector_impl(self, collector_name: str) -> Optional[ICollector]:
        """
        [내부] 단일 Collector 생성 구현

        Args:
            collector_name: Collector 이름 ('github', 'baekjoon', 'ai_chat' 등)

        Returns:
            ICollector 인스턴스 또는 None
        """
        # 설정 조회
        collector_config = self.config.get_collector_config(collector_name)
        if not collector_config:
            logger.warning(f"알 수 없는 Collector: {collector_name}")
            return None

        # 클래스 경로 가져오기
        class_path = collector_config.get('class_path')
        if not class_path:
            logger.error(f"{collector_name}: class_path가 설정되지 않았습니다")
            return None

        # 클래스 임포트
        collector_class = self._import_collector_class(class_path)
        if not collector_class:
            return None
        # 구성에서 dependencies 매핑이 있으면 인스턴스화하여 생성자에 주입
        dependencies_cfg = collector_config.get('dependencies', {}) or {}
        init_kwargs = {}

        for param_name, dep_class_path in dependencies_cfg.items():
            dep_class = self._import_class_by_path(dep_class_path)
            if not dep_class:
                logger.warning(f"{collector_name}: dependency import 실패: {dep_class_path}")
                continue
            try:
                init_kwargs[param_name] = dep_class()
            except Exception as e:
                logger.error(f"{collector_name}: dependency 인스턴스화 실패: {dep_class_path}: {e}")

        # 인스턴스 생성 (의존성 주입 시도)
        try:
            if init_kwargs:
                return collector_class(**init_kwargs)
            return collector_class()
        except Exception as e:
            logger.error(f"{collector_name} Collector 생성 실패: {e}")
            return None

    def _create_all_collectors_impl(
        self,
        enabled_only: bool = True,
        exclude: Optional[List[str]] = None,
        sort_by_priority: bool = True
    ) -> Dict[str, ICollector]:
        """
        [내부] 모든 Collector 생성 구현

        Args:
            enabled_only: 활성화된 Collector만 생성 (기본값: True)
            exclude: 제외할 Collector 이름 리스트
            sort_by_priority: 우선순위 순으로 정렬 (기본값: True)

        Returns:
            {collector_name: ICollector} 딕셔너리 (우선순위 순)
        """
        exclude = exclude or []
        collectors = {}

        # 우선순위 순 정렬이 활성화되면 sorted_collectors 사용
        if sort_by_priority:
            collector_items = self.config.get_sorted_collectors(enabled_only=enabled_only)
        else:
            # 활성화 여부에 따라 필터링
            if enabled_only:
                all_configs = self.config.get_enabled_collectors()
            else:
                all_configs = self.config.get_all_collectors()
            collector_items = list(all_configs.items())

        for name, config in collector_items:
            # 제외 리스트에 있으면 스킵
            if name in exclude:
                logger.debug(f"[Factory] {name} Collector 제외됨")
                continue

            # Collector 생성
            collector = self._create_collector_impl(name)
            if collector:
                collectors[name] = collector
                logger.info(f"[Factory] {name} Collector 생성: {config['description']}")

        return collectors

    def _set_enabled_impl(self, collector_name: str, enabled: bool) -> None:
        """
        [내부] 런타임에 Collector 활성화/비활성화

        Args:
            collector_name: Collector 이름
            enabled: 활성화 여부
        """
        self.config.set_enabled(collector_name, enabled)

    def _reload_config_impl(self) -> None:
        """[내부] 설정 파일 리로드"""
        self.config.load()
        self._cache.clear()  # 클래스 캐시 초기화
        logger.info("[Factory] 설정 리로드 완료")

    def _get_available_collectors_impl(self) -> List[str]:
        """
        [내부] 사용 가능한 모든 Collector 이름 반환

        Returns:
            Collector 이름 리스트
        """
        return self.config.get_available_collectors()

    def _get_collector_info_impl(self, collector_name: str) -> Optional[Dict]:
        """
        [내부] Collector 정보 조회

        Args:
            collector_name: Collector 이름

        Returns:
            Collector 설정 정보 또는 None
        """
        return self.config.get_collector_config(collector_name)

    def _is_enabled_impl(self, collector_name: str) -> bool:
        """
        [내부] Collector 활성화 여부 확인

        Args:
            collector_name: Collector 이름

        Returns:
            활성화 여부
        """
        return self.config.is_enabled(collector_name)

    # ============================================
    # 클래스 메서드 래퍼 (하위 호환성)
    # ============================================

    @classmethod
    def create_collector(cls, collector_name: str) -> Optional[ICollector]:
        """
        [클래스 메서드] 단일 Collector 생성 (하위 호환성)

        Args:
            collector_name: Collector 이름

        Returns:
            ICollector 인스턴스 또는 None
        """
        instance = cls._get_default_instance()
        return instance._create_collector_impl(collector_name)

    @classmethod
    def create_all_collectors(
        cls,
        enabled_only: bool = True,
        exclude: Optional[List[str]] = None,
        sort_by_priority: bool = True
    ) -> Dict[str, ICollector]:
        """
        [클래스 메서드] 모든 Collector 생성 (하위 호환성)

        Args:
            enabled_only: 활성화된 Collector만 생성
            exclude: 제외할 Collector 이름 리스트
            sort_by_priority: 우선순위 순으로 정렬

        Returns:
            {collector_name: ICollector} 딕셔너리
        """
        instance = cls._get_default_instance()
        return instance._create_all_collectors_impl(enabled_only, exclude, sort_by_priority)

    @classmethod
    def get_available_collectors(cls) -> List[str]:
        """
        [클래스 메서드] 사용 가능한 모든 Collector 이름 반환 (하위 호환성)

        Returns:
            Collector 이름 리스트
        """
        instance = cls._get_default_instance()
        return instance._get_available_collectors_impl()

    @classmethod
    def get_collector_info(cls, collector_name: str) -> Optional[Dict]:
        """
        [클래스 메서드] Collector 정보 조회 (하위 호환성)

        Args:
            collector_name: Collector 이름

        Returns:
            Collector 설정 정보 또는 None
        """
        instance = cls._get_default_instance()
        return instance._get_collector_info_impl(collector_name)


if __name__ == '__main__':
    # Factory 테스트
    print("=== CollectorFactory 테스트 ===\n")

    # 클래스 메서드 방식 테스트 (하위 호환성)
    print("[클래스 메서드 방식]")
    print("사용 가능한 Collector:")
    for name in CollectorFactory.get_available_collectors():
        info = CollectorFactory.get_collector_info(name)
        enabled = "✓" if info.get('enabled', False) else "✗"
        priority = info.get('priority', 999)
        print(f"  [{enabled}] {name} (우선순위: {priority}): {info['description']}")

    print("\n활성화된 Collector 생성:")
    collectors = CollectorFactory.create_all_collectors(enabled_only=True)
    for name, collector in collectors.items():
        print(f"  ✓ {name}: {collector.get_name()}")

    print("\n단일 Collector 생성:")
    ai_chat = CollectorFactory.create_collector('ai_chat')
    if ai_chat:
        print(f"  ✓ ai_chat: {ai_chat.get_name()}")

    # 인스턴스 방식 테스트 (새로운 방식)
    print("\n\n[인스턴스 방식]")
    factory = CollectorFactory()

    print("런타임 활성화 테스트:")
    print(f"  github 활성화 전: {factory._is_enabled_impl('github')}")
    factory._set_enabled_impl('github', True)
    print(f"  github 활성화 후: {factory._is_enabled_impl('github')}")

    github_collector = factory._create_collector_impl('github')
    if github_collector:
        print(f"  ✓ github collector 생성 성공: {github_collector.get_name()}")
