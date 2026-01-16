#!/usr/bin/env python3
"""전체 테스트 실행 스크립트"""

import sys
import subprocess
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_tests():
    """모든 테스트 실행"""
    print("=" * 80)
    print("LearningCollector 테스트 실행")
    print("=" * 80)
    print()

    # pytest 옵션
    # -v: verbose (상세 출력)
    # -s: stdout/stderr 출력 표시
    # --tb=short: traceback을 짧게 표시
    # --color=yes: 컬러 출력
    cmd = [
        'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--color=yes',
        '--strict-markers'
    ]

    print(f"실행 명령: {' '.join(cmd)}")
    print()

    # 테스트 실행
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    # 결과 코드 반환
    return result.returncode


def run_specific_test(test_file):
    """특정 테스트 파일 실행"""
    print(f"테스트 실행: {test_file}")
    print()

    cmd = [
        'pytest',
        f'tests/{test_file}',
        '-v',
        '--tb=short',
        '--color=yes'
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def run_coverage():
    """코드 커버리지 리포트 생성"""
    print("=" * 80)
    print("코드 커버리지 분석")
    print("=" * 80)
    print()

    cmd = [
        'pytest',
        'tests/',
        '--cov=.',
        '--cov-report=html',
        '--cov-report=term'
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 특정 테스트 파일 실행
        test_file = sys.argv[1]

        if test_file == '--coverage':
            # 커버리지 분석
            exit_code = run_coverage()
        else:
            # 특정 파일 테스트
            exit_code = run_specific_test(test_file)
    else:
        # 전체 테스트 실행
        exit_code = run_tests()

    # 종료 코드 반환
    sys.exit(exit_code)
