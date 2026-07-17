"""
Draft 저장 모듈
MD draft 작성 및 저장
파일명: draft의 종류(dev, algorithm, study) + 초안 생성 시간 + 초안 작성에 쓰인 첨부파일 이름.md

하나의 소스 JSON에서 여러 개의 포스팅이 생성되는 경우(예: 대화 하나에 서로 다른
학습 주제가 여러 개 섞여 있어 주제별로 포스팅을 분리하는 경우), part 번호를 붙여
"{draft_type}_{source_name}_part{N}.md" 형식으로 저장한다.
"""
import re
from pathlib import Path
from datetime import datetime


class DraftSaver:
    """Draft 저장 클래스"""

    def __init__(self):
        self.draft_dir = Path(__file__).parent.parent.parent / "data" / "draft"

        # Draft 디렉터리 생성
        (self.draft_dir / "algorithm").mkdir(parents=True, exist_ok=True)
        (self.draft_dir / "dev").mkdir(parents=True, exist_ok=True)
        (self.draft_dir / "study").mkdir(parents=True, exist_ok=True)
        (self.draft_dir / "pr").mkdir(parents=True, exist_ok=True)

    def save_draft(self, draft_type: str, content: str, source_json: str, part: int = None) -> str:
        """
        Draft 저장 (Gemini 출력 그대로)

        Args:
            draft_type: draft 종류 (algorithm, dev, study)
            content: 초안 내용 (마크다운)
            source_json: 첨부파일 이름 (JSON 파일명)
            part: 한 소스에서 여러 포스팅으로 분리된 경우의 파트 번호 (1부터 시작).
                  None이면 기존과 동일하게 파트 표시 없이 저장

        Returns:
            str: 저장된 draft 파일 경로
        """
        # source_json에서 .json 제거
        source_name = source_json.replace(".json", "")

        # 파일명: draft종류_JSON파일명[_partN].md (시간 제외)
        part_suffix = f"_part{part}" if part else ""
        filename = f"{draft_type}_{source_name}{part_suffix}.md"

        # 저장 경로
        file_path = self.draft_dir / draft_type / filename

        # 저장 (Gemini 출력 그대로)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def is_duplicate_draft(self, source_json: str, draft_type: str) -> bool:
        """
        Draft 중복 체크
        첨부파일 이름으로 중복 판단
        오류 draft는 자동으로 삭제

        save_draft()가 "{draft_type}_{source_name}.md" 또는 여러 포스팅으로 분리된
        경우 "{draft_type}_{source_name}_partN.md" 형식으로 저장하므로, 두 형식을
        모두 매칭하는 패턴으로 폴더를 훑어 존재 여부를 확인한다.

        Args:
            source_json: 첨부파일 이름 (JSON 파일명)
            draft_type: draft 종류 (algorithm, dev, study)

        Returns:
            bool: 중복이면 True (단, 오류 draft는 삭제 후 False 반환. 여러 파트 중
                  일부만 오류인 경우 해당 파트만 삭제하고, 나머지 정상 파트가
                  남아있으면 여전히 중복으로 취급한다)
        """
        # source_json에서 .json 제거
        source_name = source_json.replace(".json", "")
        draft_folder = self.draft_dir / draft_type
        pattern = re.compile(rf'^{re.escape(draft_type)}_{re.escape(source_name)}(_part\d+)?\.md$')
        matching_files = [f for f in draft_folder.glob("*.md") if pattern.match(f.name)]

        if not matching_files:
            return False

        remaining = []
        for draft_file in matching_files:
            if self._is_error_draft(draft_file):
                print(f"    🗑️  오류 draft 삭제: {draft_file.name}")
                draft_file.unlink()  # 삭제
            else:
                remaining.append(draft_file)

        return len(remaining) > 0

    def _is_error_draft(self, draft_path: Path) -> bool:
        """
        오류 draft인지 확인
        첫 10줄 안에 "오류", "RESOURCE_EXHAUSTED", "초안 생성 중 오류 발생" 등이 있으면 오류 draft

        Args:
            draft_path: draft 파일 경로

        Returns:
            bool: 오류 draft이면 True
        """
        try:
            with open(draft_path, "r", encoding="utf-8") as f:
                # 첫 10줄만 읽기
                lines = [f.readline() for _ in range(10)]
                content = "".join(lines)

                # 오류 키워드 체크
                error_keywords = [
                    "# 오류",
                    "초안 생성 중 오류 발생",
                    "RESOURCE_EXHAUSTED",
                    "429",
                    "quota",
                    "exceeded your current quota"
                ]

                for keyword in error_keywords:
                    if keyword in content:
                        return True

                return False

        except Exception:
            return False

    def get_drafts_by_type(self, draft_type: str) -> list:
        """
        특정 타입의 모든 draft 파일 조회

        Args:
            draft_type: draft 종류 (algorithm, dev, study)

        Returns:
            list: draft 파일 경로 리스트
        """
        draft_type_dir = self.draft_dir / draft_type

        if not draft_type_dir.exists():
            return []

        return [str(f) for f in draft_type_dir.glob("*.md")]

    def get_all_drafts(self) -> list:
        """
        모든 draft 파일 조회

        Returns:
            list: draft 파일 경로 리스트
        """
        all_drafts = []

        for draft_type in ["algorithm", "dev", "study", "pr"]:
            all_drafts.extend(self.get_drafts_by_type(draft_type))

        return all_drafts

    def get_recent_drafts(self, limit: int = 10) -> list:
        """
        최근 생성된 draft 파일 조회

        Args:
            limit: 조회할 최대 개수

        Returns:
            list: draft 파일 경로 리스트 (최신순)
        """
        all_drafts = []

        for draft_type in ["algorithm", "dev", "study", "pr"]:
            draft_type_dir = self.draft_dir / draft_type
            if draft_type_dir.exists():
                all_drafts.extend(draft_type_dir.glob("*.md"))

        # 수정 시간 기준 정렬 (최신순)
        all_drafts.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        return [str(f) for f in all_drafts[:limit]]


if __name__ == "__main__":
    saver = DraftSaver()

    # 테스트: draft 저장
    content = "# 백준 1234: 두 수의 합\n\n풀이 내용..."
    draft_path = saver.save_draft(
        draft_type="algorithm",
        content=content,
        source_json="Bronze_3_2024-01-01_두_수의_합_1234.json"
    )
    print(f"Draft 저장: {draft_path}")

    # 중복 체크
    is_dup = saver.is_duplicate_draft(
        "Bronze_3_2024-01-01_두_수의_합_1234.json",
        "algorithm"
    )
    print(f"중복 여부: {is_dup}")

    # 최근 drafts 조회
    recent = saver.get_recent_drafts(5)
    print(f"최근 drafts: {len(recent)}개")
