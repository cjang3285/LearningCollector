#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 시작프로그램에 쿠키 자동 추출 등록
"""

import os
import sys
from pathlib import Path
import winshell
from win32com.client import Dispatch

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def create_startup_shortcut():
    """시작프로그램에 바로가기 생성"""

    # 경로 설정
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    python_script = project_root / 'tools' / 'extract_cookies_playwright.py'

    # Python 실행 파일 찾기 (pythonw.exe - 콘솔 창 없이 실행)
    python_exe = Path(sys.executable).parent / 'pythonw.exe'
    if not python_exe.exists():
        python_exe = Path(sys.executable)  # python.exe 사용

    # 시작프로그램 폴더
    startup_folder = Path(winshell.startup())
    shortcut_path = startup_folder / 'Claude_Cookie_Extractor.lnk'

    print("=" * 60)
    print("Claude 쿠키 자동 추출 - 시작프로그램 등록")
    print("=" * 60)
    print()
    print(f"프로젝트: {project_root}")
    print(f"Python: {python_exe}")
    print(f"스크립트: {python_script}")
    print(f"바로가기: {shortcut_path}")
    print()

    # 바로가기 생성
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(python_exe)
    shortcut.Arguments = f'"{python_script}" --upload'
    shortcut.WorkingDirectory = str(project_root)
    shortcut.Description = 'Claude.ai 쿠키 자동 추출 및 Raspberry Pi 업로드'
    shortcut.IconLocation = str(python_exe)
    shortcut.WindowStyle = 7  # 최소화
    shortcut.save()

    print("✅ 등록 완료!")
    print()
    print("Windows 부팅 시 자동으로 실행됩니다.")
    print("브라우저가 잠깐 열렸다 닫히면 정상입니다.")
    print()
    print("제거하려면:")
    print(f"  {shortcut_path}")
    print("  파일을 삭제하세요.")
    print()

def remove_startup_shortcut():
    """시작프로그램에서 제거"""
    startup_folder = Path(winshell.startup())
    shortcut_path = startup_folder / 'Claude_Cookie_Extractor.lnk'

    if shortcut_path.exists():
        shortcut_path.unlink()
        print("✅ 시작프로그램에서 제거되었습니다.")
    else:
        print("⚠️  등록된 바로가기가 없습니다.")

if __name__ == '__main__':
    if '--remove' in sys.argv:
        remove_startup_shortcut()
    else:
        try:
            create_startup_shortcut()
        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            print()
            print("필요한 라이브러리 설치:")
            print("  pip install pywin32 winshell")
            sys.exit(1)
