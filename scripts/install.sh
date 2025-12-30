#!/bin/bash
# LearningETL 원스텝 설치 스크립트

set -e

echo "=========================================="
echo "🚀 LearningETL 자동 설치 시작"
echo "=========================================="
echo ""

# 프로젝트 루트
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 모드 선택
echo "설치 모드를 선택하세요:"
echo "  1) Standalone Mode (한 대의 머신에서 모든 작업)"
echo "  2) Client-Server Mode - Server (라즈베리파이)"
echo "  3) Client-Server Mode - Client (노트북/데스크탑)"
echo ""
read -p "선택 (1-3): " MODE

case $MODE in
    1)
        INSTALL_MODE="standalone"
        REQUIREMENTS_FILE="requirements.txt"
        ;;
    2)
        INSTALL_MODE="server"
        REQUIREMENTS_FILE="requirements-server.txt"
        ;;
    3)
        INSTALL_MODE="client"
        REQUIREMENTS_FILE="requirements-client.txt"
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac

echo ""
echo "선택한 모드: $INSTALL_MODE"
echo ""

# Python 버전 확인
echo "1️⃣ Python 버전 확인..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION"
echo ""

# 가상환경 생성
if [ ! -d "venv" ]; then
    echo "2️⃣ 가상환경 생성 중..."
    python3 -m venv venv
    echo "✅ 가상환경 생성 완료"
else
    echo "2️⃣ 가상환경이 이미 존재합니다."
fi
echo ""

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
echo "3️⃣ 의존성 설치 중..."
pip install --upgrade pip
pip install -r "$REQUIREMENTS_FILE"
echo "✅ 의존성 설치 완료"
echo ""

# .env 파일 생성
if [ ! -f ".env" ]; then
    echo "4️⃣ 환경 변수 설정..."
    cp .env.example .env
    echo "✅ .env 파일 생성 완료"
    echo ""
    echo "⚠️  .env 파일을 편집해주세요:"
    echo "  nano .env"
    echo ""
    read -p "지금 편집하시겠습니까? (y/N): " EDIT_ENV
    if [[ $EDIT_ENV =~ ^[Yy]$ ]]; then
        nano .env
    fi
else
    echo "4️⃣ .env 파일이 이미 존재합니다."
fi
echo ""

# 모드별 추가 설정
if [ "$INSTALL_MODE" = "standalone" ] || [ "$INSTALL_MODE" = "server" ]; then
    # PostgreSQL 및 DB 설정
    echo "5️⃣ 데이터베이스 설정..."
    read -p "PostgreSQL 데이터베이스를 설정하시겠습니까? (Y/n): " SETUP_DB
    SETUP_DB=${SETUP_DB:-Y}

    if [[ $SETUP_DB =~ ^[Yy]$ ]]; then
        bash scripts/setup-database.sh
    else
        echo "⏭️  데이터베이스 설정 건너뜀"
    fi
    echo ""

    # cron 설정
    if [ "$INSTALL_MODE" = "standalone" ] || [ "$INSTALL_MODE" = "server" ]; then
        echo "6️⃣ cron 자동 수집 설정..."
        read -p "매일 자동으로 데이터를 수집하시겠습니까? (Y/n): " SETUP_CRON
        SETUP_CRON=${SETUP_CRON:-Y}

        if [[ $SETUP_CRON =~ ^[Yy]$ ]]; then
            bash scripts/setup-cron.sh
        else
            echo "⏭️  cron 설정 건너뜀"
        fi
        echo ""
    fi

    # systemd 설정 (Server 모드)
    if [ "$INSTALL_MODE" = "server" ]; then
        echo "7️⃣ FastAPI 서버 자동 시작 설정..."
        read -p "systemd 서비스로 등록하시겠습니까? (y/N): " SETUP_SYSTEMD

        if [[ $SETUP_SYSTEMD =~ ^[Yy]$ ]]; then
            echo "systemd 서비스 설정 중..."

            # 서비스 파일 복사 및 편집
            TEMP_SERVICE=$(mktemp)
            cp docs/systemd-examples/learningetl-server.service "$TEMP_SERVICE"

            # 사용자명 및 경로 치환
            CURRENT_USER=$(whoami)
            sed -i "s|User=jcw|User=$CURRENT_USER|g" "$TEMP_SERVICE"
            sed -i "s|Group=jcw|Group=$CURRENT_USER|g" "$TEMP_SERVICE"
            sed -i "s|/home/jcw/LearningETL|$PROJECT_ROOT|g" "$TEMP_SERVICE"

            sudo cp "$TEMP_SERVICE" /etc/systemd/system/learningetl-server.service
            sudo systemctl daemon-reload
            sudo systemctl enable learningetl-server
            sudo systemctl start learningetl-server

            echo "✅ systemd 서비스 등록 완료"
            echo "서비스 상태: sudo systemctl status learningetl-server"
        else
            echo "⏭️  systemd 설정 건너뜀"
            echo ""
            echo "💡 수동으로 FastAPI 서버 실행:"
            echo "  python server/api.py"
        fi
        echo ""
    fi

