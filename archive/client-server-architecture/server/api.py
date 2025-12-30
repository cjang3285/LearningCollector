#!/usr/bin/env python3
"""
LearningETL Server - FastAPI 파일 수신 서버

라즈베리파이에서 실행:
    uvicorn server.api:app --host 0.0.0.0 --port 8000
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from datetime import datetime, date
import logging
import hashlib
import shutil
from typing import Optional

from collectors.ai_chat_collector import AIChatCollector
from config.settings import get_log_file

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('server')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="LearningETL Server",
    description="AI 채팅 파일 수신 및 처리 서버",
    version="1.0.0"
)

# 업로드 임시 디렉토리
UPLOAD_DIR = PROJECT_ROOT / "uploads" / "temp"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Collector 초기화
ai_chat_collector = AIChatCollector()


def calculate_md5(file_path: Path) -> str:
    """파일 MD5 체크섬 계산"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def process_file(file_path: Path, original_filename: str, target_date: date):
    """백그라운드에서 파일 처리 (파싱 + DB 저장)"""
    try:
        logger.info(f"파일 처리 시작: {original_filename}")

        # AI Chat Collector로 처리
        result = ai_chat_collector.collect_from_files(
            file_paths=[str(file_path)],
            target_date=target_date
        )

        if result.get('success'):
            logger.info(f"파일 처리 완료: {original_filename}")
            logger.info(f"저장된 대화: {result.get('conversations_count')}개")
            logger.info(f"제공자: {result.get('providers')}")
        else:
            logger.error(f"파일 처리 실패: {original_filename} - {result.get('error')}")

    except Exception as e:
        logger.error(f"파일 처리 중 에러: {original_filename} - {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 임시 파일 삭제
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"임시 파일 삭제: {file_path}")
        except Exception as e:
            logger.error(f"임시 파일 삭제 실패: {e}")


@app.get("/")
async def root():
    """서버 상태 확인"""
    return {
        "service": "LearningETL Server",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    md5: Optional[str] = None,
    target_date: Optional[str] = None
):
    """
    AI 채팅 파일 업로드 및 처리

    Args:
        file: 업로드할 마크다운 파일
        md5: 파일 MD5 체크섬 (선택)
        target_date: 저장할 날짜 YYYY-MM-DD (기본값: 오늘)

    Returns:
        {
            "success": true,
            "filename": "Claude-Export.md",
            "size": 12345,
            "md5": "abc123...",
            "message": "파일이 처리 중입니다"
        }
    """
    try:
        # 파일명 검증
        if not file.filename.endswith('.md'):
            raise HTTPException(
                status_code=400,
                detail="마크다운 파일(.md)만 업로드 가능합니다"
            )

        # 날짜 파싱
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="날짜 형식이 잘못되었습니다 (YYYY-MM-DD)"
                )
        else:
            parsed_date = date.today()

        # 임시 파일로 저장
        temp_file = UPLOAD_DIR / f"{datetime.now().timestamp()}_{file.filename}"

        with open(temp_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        file_size = temp_file.stat().st_size
        file_md5 = calculate_md5(temp_file)

        logger.info(f"파일 수신 완료: {file.filename} ({file_size} bytes, MD5: {file_md5})")

        # MD5 체크섬 검증 (제공된 경우)
        if md5 and md5 != file_md5:
            temp_file.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"MD5 체크섬 불일치 (expected: {md5}, got: {file_md5})"
            )

        # 백그라운드에서 파일 처리
        background_tasks.add_task(
            process_file,
            temp_file,
            file.filename,
            parsed_date
        )

        return JSONResponse(
            status_code=202,  # Accepted
            content={
                "success": True,
                "filename": file.filename,
                "size": file_size,
                "md5": file_md5,
                "target_date": str(parsed_date),
                "message": "파일이 처리 중입니다"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """서버 통계"""
    return {
        "upload_dir": str(UPLOAD_DIR),
        "temp_files": len(list(UPLOAD_DIR.glob("*"))),
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn

    print("="*60)
    print("LearningETL Server 시작")
    print("="*60)
    print(f"URL: http://0.0.0.0:8000")
    print(f"Docs: http://0.0.0.0:8000/docs")
    print(f"업로드 디렉토리: {UPLOAD_DIR}")
    print("="*60)

    uvicorn.run(
        "server.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
