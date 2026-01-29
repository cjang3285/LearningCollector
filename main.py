#!/usr/bin/env python3
"""
LearningCollector - 메인 실행 파일

학습 자료 수집 및 블로그 포스팅 자동화 시스템
"""
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
import getpass

# Core 모듈
from core.env_validator import validate_env
from core.startup_register import register_startup
from core.orchestrator import run_orchestrator


def setup_env_cli():
    """CLI로 환경변수 입력받아 .env 파일 생성"""
    print("\n환경변수 설정을 시작합니다.")
    print("=" * 60)

    env_vars = {}

    # Module 1: 인증 정보
    print("\n[Module 1: 인증 정보]")
    env_vars["GITHUB_TOKEN"] = getpass.getpass("GITHUB_TOKEN: ")
    env_vars["GEMINI_API_KEY"] = getpass.getpass("GEMINI_API_KEY: ")

    # Module 2: 감시
    print("\n[Module 2: 감시]")
    env_vars["AI_CHAT_DOWNLOAD_DIR"] = input("AI_CHAT_DOWNLOAD_DIR (다운로드 폴더 경로): ").strip()
    log_path = input("LOG_FILE_PATH (기본값: ./log/err.log): ").strip()
    env_vars["LOG_FILE_PATH"] = log_path if log_path else "./log/err.log"

    # Module 3: 필터링 및 환경 설정
    print("\n[Module 3: 필터링 및 환경 설정]")
    env_vars["GITHUB_USERNAME"] = input("GITHUB_USERNAME: ").strip()
    editor = input("EDITOR_COMMAND (기본값: code): ").strip()
    env_vars["EDITOR_COMMAND"] = editor if editor else "code"

    # .env 파일 저장
    env_path = Path(__file__).parent / ".env"
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        print("\n✓ .env 파일이 생성되었습니다.")
        return True

    except Exception as e:
        print(f"\n✗ .env 파일 생성 실패: {str(e)}")
        return False


def main():
    """메인 실행 함수"""
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description="LearningCollector - 학습 자료 수집 및 블로그 포스팅 자동화")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="자동 모드 (모든 레포/브랜치 자동 조회, cron job용)"
    )
    args = parser.parse_args()

    print("="*60)
    print("LearningCollector 시작")
    if args.auto:
        print("(Auto 모드: 모든 레포/브랜치 자동 조회)")
    else:
        print("(Interactive 모드: 레포/브랜치 선택)")
    print("="*60)

    # 1. .env 파일 존재 여부 확인
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print("\n환경변수 파일(.env)이 존재하지 않습니다.")

        # CLI로 환경변수 입력
        success = setup_env_cli()

        if not success:
            print("환경변수 설정이 실패했습니다.")
            sys.exit(1)

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
        run_orchestrator(auto=args.auto)
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
