#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Export ZIP 파서

data-YYYY-MM-DD-HH-MM-SS-batch-XXXX.zip 파일을 파싱하여:
1. 대화 기록을 텍스트로 저장
2. 아티팩트 데이터 추출

실행:
  python parse/claude_export_parser.py <zip_file>
"""

import os
import sys
import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# 대화 저장 디렉토리
CONVERSATIONS_DIR = Path("Z:/learning-etl/claude-conversations")
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


def parse_export_zip(zip_path: Path) -> Dict:
    """Export ZIP 파일 파싱

    Args:
        zip_path: ZIP 파일 경로

    Returns:
        파싱된 데이터 딕셔너리
    """
    print(f"📦 ZIP 파일 파싱: {zip_path.name}")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # ZIP 내부 파일 목록
        file_list = zf.namelist()
        print(f"   파일 수: {len(file_list)}")

        # 샘플 파일 출력
        print(f"   샘플 파일:")
        for fname in file_list[:5]:
            print(f"     - {fname}")

        # conversations.json 찾기
        json_files = [f for f in file_list if f.endswith('.json')]
        print(f"   JSON 파일: {len(json_files)}개")

        conversations_data = None

        # conversations.json 파싱
        if 'conversations.json' in file_list:
            print(f"\n   conversations.json 파싱 중...")

            with zf.open('conversations.json') as f:
                conversations_data = json.load(f)

            if isinstance(conversations_data, list):
                print(f"   대화 수: {len(conversations_data)}개")

                if conversations_data:
                    # 첫 대화 샘플
                    first_conv = conversations_data[0]
                    print(f"   첫 대화 키: {list(first_conv.keys())}")
                    print(f"   이름: {first_conv.get('name', 'N/A')}")
                    print(f"   UUID: {first_conv.get('uuid', 'N/A')[:16]}...")

                    # 메시지 수 확인
                    msg_count = len(first_conv.get('chat_messages', []))
                    print(f"   메시지 수: {msg_count}개")

            return {
                'zip_path': str(zip_path),
                'file_list': file_list,
                'json_files': json_files,
                'conversations': conversations_data
            }
        else:
            print("   ⚠️  conversations.json 없음")

            return {
                'zip_path': str(zip_path),
                'file_list': file_list,
                'json_files': json_files
            }

    return {}


def save_conversation_text(conversation: Dict, output_dir: Path):
    """대화를 텍스트 파일로 저장

    Args:
        conversation: 대화 데이터
        output_dir: 출력 디렉토리
    """
    # 대화 ID 추출
    conv_id = conversation.get('uuid', 'unknown')
    conv_name = conversation.get('name', 'Untitled')

    # 안전한 파일명
    safe_name = "".join(c for c in conv_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name[:50]  # 최대 50자

    filename = f"{conv_id[:8]}_{safe_name}.txt"
    output_path = output_dir / filename

    # 텍스트 생성
    lines = []
    lines.append(f"Conversation: {conv_name}")
    lines.append(f"UUID: {conv_id}")
    lines.append(f"Created: {conversation.get('created_at', 'Unknown')}")
    lines.append("=" * 80)
    lines.append("")

    # 메시지 추출
    for msg in conversation.get('chat_messages', []):
        sender = msg.get('sender', 'unknown')
        text = msg.get('text', '')

        lines.append(f"[{sender.upper()}]")
        lines.append(text)
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

    # 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"   💾 저장: {output_path.name}")
    return str(output_path)


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        # 기본 경로
        export_dir = Path("Z:/learning-etl/claude-exports")
        zip_files = list(export_dir.glob("claude_export_*.zip"))

        if not zip_files:
            print("❌ Export ZIP 파일이 없습니다.")
            print(f"경로: {export_dir}")
            return

        # 최신 파일 사용
        zip_path = sorted(zip_files, key=lambda x: x.stat().st_mtime)[-1]
        print(f"✅ 최신 파일 사용: {zip_path.name}")
    else:
        zip_path = Path(sys.argv[1])

        if not zip_path.exists():
            print(f"❌ 파일 없음: {zip_path}")
            return

    print("=" * 80)
    print("Claude Export 파서")
    print("=" * 80)
    print()

    # 파싱
    result = parse_export_zip(zip_path)

    if result:
        print()
        print("=" * 80)
        print("파싱 완료")
        print("=" * 80)
        print(f"ZIP: {result['zip_path']}")
        print(f"전체 파일: {len(result['file_list'])}개")
        print(f"JSON 파일: {len(result['json_files'])}개")
        print()

        # 대화 데이터가 있으면 처리
        conversations = result.get('conversations', [])
        if conversations:
            print(f"대화 처리 중...")
            print(f"전체 대화: {len(conversations)}개")
            print()

            saved_count = 0
            for i, conv in enumerate(conversations[:10], 1):  # 처음 10개만 테스트
                try:
                    saved_path = save_conversation_text(conv, CONVERSATIONS_DIR)
                    saved_count += 1
                except Exception as e:
                    print(f"   ❌ 대화 {i} 저장 실패: {e}")

            print()
            print(f"✅ {saved_count}개 대화 저장 완료")
            print(f"📁 저장 위치: {CONVERSATIONS_DIR}")


if __name__ == '__main__':
    main()
