@echo off
REM Windows 시작프로그램에 쿠키 자동 추출 등록
REM 이 스크립트를 실행하면 Windows 부팅 시 자동으로 쿠키를 추출합니다

echo ================================================
echo Claude 쿠키 자동 추출 - 시작프로그램 등록
echo ================================================
echo.

REM 현재 디렉토리 확인
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo 프로젝트 경로: %PROJECT_ROOT%
echo 시작프로그램 폴더: %STARTUP_DIR%
echo.

REM VBScript를 사용해서 바로가기 생성 (숨김 창으로 실행)
set SHORTCUT_PATH=%STARTUP_DIR%\Claude_Cookie_Extractor.lnk
set PYTHON_SCRIPT=%PROJECT_ROOT%\tools\extract_cookies_playwright.py
set PYTHON_EXE=pythonw.exe

echo 바로가기 생성 중...
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = "%SHORTCUT_PATH%" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "%PYTHON_EXE%" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Arguments = """%PYTHON_SCRIPT%"" --upload" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "%PROJECT_ROOT%" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Description = "Claude.ai 쿠키 자동 추출 및 업로드" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WindowStyle = 7 >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"

cscript //nologo "%TEMP%\CreateShortcut.vbs"
del "%TEMP%\CreateShortcut.vbs"

echo.
echo ================================================
echo 등록 완료!
echo ================================================
echo.
echo 위치: %SHORTCUT_PATH%
echo.
echo Windows 부팅 시 자동으로 실행됩니다.
echo 브라우저가 잠깐 열렸다 닫히면 정상입니다.
echo.
echo 제거하려면: %STARTUP_DIR% 폴더에서
echo             Claude_Cookie_Extractor.lnk 파일을 삭제하세요.
echo.
pause