elif [ "$INSTALL_MODE" = "client" ]; then
    # Client 설정
    echo "5️⃣ 서버 연결 설정..."
    read -p "서버 URL을 입력하세요 (예: http://raspberrypi.local:8000): " SERVER_URL

    echo ""
    echo "Client Agent 실행 명령:"
    echo "  python client/agent.py --server $SERVER_URL"
    echo ""

    read -p "systemd 서비스로 등록하시겠습니까? (y/N): " SETUP_CLIENT_SYSTEMD

    if [[ $SETUP_CLIENT_SYSTEMD =~ ^[Yy]$ ]]; then
        echo "systemd 서비스 설정 중..."

        TEMP_SERVICE=$(mktemp)
        cp docs/systemd-examples/learningetl-client.service "$TEMP_SERVICE"

        CURRENT_USER=$(whoami)
        sed -i "s|User=username|User=$CURRENT_USER|g" "$TEMP_SERVICE"
        sed -i "s|Group=username|Group=$CURRENT_USER|g" "$TEMP_SERVICE"
        sed -i "s|/home/username/LearningETL|$PROJECT_ROOT|g" "$TEMP_SERVICE"
        sed -i "s|http://raspberrypi.local:8000|$SERVER_URL|g" "$TEMP_SERVICE"

        sudo cp "$TEMP_SERVICE" /etc/systemd/system/learningetl-client.service
        sudo systemctl daemon-reload
        sudo systemctl enable learningetl-client
        sudo systemctl start learningetl-client

        echo "✅ systemd 서비스 등록 완료"
        echo "서비스 상태: sudo systemctl status learningetl-client"
    else
        echo "⏭️  systemd 설정 건너뜀"
    fi
    echo ""
fi

# 설치 테스트
echo "8️⃣ 설치 테스트 중..."
if bash scripts/test-installation.sh; then
    echo "✅ 설치 테스트 통과"
else
    echo "⚠️  일부 테스트 실패 (수동으로 확인 필요)"
fi
echo ""

# 완료
echo "=========================================="
echo "🎉 설치 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"

if [ "$INSTALL_MODE" = "standalone" ]; then
    echo "  1. 테스트 실행: python main.py"
    echo "  2. cron이 매일 자동으로 수집합니다"
    echo "  3. 로그 확인: tail -f logs/main.log"

elif [ "$INSTALL_MODE" = "server" ]; then
    echo "  1. FastAPI 서버 실행 중: http://0.0.0.0:8000"
    echo "  2. API 문서: http://localhost:8000/docs"
    echo "  3. cron이 매일 자동으로 GitHub/Baekjoon 수집"
    echo "  4. 로그 확인: sudo journalctl -u learningetl-server -f"

elif [ "$INSTALL_MODE" = "client" ]; then
    echo "  1. Client Agent 실행 중"
    echo "  2. Downloads 폴더 감시 중"
    echo "  3. 로그 확인: sudo journalctl -u learningetl-client -f"
fi

echo ""
echo "📖 문서:"
echo "  - README.md"
echo "  - docs/standalone-guide.md"
echo "  - docs/client-server-guide.md"
echo ""
