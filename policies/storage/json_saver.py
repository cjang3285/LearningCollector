"""
JSON 저장 모듈
중복 체크 후 data/ 폴더에 JSON 저장
각 JSON에 상태 필드 포함: draft_created, posted, skipped
"""
import json
from pathlib import Path
from datetime import datetime, timedelta

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

    def _get_default_status(self) -> dict:
        """기본 상태 필드 반환"""
        return {
            "draft_created": False,  # 초안 작성 여부
            "posted": False,         # 포스팅 여부
            "skipped": False         # 영구 포기 여부
        }

    def _utc_to_kst(self, utc_time_str: str) -> str:
        """
        UTC 시간을 KST로 변환

        Args:
            utc_time_str: ISO 8601 형식 UTC 시간 (예: "2026-01-21T12:18:56Z")

        Returns:
            str: KST 시간 (예: "2026-01-21_21-18-56")
        """
        # ISO 8601 파싱 (Z를 +00:00으로 변환)
        utc_time_str = utc_time_str.replace("Z", "+00:00")
        utc_time = datetime.fromisoformat(utc_time_str)

        # UTC → KST (+9시간)
        kst_time = utc_time + timedelta(hours=9)

        # 파일명용 형식: YYYY-MM-DD_HH-MM-SS
        return kst_time.strftime("%Y-%m-%d_%H-%M-%S")

    def save_baekjoon(self, data: dict) -> str:
        """
        백준 JSON 저장
        파일명: 티어_문제번호_문제제목_푼시간.json

        Returns:
            str: 저장된 파일명 (중복이면 None)
        """
        commit_sha = data.get("커밋_SHA")

        # 중복 체크
        if self.duplicate_checker.is_duplicate_baekjoon(commit_sha):
            return None

        # 파일명 생성
        tier = data.get("티어", "Unknown")
        problem_name = data.get("문제명", "Unknown")
        problem_number = data.get("문제_번호", "Unknown")
        solved_time = data.get("제출한_날짜", "")

        # UTC → KST 변환
        if solved_time:
            kst_time = self._utc_to_kst(solved_time)
        else:
            kst_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # 파일명: 티어_번호_제목_시간.json
        safe_name = self._sanitize_filename(f"{tier}_{problem_number}_{problem_name}_{kst_time}")
        filename = f"{safe_name}.json"

        # 상태 필드 추가
        data["_status"] = self._get_default_status()

        # 저장
        file_path = self.data_dir / "baekjoon" / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def save_commit(self, data: dict) -> str:
        """
        개발 커밋 JSON 저장
        파일명: 레포_브랜치_메시지핵심_커밋시간_SHA.json

        Returns:
            str: 저장된 파일명 (중복이면 None)
        """
        sha = data.get("SHA")

        # 중복 체크
        if self.duplicate_checker.is_duplicate_commit(sha):
            return None

        # 파일명 구성 요소
        repo = data.get("레포지토리", "unknown")
        branch = data.get("브랜치", "unknown")
        commit_message = data.get("커밋_메시지", "")
        commit_time = data.get("커밋_날짜", "")

        # SHA 앞 7자리
        short_sha = sha[:7] if sha else "unknown"

        # 커밋 메시지 핵심 (첫 줄, 30자 제한)
        message_core = commit_message.split("\n")[0][:30]

        # UTC → KST 변환
        if commit_time:
            kst_commit_time = self._utc_to_kst(commit_time)
        else:
            kst_commit_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # 파일명: 레포_브랜치_메시지_커밋시간_SHA.json
        safe_name = self._sanitize_filename(
            f"{repo}_{branch}_{message_core}_{kst_commit_time}_{short_sha}"
        )
        filename = f"{safe_name}.json"

        # 상태 필드 추가
        data["_status"] = self._get_default_status()

        # 저장
        file_path = self.data_dir / "commits" / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def save_ai_chat(self, data: dict) -> str:
        """
        AI Chat JSON 저장
        파일명: AI종류_파일제목_exported시간.json

        Returns:
            str: 저장된 파일명 (중복이면 None)
        """
        original_filename = data.get("원본_파일")

        # 중복 체크 (원본 파일명 기반)
        if self.duplicate_checker.is_duplicate_ai_chat(original_filename):
            return None

        ai_type = data.get("AI_종류")
        file_title = data.get("파일_제목", "NoTitle")  # 파일명 기반 제목 사용
        exported_time = data.get("Exported_시간", "")

        # Exported 시간 파싱하여 파일명용 형식으로 변환
        formatted_time = self._format_exported_time(exported_time)

        # 파일명: AI종류_파일제목_시간.json
        safe_title = self._sanitize_filename(file_title)
        filename = f"{ai_type}_{safe_title}_{formatted_time}.json"

        # 상태 필드 추가
        data["_status"] = self._get_default_status()

        # 저장
        file_path = self.data_dir / "ai_chat" / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def _format_exported_time(self, exported_time: str) -> str:
        """
        Exported 시간을 파일명용 형식으로 변환
        다양한 형식 지원: ISO 8601, 자연어 등
        """
        if not exported_time:
            return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        try:
            # ISO 8601 형식 시도
            if "T" in exported_time:
                exported_time = exported_time.replace("Z", "+00:00")
                dt = datetime.fromisoformat(exported_time)
                return dt.strftime("%Y-%m-%d_%H-%M-%S")

            # 일반적인 날짜/시간 형식 시도
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"]:
                try:
                    dt = datetime.strptime(exported_time, fmt)
                    return dt.strftime("%Y-%m-%d_%H-%M-%S")
                except ValueError:
                    continue

            # 파싱 실패 시 특수문자 제거하고 반환
            safe_time = exported_time.replace(":", "-").replace(" ", "_").replace("/", "-")
            return self._sanitize_filename(safe_time)[:25]

        except Exception:
            return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def update_status(self, json_filename: str, field: str, value: bool) -> bool:
        """
        JSON 파일의 상태 필드 업데이트

        Args:
            json_filename: JSON 파일명
            field: 업데이트할 필드 (draft_created, posted, skipped)
            value: 설정할 값

        Returns:
            bool: 성공 여부
        """
        # 모든 폴더에서 파일 찾기
        for subdir in ["baekjoon", "commits", "ai_chat"]:
            file_path = self.data_dir / subdir / json_filename
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # _status 필드가 없으면 생성
                    if "_status" not in data:
                        data["_status"] = self._get_default_status()

                    data["_status"][field] = value

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    return True
                except Exception as e:
                    print(f"  ⚠️  상태 업데이트 실패 ({json_filename}): {e}")
                    return False

        return False

    def get_pending_jsons(self, verbose: bool = False) -> dict:
        """
        처리되지 않은 JSON 파일들 조회

        Args:
            verbose: True면 상세 로그 출력

        Returns:
            dict: {
                "no_draft": [(폴더, 파일명), ...],  # 초안 미작성
                "no_post": [(폴더, 파일명), ...]    # 포스팅 미완료
            }
        """
        result = {
            "no_draft": [],
            "no_post": []
        }

        for subdir in ["baekjoon", "commits", "ai_chat"]:
            folder = self.data_dir / subdir
            if not folder.exists():
                if verbose:
                    print(f"  [DEBUG] 폴더 없음: {folder}")
                continue

            json_files = list(folder.glob("*.json"))
            if verbose:
                print(f"  [DEBUG] {subdir}/: {len(json_files)}개 JSON 발견")

            for json_file in json_files:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    status = data.get("_status", {})

                    # skipped면 무시
                    if status.get("skipped", False):
                        if verbose:
                            print(f"    [SKIP] {json_file.name}: skipped=True")
                        continue

                    # 초안 미작성
                    if not status.get("draft_created", False):
                        result["no_draft"].append((subdir, json_file.name))
                        if verbose:
                            print(f"    [PENDING] {json_file.name}: draft_created=False")
                    # 초안은 작성됐지만 포스팅 미완료
                    elif not status.get("posted", False):
                        result["no_post"].append((subdir, json_file.name))
                        if verbose:
                            print(f"    [PENDING] {json_file.name}: posted=False")
                    else:
                        if verbose:
                            print(f"    [DONE] {json_file.name}: 처리 완료")

                except Exception as e:
                    if verbose:
                        print(f"    [ERROR] {json_file.name}: {e}")
                    continue

        return result

    def get_json_summary(self, json_filename: str) -> dict:
        """
        JSON 파일의 요약 정보 반환

        Args:
            json_filename: JSON 파일명

        Returns:
            dict: 요약 정보
        """
        for subdir in ["baekjoon", "commits", "ai_chat"]:
            file_path = self.data_dir / subdir / json_filename
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if subdir == "baekjoon":
                        return {
                            "type": "백준",
                            "title": f"{data.get('티어', 'Unknown')} - {data.get('문제명', 'Unknown')}",
                            "number": data.get("문제_번호", "Unknown"),
                            "status": data.get("_status", {})
                        }
                    elif subdir == "commits":
                        return {
                            "type": "개발",
                            "title": data.get("커밋_메시지", "Unknown")[:50],
                            "repo": data.get("레포지토리", "Unknown"),
                            "status": data.get("_status", {})
                        }
                    else:  # ai_chat
                        return {
                            "type": "AI Chat",
                            "title": data.get("파일_제목", data.get("대화_제목", "Unknown"))[:50],
                            "ai": data.get("AI_종류", "Unknown"),
                            "status": data.get("_status", {})
                        }
                except Exception:
                    pass

        return {"type": "Unknown", "title": json_filename}

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
