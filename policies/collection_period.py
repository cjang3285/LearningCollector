"""
소스별 수집 기간 관리 모듈
- baekjoon_collected_time.log: 백준 커밋 수집 시간
- commits_collected_time.log: 개발 커밋 수집 시간
- 각 소스별로 새 데이터가 수집됐을 때만 시간 기록
- AI Chat은 시간 기반 수집이 아니므로 제외
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path


class CollectionPeriodManager:
    """소스별 수집 기간 관리 클래스"""

    def __init__(self):
        self.log_dir = Path(__file__).parent.parent / "log"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 소스별 로그 파일 경로
        self.baekjoon_log = self.log_dir / "baekjoon_collected_time.log"
        self.commits_log = self.log_dir / "commits_collected_time.log"

    def _get_kst_now(self) -> datetime:
        """현재 한국 시간 (KST) 반환"""
        utc_now = datetime.now(timezone.utc)
        kst_now = utc_now + timedelta(hours=9)
        return kst_now.replace(tzinfo=None, microsecond=0)

    def _get_utc_now(self) -> datetime:
        """현재 UTC 시간 반환"""
        return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

    def get_baekjoon_period(self) -> tuple:
        """
        백준허브 커밋 수집 기간 계산

        Returns:
            tuple: (start_date, end_date) - UTC datetime
        """
        return self._get_source_period(self.baekjoon_log, "백준허브 커밋")

    def get_commits_period(self) -> tuple:
        """
        개발사항 커밋 수집 기간 계산

        Returns:
            tuple: (start_date, end_date) - UTC datetime
        """
        return self._get_source_period(self.commits_log, "개발사항 커밋")

    def _get_source_period(self, log_path: Path, source_name: str) -> tuple:
        """
        특정 소스의 수집 기간 계산

        Args:
            log_path: 로그 파일 경로
            source_name: 소스 이름 (로깅용)

        Returns:
            tuple: (start_date, end_date) - UTC datetime
        """
        import os
        end_date = self._get_utc_now()

        # 환경변수로 강제 30일 수집 (테스트용)
        force_full = os.getenv("FORCE_FULL_COLLECTION", "false").lower() == "true"
        if force_full:
            start_date = end_date - timedelta(days=30)
            print(f"  🔄 [{source_name}] 강제 전체 수집: 최근 30일")
            return start_date, end_date

        # 마지막 수집 시간 확인
        last_time = self._read_last_time(log_path)

        if last_time is None:
            # 첫 실행: 로그 파일 생성 (현재 KST 시간 기록)
            self._init_log_file(log_path, source_name)
            # 30일 전부터 수집
            start_date = end_date - timedelta(days=30)
            print(f"  📌 [{source_name}] 첫 실행: 최근 30일 수집")
        else:
            start_date = last_time
            duration = end_date - start_date
            hours = duration.total_seconds() / 3600
            print(f"  📌 [{source_name}] 마지막 수집 이후: {hours:.1f}시간")

        return start_date, end_date

    def _read_last_time(self, log_path: Path) -> datetime:
        """로그 파일에서 마지막 시간 읽기 (주석 제외)"""
        if not log_path.exists():
            return None

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

                # 뒤에서부터 주석 아닌 줄 찾기
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return datetime.fromisoformat(line)

        except Exception as e:
            print(f"  ⚠️  로그 읽기 실패 ({log_path.name}): {e}")

        return None

    def _init_log_file(self, log_path: Path, source_name: str):
        """로그 파일 초기화 (현재 UTC 시간 기록)"""
        utc_now = self._get_utc_now()
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"# {source_name} 수집 시간 로그\n")
                f.write(f"{utc_now.isoformat()}\n")  # 초기 시간 기록
            print(f"  📁 [{source_name}] 로그 파일 생성: {log_path.name}")
        except Exception as e:
            print(f"  ⚠️  로그 파일 생성 실패: {e}")

    def update_baekjoon_time(self):
        """백준 커밋 수집 성공 시 시간 기록"""
        self._update_source_time(self.baekjoon_log, "백준")

    def update_commits_time(self):
        """개발 커밋 수집 성공 시 시간 기록"""
        self._update_source_time(self.commits_log, "개발 커밋")

    def _update_source_time(self, log_path: Path, source_name: str):
        """특정 소스의 수집 시간 업데이트 (UTC)"""
        current_time = self._get_utc_now()

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{current_time.isoformat()}\n")
            print(f"  ✅ [{source_name}] 수집 시간 기록: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        except Exception as e:
            print(f"  ⚠️  수집 시간 기록 실패 ({source_name}): {e}")

    def get_history(self, source: str) -> list:
        """
        특정 소스의 수집 히스토리 조회

        Args:
            source: "baekjoon" 또는 "commits"

        Returns:
            list: 수집 시간 리스트
        """
        log_path = self.baekjoon_log if source == "baekjoon" else self.commits_log

        if not log_path.exists():
            return []

        history = []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        history.append(datetime.fromisoformat(line))
        except Exception as e:
            print(f"  ⚠️  히스토리 읽기 실패: {e}")

        return history


if __name__ == "__main__":
    manager = CollectionPeriodManager()

    # 백준 수집 기간
    baek_start, baek_end = manager.get_baekjoon_period()
    print(f"백준 수집 기간: {baek_start} ~ {baek_end}")

    # 개발 커밋 수집 기간
    commit_start, commit_end = manager.get_commits_period()
    print(f"개발 커밋 수집 기간: {commit_start} ~ {commit_end}")
