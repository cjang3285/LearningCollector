"""
JSON 저장 모듈
중복 체크 후 data/ 폴더에 JSON 저장
"""
import json
from pathlib import Path
from datetime import datetime

from policies.storage.duplicate_checker import DuplicateChecker


class JSONSaver:
    """JSON 저장 클래스"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.duplicate_checker = DuplicateChecker()

        # 데이터 디렉터리 생성
        (self.data_dir / "baekjoon").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "commits").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "ai_chat").mkdir(parents=True, exist_ok=True)

    def save_baekjoon(self, data: dict) -> str:
        """
        백준 JSON 저장
        파일명: 티어+푼 시간+문제 제목+번호.json

        Returns:
            str: 저장된 파일명 (중복이면 None)
        """
        commit_sha = data.get("커밋_SHA")

        # 중복 체크
        if self.duplicate_checker.is_duplicate_baekjoon(commit_sha):
            return None

        # 파일명 생성
        tier = data.get("티어", "Unknown")
        solved_time = data.get("제출한_날짜", datetime.now().isoformat())
        problem_name = data.get("문제명", "Unknown")
        problem_number = data.get("문제_번호", "Unknown")

        # 파일명에서 특수문자 제거
        safe_name = self._sanitize_filename(f"{tier}_{solved_time}_{problem_name}_{problem_number}")
        filename = f"{safe_name}.json"

        # 저장
        file_path = self.data_dir / "baekjoon" / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def save_commit(self, data: dict) -> str:
        """
        개발 커밋 JSON 저장
        파일명: 커밋 SHA+시간+레포지토리.json

        Returns:
            str: 저장된 파일명 (중복이면 None)
        """
        sha = data.get("SHA")

        # 중복 체크
        if self.duplicate_checker.is_duplicate_commit(sha):
            return None

        # 파일명 생성
        commit_time = data.get("커밋_날짜", datetime.now().isoformat())
        repo = data.get("레포지토리", "unknown")

        # SHA 앞 7자리만 사용
        short_sha = sha[:7] if sha else "unknown"

        safe_name = self._sanitize_filename(f"{short_sha}_{commit_time}_{repo}")
        filename = f"{safe_name}.json"

        # 저장
        file_path = self.data_dir / "commits" / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def save_ai_chat(self, data: dict) -> str:
        """
        AI Chat JSON 저장
        파일명: 대화 제목 및 exported 날짜, 시간.json

        Returns:
            str: 저장된 파일명 (중복이면 None)
        """
        ai_type = data.get("AI_종류")
        exported_time = data.get("Exported_시간")

        # 중복 체크
        if self.duplicate_checker.is_duplicate_ai_chat(ai_type, exported_time):
            return None

        # 파일명 생성
        title = data.get("대화_제목", "NoTitle")

        safe_title = self._sanitize_filename(title)
        safe_time = self._sanitize_filename(exported_time)
        filename = f"{ai_type}_{safe_title}_{safe_time}.json"

        # 저장
        file_path = self.data_dir / "ai_chat" / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def _sanitize_filename(self, filename: str) -> str:
        """파일명에서 특수문자 제거"""
        # 파일명으로 사용 불가능한 문자 제거
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # 공백을 언더스코어로 변경
        filename = filename.replace(" ", "_")

        # 연속된 언더스코어 제거
        while "__" in filename:
            filename = filename.replace("__", "_")

        # 최대 길이 제한 (200자)
        if len(filename) > 200:
            filename = filename[:200]

        return filename


if __name__ == "__main__":
    saver = JSONSaver()

    # 테스트: 백준 JSON 저장
    baekjoon_data = {
        "문제_번호": "1234",
        "문제명": "두 수의 합",
        "티어": "Bronze_3",
        "풀이_코드": "print(sum(map(int, input().split())))",
        "제출한_날짜": "2024-01-01T12:00:00",
        "커밋_SHA": "abc123def456"
    }

    filename = saver.save_baekjoon(baekjoon_data)
    print(f"백준 JSON 저장: {filename}")

    # 테스트: 개발 커밋 JSON 저장
    commit_data = {
        "커밋_메시지": "feat: Add authentication",
        "SHA": "xyz789abc123",
        "변경된_파일_목록": ["auth.py", "models.py"],
        "커밋_날짜": "2024-01-01T13:00:00",
        "레포지토리": "TestRepo"
    }

    filename = saver.save_commit(commit_data)
    print(f"개발 커밋 JSON 저장: {filename}")

    # 테스트: AI Chat JSON 저장
    ai_chat_data = {
        "대화_제목": "Python 학습",
        "모든_대화_내용": "대화 내용...",
        "Exported_시간": "2024-01-01T14:00:00",
        "AI_종류": "ChatGPT"
    }

    filename = saver.save_ai_chat(ai_chat_data)
    print(f"AI Chat JSON 저장: {filename}")
