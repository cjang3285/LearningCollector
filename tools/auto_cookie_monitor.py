#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude.ai 접속 감지 시 자동으로 쿠키 추출 및 Pi 업로드

동작 방식:
1. Chrome 프로세스 모니터링
2. claude.ai 접속 감지
3. 자동으로 쿠키 추출
4. Pi로 전송

백그라운드에서 계속 실행됨
"""

import os
import sys
import time
import psutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

PROJECT_ROOT = Path(__file__).parent.parent
COOKIE_SCRIPT = PROJECT_ROOT / 'tools' / 'extract_cookies_playwright.py'
LOG_FILE = PROJECT_ROOT / 'temp' / 'cookie_monitor.log'
STATE_FILE = PROJECT_ROOT / 'temp' / 'last_extract.txt'

# 설정
CHECK_INTERVAL = 60  # 1분마다 체크
EXTRACT_COOLDOWN = 3600  # 1시간에 한 번만 추출 (너무 자주 추출 방지)

def log(message):
    """로그 출력 및 파일 저장"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')

def is_claude_running():
    """Chrome에서 claude.ai가 열려있는지 확인"""
    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if proc.info['name'] in ['chrome.exe', 'msedge.exe']:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('claude.ai' in str(arg).lower() for arg in cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        log(f"프로세스 체크 에러: {e}")

    return False

def should_extract():
    """쿠키를 추출해야 하는지 확인 (cooldown 체크)"""
    if not STATE_FILE.exists():
        return True

    try:
        with open(STATE_FILE, 'r') as f:
            last_time = datetime.fromisoformat(f.read().strip())

        elapsed = datetime.now() - last_time
        if elapsed.total_seconds() < EXTRACT_COOLDOWN:
            return False
    except Exception as e:
        log(f"상태 파일 읽기 에러: {e}")

    return True

def update_last_extract():
    """마지막 추출 시간 업데이트"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        f.write(datetime.now().isoformat())

def extract_and_upload():
    """쿠키 추출 및 Pi 업로드"""
    log("🍪 쿠키 추출 시작...")

    try:
        # Playwright로 쿠키 추출 및 업로드
        result = subprocess.run(
            [sys.executable, str(COOKIE_SCRIPT), '--upload'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            log("✅ 쿠키 추출 및 업로드 성공!")
            update_last_extract()
            return True
        else:
            log(f"❌ 쿠키 추출 실패: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        log("❌ 타임아웃: 쿠키 추출이 60초를 초과했습니다")
        return False
    except Exception as e:
        log(f"❌ 에러: {e}")
        return False

def main():
    """메인 모니터링 루프"""
    log("=" * 60)
    log("Claude.ai 쿠키 자동 모니터링 시작")
    log(f"체크 간격: {CHECK_INTERVAL}초")
    log(f"추출 간격: {EXTRACT_COOLDOWN}초 ({EXTRACT_COOLDOWN//3600}시간)")
    log("=" * 60)

    claude_was_running = False

    while True:
        try:
            claude_is_running = is_claude_running()

            # Claude가 새로 실행되었을 때
            if claude_is_running and not claude_was_running:
                log("🌐 Claude.ai 접속 감지!")

                if should_extract():
                    extract_and_upload()
                else:
                    last_time = STATE_FILE.read_text().strip() if STATE_FILE.exists() else "알 수 없음"
                    log(f"⏰ 쿠키 추출 대기 중 (마지막 추출: {last_time})")

            claude_was_running = claude_is_running
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            log("\n종료 중...")
            break
        except Exception as e:
            log(f"❌ 모니터링 에러: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
