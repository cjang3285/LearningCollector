#!/usr/bin/env python3
"""
기본 기능 테스트

실제 환경에서 각 모듈이 정상적으로 임포트되고 초기화되는지 확인합니다.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """모든 주요 모듈 임포트 테스트"""
    print("="*70)
    print("모듈 임포트 테스트")
    print("="*70)

    try:
        print("\n[1/6] Config 모듈 임포트...")
        from config import settings
        print(f"  ✓ PROJECT_ROOT: {settings.PROJECT_ROOT}")
        print(f"  ✓ GITHUB_USERNAME: {settings.GITHUB_USERNAME}")
        print(f"  ✓ BAEKJOON_HANDLE: {settings.BAEKJOON_HANDLE}")
    except Exception as e:
        print(f"  ✗ 실패: {e}")
        return False

    try:
        print("\n[2/6] Export 모듈 임포트...")
        from export.github_export import GitHubExporter
        from export.baekjoon_export import BaekjoonExporter
        print("  ✓ GitHubExporter")
        print("  ✓ BaekjoonExporter")
    except Exception as e:
        print(f"  ✗ 실패: {e}")
        return False

    try:
        print("\n[3/6] Parse 모듈 임포트...")
        from parse.github_parse import GitHubParser
        from parse.claude_parse import ClaudeParser
        from parse.baekjoon_parse import BaekjoonParser
        print("  ✓ GitHubParser")
        print("  ✓ ClaudeParser")
        print("  ✓ BaekjoonParser")
    except Exception as e:
        print(f"  ✗ 실패: {e}")
        return False

    try:
        print("\n[4/6] Storage 모듈 임포트...")
        from storage.base_saver import BaseSaver
        from storage.github_saver import GitHubSaver
        from storage.claude_saver import ClaudeSaver
        from storage.baekjoon_saver import BaekjoonSaver
        from storage.artifact_saver import ArtifactSaver
        print("  ✓ BaseSaver")
        print("  ✓ GitHubSaver")
        print("  ✓ ClaudeSaver")
        print("  ✓ BaekjoonSaver")
        print("  ✓ ArtifactSaver")
    except Exception as e:
        print(f"  ✗ 실패: {e}")
        return False

    try:
        print("\n[5/6] Collectors 모듈 임포트...")
        from collectors.github_collector import GitHubCollector
        from collectors.claude_collector import ClaudeCollector
        from collectors.baekjoon_collector import BaekjoonCollector
        print("  ✓ GitHubCollector")
        print("  ✓ ClaudeCollector")
        print("  ✓ BaekjoonCollector")
    except Exception as e:
        print(f"  ✗ 실패: {e}")
        return False

    try:
        print("\n[6/6] Main 모듈 임포트...")
        from main import LearningETL
        print("  ✓ LearningETL")
    except Exception as e:
        print(f"  ✗ 실패: {e}")
        return False

    print("\n" + "="*70)
    print("✓ 모든 모듈 임포트 성공!")
    print("="*70)
    return True


def test_basic_initialization():
    """기본 클래스 초기화 테스트"""
    print("\n" + "="*70)
    print("기본 초기화 테스트")
    print("="*70)

    try:
        print("\n[1/3] Parser 초기화...")
        from parse.github_parse import GitHubParser
        parser = GitHubParser()
        print("  ✓ GitHubParser 초기화 성공")

        from parse.claude_parse import ClaudeParser
        claude_parser = ClaudeParser()
        print("  ✓ ClaudeParser 초기화 성공")

        from parse.baekjoon_parse import BaekjoonParser
        boj_parser = BaekjoonParser()
        print("  ✓ BaekjoonParser 초기화 성공")
    except Exception as e:
        print(f"  ✗ Parser 초기화 실패: {e}")
        return False

    try:
        print("\n[2/3] Saver 초기화...")
        from storage.base_saver import BaseSaver
        saver = BaseSaver()
        print("  ✓ BaseSaver 초기화 성공")

        from storage.artifact_saver import ArtifactSaver
        artifact_saver = ArtifactSaver()
        print("  ✓ ArtifactSaver 초기화 성공")
    except Exception as e:
        print(f"  ✗ Saver 초기화 실패: {e}")
        return False

    try:
        print("\n[3/3] Collector 초기화...")
        from collectors.claude_collector import ClaudeCollector
        collector = ClaudeCollector()
        print("  ✓ ClaudeCollector 초기화 성공")
    except Exception as e:
        print(f"  ✗ Collector 초기화 실패: {e}")
        return False

    print("\n" + "="*70)
    print("✓ 모든 클래스 초기화 성공!")
    print("="*70)
    return True


def test_directory_structure():
    """디렉토리 구조 확인"""
    print("\n" + "="*70)
    print("디렉토리 구조 확인")
    print("="*70)

    from config import settings

    dirs_to_check = {
        'TEMP_DIR': settings.TEMP_DIR,
        'LOGS_DIR': settings.LOGS_DIR,
        'ARTIFACTS_DIR': settings.ARTIFACTS_DIR,
        'CLAUDE_DOWNLOAD_DIR': settings.CLAUDE_DOWNLOAD_DIR,
    }

    all_ok = True
    for name, path in dirs_to_check.items():
        if path.exists():
            print(f"  ✓ {name}: {path}")
        else:
            print(f"  ✗ {name}: {path} (존재하지 않음)")
            all_ok = False

    if all_ok:
        print("\n✓ 모든 필수 디렉토리 존재")
    else:
        print("\n✗ 일부 디렉토리 누락")

    return all_ok


def test_config_validation():
    """설정 검증"""
    print("\n" + "="*70)
    print("설정 검증")
    print("="*70)

    from config import settings

    print(f"\n환경변수 상태:")
    print(f"  GITHUB_TOKEN: {'설정됨' if settings.GITHUB_TOKEN else '미설정'}")
    print(f"  GITHUB_USERNAME: {settings.GITHUB_USERNAME}")
    print(f"  BAEKJOON_HANDLE: {settings.BAEKJOON_HANDLE}")
    print(f"  DB_HOST: {settings.DB_HOST}")
    print(f"  DB_NAME: {settings.DB_NAME}")

    print(f"\n수집 활성화 상태:")
    print(f"  COLLECT_GITHUB: {settings.COLLECT_GITHUB}")
    print(f"  COLLECT_CLAUDE: {settings.COLLECT_CLAUDE}")
    print(f"  COLLECT_BAEKJOON: {settings.COLLECT_BAEKJOON}")

    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("Learning ETL 기본 기능 테스트")
    print("="*70)

    results = []

    # 1. 임포트 테스트
    results.append(("모듈 임포트", test_imports()))

    # 2. 초기화 테스트
    results.append(("기본 초기화", test_basic_initialization()))

    # 3. 디렉토리 구조
    results.append(("디렉토리 구조", test_directory_structure()))

    # 4. 설정 검증
    results.append(("설정 검증", test_config_validation()))

    # 결과 요약
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)

    for name, result in results:
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{status}: {name}")

    all_passed = all(r for _, r in results)

    print("\n" + "="*70)
    if all_passed:
        print("✓ 모든 기본 기능 테스트 통과!")
        print("="*70)
        sys.exit(0)
    else:
        print("✗ 일부 테스트 실패")
        print("="*70)
        sys.exit(1)
