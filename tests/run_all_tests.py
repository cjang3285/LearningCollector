#!/usr/bin/env python3
"""
통합 테스트 러너

모든 테스트를 TestSuite로 통합하여 실행합니다.
"""

import sys
import unittest
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 각 테스트 모듈 import
from tests import (
    test_config,
    test_export,
    test_parse,
    test_storage,
    test_collectors,
    test_main,
    test_github
)


def create_test_suite():
    """
    전체 테스트 스위트 생성

    Returns:
        unittest.TestSuite: 모든 테스트를 포함한 테스트 스위트
    """
    # TestLoader 생성
    loader = unittest.TestLoader()

    # TestSuite 생성
    suite = unittest.TestSuite()

    # 각 모듈의 테스트 추가
    print("="*70)
    print("테스트 스위트 구성 중...")
    print("="*70)

    # 1. Config 테스트
    print("\n[1/7] Config 모듈 테스트 추가")
    suite.addTests(loader.loadTestsFromModule(test_config))

    # 2. Export 테스트
    print("[2/7] Export 모듈 테스트 추가")
    suite.addTests(loader.loadTestsFromModule(test_export))

    # 3. Parse 테스트
    print("[3/7] Parse 모듈 테스트 추가")
    suite.addTests(loader.loadTestsFromModule(test_parse))

    # 4. Storage 테스트
    print("[4/7] Storage 모듈 테스트 추가")
    suite.addTests(loader.loadTestsFromModule(test_storage))

    # 5. Collectors 테스트
    print("[5/7] Collectors 모듈 테스트 추가")
    suite.addTests(loader.loadTestsFromModule(test_collectors))

    # 6. Main 테스트
    print("[6/7] Main ETL 파이프라인 테스트 추가")
    suite.addTests(loader.loadTestsFromModule(test_main))

    # 7. GitHub 통합 테스트
    print("[7/7] GitHub 통합 테스트 추가")
    suite.addTests(loader.loadTestsFromModule(test_github))

    print("\n테스트 스위트 구성 완료!")
    print(f"총 테스트 케이스 수: {suite.countTestCases()}")

    return suite


def run_tests_with_runner(verbosity=2):
    """
    TestRunner로 테스트 실행

    Args:
        verbosity: 출력 상세 레벨 (0: 최소, 1: 기본, 2: 상세)

    Returns:
        unittest.TestResult: 테스트 결과
    """
    # TestSuite 생성
    suite = create_test_suite()

    # TextTestRunner 생성
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        descriptions=True,
        failfast=False  # 첫 실패에서 멈추지 않음
    )

    # 테스트 실행
    print("\n" + "="*70)
    print("테스트 실행 시작")
    print("="*70 + "\n")

    result = runner.run(suite)

    # 결과 요약
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)
    print(f"실행된 테스트: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"실패: {len(result.failures)}")
    print(f"에러: {len(result.errors)}")
    print(f"스킵: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n✓ 모든 테스트 통과!")
        return 0
    else:
        print("\n✗ 일부 테스트 실패")
        return 1


def run_specific_module(module_name, verbosity=2):
    """
    특정 모듈의 테스트만 실행

    Args:
        module_name: 테스트 모듈 이름 ('config', 'export', 'parse', etc.)
        verbosity: 출력 상세 레벨
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    module_map = {
        'config': test_config,
        'export': test_export,
        'parse': test_parse,
        'storage': test_storage,
        'collectors': test_collectors,
        'main': test_main,
        'github': test_github
    }

    if module_name not in module_map:
        print(f"❌ 잘못된 모듈 이름: {module_name}")
        print(f"사용 가능한 모듈: {', '.join(module_map.keys())}")
        return 1

    print(f"\n[{module_name.upper()}] 모듈 테스트만 실행")
    suite.addTests(loader.loadTestsFromModule(module_map[module_name]))

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Learning ETL 통합 테스트 러너')
    parser.add_argument(
        '-m', '--module',
        choices=['config', 'export', 'parse', 'storage', 'collectors', 'main', 'github'],
        help='특정 모듈만 테스트 (미지정 시 전체 테스트)'
    )
    parser.add_argument(
        '-v', '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='출력 상세 레벨 (0: 최소, 1: 기본, 2: 상세)'
    )

    args = parser.parse_args()

    # 특정 모듈 또는 전체 테스트 실행
    if args.module:
        exit_code = run_specific_module(args.module, args.verbosity)
    else:
        exit_code = run_tests_with_runner(args.verbosity)

    sys.exit(exit_code)
