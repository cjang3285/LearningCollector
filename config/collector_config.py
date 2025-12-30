#!/usr/bin/env python3
"""
Collector Configuration Manager - YAML 기반 설정 관리
Phase 6: 설정 기반 Collector 관리 (SOLID - OCP)

기능:
- YAML 설정 파일 로드
- 런타임 Collector 활성화/비활성화
- 설정 변경 감지 및 자동 리로드
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Optional, Any
import yaml
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CollectorConfig:
    """
    YAML 기반 Collector 설정 관리자

    사용 예시:
        config = CollectorConfig()
        enabled_collectors = config.get_enabled_collectors()
        config.set_enabled('github', True)  # 런타임 활성화
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: YAML 설정 파일 경로 (기본값: config/collectors.yaml)
        """
        if config_path is None:
            config_path = PROJECT_ROOT / 'config' / 'collectors.yaml'

        self.config_path = Path(config_path)
        self._config: Dict = {}
        self._last_modified: Optional[float] = None
        self._runtime_overrides: Dict[str, bool] = {}  # 런타임 활성화/비활성화 오버라이드

        # 초기 로드
        self.load()

    def load(self) -> None:
        """
        YAML 설정 파일 로드

        Raises:
            FileNotFoundError: 설정 파일이 없는 경우
            yaml.YAMLError: YAML 파싱 실패
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {self.config_path}")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}

            self._last_modified = self.config_path.stat().st_mtime
            logger.info(f"Collector 설정 로드: {self.config_path}")

        except yaml.YAMLError as e:
            logger.error(f"YAML 파싱 실패: {e}")
            raise
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise

    def reload_if_modified(self) -> bool:
        """
        설정 파일이 수정되었으면 자동 리로드

        Returns:
            리로드 여부
        """
        if not self.config_path.exists():
            return False

        current_mtime = self.config_path.stat().st_mtime
        if current_mtime > self._last_modified:
            logger.info("설정 파일 변경 감지, 리로드 중...")
            self.load()
            return True

        return False

    def get_all_collectors(self) -> Dict[str, Dict]:
        """
        모든 Collector 설정 반환

        Returns:
            {collector_name: config_dict}
        """
        return self._config.get('collectors', {})

    def get_collector_config(self, name: str) -> Optional[Dict]:
        """
        특정 Collector 설정 조회

        Args:
            name: Collector 이름

        Returns:
            Collector 설정 딕셔너리 또는 None
        """
        return self.get_all_collectors().get(name)

    def is_enabled(self, name: str) -> bool:
        """
        Collector 활성화 여부 확인

        Args:
            name: Collector 이름

        Returns:
            활성화 여부 (런타임 오버라이드 우선)
        """
        # 1. 런타임 오버라이드가 있으면 우선 적용
        if name in self._runtime_overrides:
            return self._runtime_overrides[name]

        # 2. YAML 설정 확인
        config = self.get_collector_config(name)
        if not config:
            return False

        # 3. 환경변수 기반 활성화 확인
        config_key = config.get('config_key')
        if config_key:
            # config/settings.py에서 환경변수 읽기
            from config.settings import COLLECT_GITHUB, COLLECT_BAEKJOON

            if config_key == 'COLLECT_GITHUB':
                return COLLECT_GITHUB
            elif config_key == 'COLLECT_BAEKJOON':
                return COLLECT_BAEKJOON

        # 4. 기본 enabled 값 반환
        return config.get('enabled', False)

    def get_enabled_collectors(self) -> Dict[str, Dict]:
        """
        활성화된 Collector들만 반환

        Returns:
            {collector_name: config_dict}
        """
        enabled = {}
        for name, config in self.get_all_collectors().items():
            if self.is_enabled(name):
                enabled[name] = config

        return enabled

    def get_sorted_collectors(self, enabled_only: bool = True) -> List[tuple]:
        """
        우선순위 순으로 정렬된 Collector 리스트 반환

        Args:
            enabled_only: 활성화된 것만 반환할지 여부

        Returns:
            [(collector_name, config_dict), ...] (우선순위 순)
        """
        collectors = self.get_enabled_collectors() if enabled_only else self.get_all_collectors()

        # priority 기준 정렬 (낮을수록 먼저)
        sorted_items = sorted(
            collectors.items(),
            key=lambda x: x[1].get('priority', 999)
        )

        return sorted_items

    def set_enabled(self, name: str, enabled: bool) -> None:
        """
        런타임에 Collector 활성화/비활성화 (오버라이드)

        Args:
            name: Collector 이름
            enabled: 활성화 여부
        """
        if name not in self.get_all_collectors():
            logger.warning(f"알 수 없는 Collector: {name}")
            return

        self._runtime_overrides[name] = enabled
        status = "활성화" if enabled else "비활성화"
        logger.info(f"[Runtime] {name} Collector {status}")

    def clear_overrides(self) -> None:
        """런타임 오버라이드 초기화"""
        self._runtime_overrides.clear()
        logger.info("런타임 오버라이드 초기화")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        전역 설정 조회

        Args:
            key: 설정 키
            default: 기본값

        Returns:
            설정 값
        """
        return self._config.get('settings', {}).get(key, default)

    def get_class_path(self, name: str) -> Optional[str]:
        """
        Collector의 클래스 경로 반환

        Args:
            name: Collector 이름

        Returns:
            클래스 경로 (예: "collectors.github_collector.GitHubCollector")
        """
        config = self.get_collector_config(name)
        return config.get('class_path') if config else None

    def get_available_collectors(self) -> List[str]:
        """
        사용 가능한 모든 Collector 이름 반환

        Returns:
            Collector 이름 리스트
        """
        return list(self.get_all_collectors().keys())

    def __repr__(self) -> str:
        enabled = list(self.get_enabled_collectors().keys())
        return f"CollectorConfig(enabled={enabled}, overrides={self._runtime_overrides})"


if __name__ == '__main__':
    # CollectorConfig 테스트
    print("=== CollectorConfig 테스트 ===\n")

    config = CollectorConfig()

    # 사용 가능한 Collector 목록
    print("사용 가능한 Collector:")
    for name in config.get_available_collectors():
        info = config.get_collector_config(name)
        enabled = "✓" if config.is_enabled(name) else "✗"
        print(f"  [{enabled}] {name}: {info['description']}")

    # 활성화된 Collector
    print("\n활성화된 Collector:")
    for name in config.get_enabled_collectors():
        print(f"  ✓ {name}")

    # 우선순위 순 정렬
    print("\n우선순위 순:")
    for name, cfg in config.get_sorted_collectors():
        print(f"  {cfg['priority']:2d}. {name}: {cfg['description']}")

    # 런타임 활성화
    print("\n런타임 활성화 테스트:")
    print(f"  github 활성화 전: {config.is_enabled('github')}")
    config.set_enabled('github', True)
    print(f"  github 활성화 후: {config.is_enabled('github')}")

    print(f"\n{config}")
