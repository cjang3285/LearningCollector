"""
Draft 저장 모듈
MD draft 작성 및 저장
파일명: draft의 종류(dev, algorithm, study) + 초안 생성 시간 + 초안 작성에 쓰인 첨부파일 이름.md
"""
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

    def save_draft(self, draft_type: str, content: str, source_json: str) -> str:
        """
        Draft 저장

        Args:
            draft_type: draft 종류 (algorithm, dev, study)
            content: 초안 내용 (마크다운)
            source_json: 첨부파일 이름 (JSON 파일명)

        Returns:
            str: 저장된 draft 파일 경로
        """
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # source_json에서 .json 제거
        source_name = source_json.replace(".json", "")

        filename = f"{draft_type}_{timestamp}_{source_name}.md"

        # 저장 경로
        file_path = self.draft_dir / draft_type / filename

        # 저장
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def is_duplicate_draft(self, source_json: str, draft_type: str) -> bool:
        """
        Draft 중복 체크
        첨부파일 이름으로 중복 판단

        Args:
            source_json: 첨부파일 이름 (JSON 파일명)
            draft_type: draft 종류 (algorithm, dev, study)

        Returns:
            bool: 중복이면 True
        """
        draft_type_dir = self.draft_dir / draft_type

        if not draft_type_dir.exists():
            return False

        # source_json에서 .json 제거
        source_name = source_json.replace(".json", "")

        # 해당 타입의 모든 draft 파일 확인
        for draft_file in draft_type_dir.glob("*.md"):
            # 파일명이 source_name으로 끝나는지 확인
            if draft_file.stem.endswith(source_name):
                return True

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

        for draft_type in ["algorithm", "dev", "study"]:
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

        for draft_type in ["algorithm", "dev", "study"]:
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
