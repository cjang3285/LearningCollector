"""
AI Chat 수집 모듈
watchdog으로 다운로드 폴더를 감시하여 ChatGPT-, Gemini-, Claude- 접두사 md 파일 수집
"""
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 정책 모듈 임포트
from policies.storage.json_saver import JSONSaver


class AIChatCollector:
    """AI Chat 수집 클래스"""

    def __init__(self):
        self.download_dir = os.getenv("AI_CHAT_DOWNLOAD_DIR")
        self.json_saver = JSONSaver()
        self.collected_files = []

    def collect(self, start_date: datetime, end_date: datetime) -> List[str]:
        """
        다운로드 폴더에서 AI Chat MD 파일 수집

        Returns:
            List[str]: 저장된 JSON 파일명 리스트
        """
        download_path = Path(self.download_dir)

        if not download_path.exists():
            print(f"  경고: 다운로드 폴더가 존재하지 않습니다: {self.download_dir}")
            return []

        # MD 파일 검색
        md_files = self._find_ai_chat_files(download_path, start_date, end_date)
        print(f"  {len(md_files)}개의 AI Chat MD 파일 발견")

        # JSON 변환 및 저장
        saved_jsons = []
        for md_file in md_files:
            try:
                json_filename = self._process_md_file(md_file)
                if json_filename:
                    saved_jsons.append(json_filename)
                else:
                    print(f"  중복 제외: {md_file.name}")
            except Exception as e:
                print(f"  오류: {md_file.name} 처리 실패 - {str(e)}")

        return saved_jsons

    def _find_ai_chat_files(
        self,
        download_path: Path,
        start_date: datetime,
        end_date: datetime
    ) -> List[Path]:
        """
        AI Chat MD 파일 검색
        ChatGPT-, Gemini-, Claude- 접두사를 가진 파일만 수집
        파일 시간과 무관하게 모든 파일 수집 (중복은 save 시 체크)
        """
        ai_prefixes = ["ChatGPT-", "Gemini-", "Claude-"]
        found_files = []

        for md_file in download_path.glob("*.md"):
            # 파일명 체크 (접두사로 필터링)
            if any(md_file.name.startswith(prefix) for prefix in ai_prefixes):
                found_files.append(md_file)

        return found_files

    def _process_md_file(self, md_file: Path) -> str:
        """
        MD 파일을 파싱하여 JSON으로 저장

        Returns:
            str: 저장된 JSON 파일명 (중복이면 None)
        """
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 대화 제목 추출 (첫 번째 # 제목)
        title = self._extract_title(content)

        # Exported 시간 추출
        exported_time = self._extract_exported_time(content)

        # 대화 내용 추출
        conversation = self._extract_conversation(content)

        # AI 종류 추출 (파일명에서)
        ai_type = self._extract_ai_type(md_file.name)

        # JSON 데이터 생성
        ai_chat_data = {
            "대화_제목": title,
            "모든_대화_내용": conversation,
            "Exported_시간": exported_time,
            "AI_종류": ai_type,
            "원본_파일": md_file.name
        }

        # JSON 저장 (중복 체크 포함)
        json_filename = self.json_saver.save_ai_chat(ai_chat_data)
        return json_filename

    def _extract_title(self, content: str) -> str:
        """마크다운에서 제목 추출"""
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "제목 없음"

    def _extract_exported_time(self, content: str) -> str:
        """Exported 시간 추출"""
        # "Exported on: 2024-01-01 12:00:00" 형식 찾기
        match = re.search(r"Exported on[:\s]+(.+)", content)
        if match:
            return match.group(1).strip()

        # 다른 형식도 시도
        match = re.search(r"Export[ed]*\s*[Dd]ate[:\s]+(.+)", content)
        if match:
            return match.group(1).strip()

        return datetime.now().isoformat()

    def _extract_conversation(self, content: str) -> str:
        """대화 내용 추출"""
        # 메타데이터 제거 후 본문만 추출
        lines = content.split("\n")
        conversation_lines = []
        in_conversation = False

        for line in lines:
            # 실제 대화 시작 감지
            if line.startswith("**User:**") or line.startswith("**Assistant:**"):
                in_conversation = True

            if in_conversation:
                conversation_lines.append(line)

        return "\n".join(conversation_lines) if conversation_lines else content

    def _extract_ai_type(self, filename: str) -> str:
        """파일명에서 AI 종류 추출"""
        if filename.startswith("ChatGPT-"):
            return "ChatGPT"
        elif filename.startswith("Gemini-"):
            return "Gemini"
        elif filename.startswith("Claude-"):
            return "Claude"
        return "Unknown"


class AIChatWatchdog(FileSystemEventHandler):
    """실시간 파일 감시용 핸들러 (향후 확장용)"""

    def __init__(self, collector: AIChatCollector):
        self.collector = collector

    def on_created(self, event):
        """새 파일 생성 시 호출"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix == ".md":
            ai_prefixes = ["ChatGPT-", "Gemini-", "Claude-"]
            if any(file_path.name.startswith(prefix) for prefix in ai_prefixes):
                print(f"새 AI Chat 파일 감지: {file_path.name}")
                # 처리 로직


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    from datetime import timedelta
    collector = AIChatCollector()
    end = datetime.now()
    start = end - timedelta(days=30)
    collector.collect(start, end)
