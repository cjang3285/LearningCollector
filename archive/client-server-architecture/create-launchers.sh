#!/bin/bash
# ========================================
# LearningETL 실행 파일 생성 스크립트
# ========================================
#
# Windows .bat, macOS .command, Linux .sh 파일 생성
# 더블클릭으로 실행 가능!
#
# 사용법:
# bash scripts/create-launchers.sh
# ========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "LearningETL 실행 파일 생성"
echo "=========================================="
echo ""

cd "$PROJECT_ROOT"

# ========================================
# 1. Windows 실행 파일 (.bat)
# ========================================

echo "1. Windows 실행 파일 생성 중..."

# 서버 시작 (라즈베리파이용)
cat > "Start-Server.bat" << 'WINEOF'
@echo off
title LearningETL Server
cd /d "%~dp0"

echo ========================================
echo LearningETL Server Starting...
echo ========================================
echo.

REM 가상환경 활성화
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] venv not found! Run: python -m venv venv
    pause
    exit /b 1
)

REM 서버 시작
python server\api.py

pause
WINEOF

# 클라이언트 시작 (노트북용)
cat > "Start-Client.bat" << 'WINEOF'
@echo off
title LearningETL Client
cd /d "%~dp0"

echo ========================================
echo LearningETL Client Starting...
echo ========================================
echo.

REM 가상환경 활성화
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] venv not found! Run: python -m venv venv
    pause
    exit /b 1
)

REM 클라이언트 시작
python client\agent.py

pause
WINEOF

# Standalone 모드 (단일 머신)
cat > "Start-Standalone.bat" << 'WINEOF'
@echo off
title LearningETL Standalone
cd /d "%~dp0"

echo ========================================
echo LearningETL Standalone Mode
echo ========================================
echo.

REM 가상환경 활성화
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] venv not found! Run: python -m venv venv
    pause
    exit /b 1
)

REM main.py 실행
python main.py

pause
WINEOF

echo "✓ Windows .bat 파일 생성 완료"

# ========================================
# 2. macOS 실행 파일 (.command)
# ========================================

echo "2. macOS 실행 파일 생성 중..."

# 서버 시작
cat > "Start-Server.command" << 'MACEOF'
#!/bin/bash
# LearningETL Server (macOS)

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

echo "========================================"
echo "LearningETL Server Starting..."
echo "========================================"
echo ""

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[ERROR] venv not found! Run: python3 -m venv venv"
    read -p "Press any key to exit..."
    exit 1
fi

# 서버 시작
python server/api.py

read -p "Press any key to exit..."
MACEOF

# 클라이언트 시작
cat > "Start-Client.command" << 'MACEOF'
#!/bin/bash
# LearningETL Client (macOS)

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

echo "========================================"
echo "LearningETL Client Starting..."
echo "========================================"
echo ""

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[ERROR] venv not found! Run: python3 -m venv venv"
    read -p "Press any key to exit..."
    exit 1
fi

# 클라이언트 시작
python client/agent.py

read -p "Press any key to exit..."
MACEOF

# Standalone 모드
cat > "Start-Standalone.command" << 'MACEOF'
#!/bin/bash
# LearningETL Standalone (macOS)

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

echo "========================================"
echo "LearningETL Standalone Mode"
echo "========================================"
echo ""

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[ERROR] venv not found! Run: python3 -m venv venv"
    read -p "Press any key to exit..."
    exit 1
fi

# main.py 실행
python main.py

read -p "Press any key to exit..."
MACEOF

# 실행 권한 부여
chmod +x Start-Server.command
chmod +x Start-Client.command
chmod +x Start-Standalone.command

echo "✓ macOS .command 파일 생성 완료"

# ========================================
# 3. Linux 실행 파일 (.sh)
# ========================================

echo "3. Linux 실행 파일 생성 중..."

# 서버 시작
cat > "start-server.sh" << 'LINUXEOF'
#!/bin/bash
# LearningETL Server (Linux)

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

echo "========================================"
echo "LearningETL Server Starting..."
echo "========================================"
echo ""

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[ERROR] venv not found! Run: python3 -m venv venv"
    read -p "Press any key to exit..."
    exit 1
