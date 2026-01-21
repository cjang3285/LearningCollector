#!/usr/bin/env python3
"""
LearningCollector - 메인 실행 파일

학습 자료 수집 및 블로그 포스팅 자동화 시스템
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# UI 모듈
from ui.env_setup_ui import show_env_setup_ui

# Core 모듈
from core.env_validator import validate_env
from core.startup_register import register_startup
from core.orchestrator import run_orchestrator


def main():
    """메인 실행 함수"""
    print("="*60)
    print("LearningCollector 시작")
    print("="*60)

    # 1. .env 파일 존재 여부 확인
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print("\n환경변수 파일(.env)이 존재하지 않습니다.")
        print("환경변수 설정 UI를 시작합니다...\n")

        # 환경변수 입력 UI 표시
        env_vars = show_env_setup_ui()

        if not env_vars:
            print("환경변수 설정이 취소되었습니다.")
            sys.exit(0)

    # 2. 환경변수 로드
    load_dotenv()
    print("\n환경변수 로드 완료")

    # 3. 환경변수 검증
    print("\n환경변수 검증 중...")
    is_valid = validate_env()

    if not is_valid:
        print("환경변수 검증 실패. 프로그램을 종료합니다.")
        sys.exit(1)

    print("환경변수 검증 완료")

    # 4. 시작프로그램 등록 (첫 실행 시 또는 필요 시)
    log_dir = Path(__file__).parent / "log"
    exec_log = log_dir / "exec_date.log"

    if not exec_log.exists():
        print("\n첫 실행 감지: 시작프로그램 등록 중...")
        success = register_startup()

        if success:
            print("시작프로그램 등록 완료 (매일 자정 실행)")
        else:
            print("경고: 시작프로그램 등록 실패")

    # 5. 메인 기능 실행
    print("\n메인 수집 작업 시작...\n")

    try:
        run_orchestrator()
        print("\n모든 작업이 완료되었습니다.")

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(0)

    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