fi

# 서버 시작
python server/api.py

echo ""
echo "Server stopped."
read -p "Press any key to exit..."
LINUXEOF

# 클라이언트 시작
cat > "start-client.sh" << 'LINUXEOF'
#!/bin/bash
# LearningETL Client (Linux)

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

echo "========================================"
echo "LearningETL Client Starting..."
echo "========================================"
echo ""

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[ERROR] venv not found! Run: python3 -m venv venv"
    read -p "Press any key to exit..."
    exit 1
fi

# 클라이언트 시작
python client/agent.py

echo ""
echo "Client stopped."
read -p "Press any key to exit..."
LINUXEOF

# Standalone 모드
cat > "start-standalone.sh" << 'LINUXEOF'
#!/bin/bash
# LearningETL Standalone (Linux)

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

echo "========================================"
echo "LearningETL Standalone Mode"
echo "========================================"
echo ""

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[ERROR] venv not found! Run: python3 -m venv venv"
    read -p "Press any key to exit..."
    exit 1
fi

# main.py 실행
python main.py

echo ""
echo "Execution completed."
read -p "Press any key to exit..."
LINUXEOF

# 실행 권한 부여
chmod +x start-server.sh
chmod +x start-client.sh
chmod +x start-standalone.sh

echo "✓ Linux .sh 파일 생성 완료"

# ========================================
# 4. Desktop 바로가기 생성 (Linux)
# ========================================

if [ "$(uname)" == "Linux" ]; then
    echo "4. Linux Desktop 바로가기 생성 중..."

    # Server Desktop Entry
    cat > "LearningETL-Server.desktop" << DESKTOPEOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LearningETL Server
Comment=Start LearningETL Server
Exec=bash $PROJECT_ROOT/start-server.sh
Icon=utilities-terminal
Terminal=true
Categories=Development;
DESKTOPEOF

    # Client Desktop Entry
    cat > "LearningETL-Client.desktop" << DESKTOPEOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LearningETL Client
Comment=Start LearningETL Client
Exec=bash $PROJECT_ROOT/start-client.sh
Icon=utilities-terminal
Terminal=true
Categories=Development;
DESKTOPEOF

    # Standalone Desktop Entry
    cat > "LearningETL-Standalone.desktop" << DESKTOPEOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LearningETL Standalone
Comment=Run LearningETL in Standalone Mode
Exec=bash $PROJECT_ROOT/start-standalone.sh
Icon=utilities-terminal
Terminal=true
Categories=Development;
DESKTOPEOF

    chmod +x LearningETL-*.desktop

    echo "✓ Desktop 바로가기 생성 완료"
    echo ""
    echo "Desktop 바로가기를 사용하려면:"
    echo "  cp LearningETL-*.desktop ~/Desktop/"
fi

# ========================================
# 완료!
# ========================================

echo ""
echo "=========================================="
echo "✓ 실행 파일 생성 완료!"
echo "=========================================="
echo ""
echo "생성된 파일:"
echo ""
echo "Windows (.bat):"
echo "  - Start-Server.bat"
echo "  - Start-Client.bat"
echo "  - Start-Standalone.bat"
echo ""
echo "macOS (.command):"
echo "  - Start-Server.command"
echo "  - Start-Client.command"
echo "  - Start-Standalone.command"
echo ""
echo "Linux (.sh):"
echo "  - start-server.sh"
echo "  - start-client.sh"
echo "  - start-standalone.sh"
echo ""

if [ "$(uname)" == "Linux" ]; then
    echo "Desktop 바로가기:"
    echo "  - LearningETL-Server.desktop"
    echo "  - LearningETL-Client.desktop"
    echo "  - LearningETL-Standalone.desktop"
    echo ""
fi

echo "사용법:"
echo "  Windows: 파일 더블클릭"
echo "  macOS: 파일 더블클릭 (최초 1회: 시스템 환경설정 → 보안 및 개인정보)"
echo "  Linux: 파일 더블클릭 또는 ./start-xxx.sh"
echo ""
