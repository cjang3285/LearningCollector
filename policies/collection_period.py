"""
통합 수집 기간 계산 및 관리 모듈
첫 실행: 한달 전부터 당일까지
이후 실행: 마지막 실행 시간부터 현재 시간까지
"""
from datetime import datetime, timedelta
from pathlib import Path


class CollectionPeriodManager:
    """수집 기간 관리 클래스"""

    def __init__(self):
        self.log_dir = Path(__file__).parent.parent / "log"
        self.exec_log_path = self.log_dir / "exec_date.log"

        # 로그 디렉터리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_collection_period(self) -> tuple:
        """
        수집 기간 계산

        Returns:
            tuple: (start_date, end_date)
        """
        import os
        end_date = datetime.now()

        # 환경변수로 강제 30일 수집 (테스트용)
        force_full_collection = os.getenv("FORCE_FULL_COLLECTION", "false").lower() == "true"

        if force_full_collection:
            start_date = end_date - timedelta(days=30)
            print(f"  🔄 강제 전체 수집 모드: 최근 30일")
            return start_date, end_date

        # 마지막 실행 시간 확인
        last_exec_time = self._get_last_execution_time()

        if last_exec_time is None:
            # 첫 실행: 한달 전부터
            start_date = end_date - timedelta(days=30)
            print(f"  📌 첫 실행: 최근 30일 수집")
        else:
            # 이후 실행: 마지막 실행 시간부터
            start_date = last_exec_time
            duration = end_date - start_date
            print(f"  📌 증분 수집: 마지막 실행 이후 ({duration.total_seconds() / 60:.1f}분)")
            print(f"     exec_date.log 위치: {self.exec_log_path}")

        return start_date, end_date

    def _get_last_execution_time(self) -> datetime:
        """
        마지막 실행 시간 조회

        Returns:
            datetime: 마지막 실행 시간 (없으면 None)
        """
        if not self.exec_log_path.exists():
            return None

        try:
            with open(self.exec_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    # 마지막 줄 읽기
                    last_line = lines[-1].strip()
                    return datetime.fromisoformat(last_line)
        except Exception as e:
            print(f"경고: exec_date.log 읽기 실패 - {str(e)}")

        return None

    def update_last_execution(self):
        """현재 시간을 마지막 실행 시간으로 기록"""
        current_time = datetime.now()

        try:
            with open(self.exec_log_path, "a", encoding="utf-8") as f:
                f.write(f"{current_time.isoformat()}\n")
            print(f"\n실행 시간 기록: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"경고: exec_date.log 쓰기 실패 - {str(e)}")

    def get_execution_history(self) -> list:
        """
        실행 히스토리 조회

        Returns:
            list: 실행 시간 리스트
        """
        if not self.exec_log_path.exists():
            return []

        history = []
        try:
            with open(self.exec_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        history.append(datetime.fromisoformat(line))
        except Exception as e:
            print(f"경고: exec_date.log 읽기 실패 - {str(e)}")

        return history


if __name__ == "__main__":
    manager = CollectionPeriodManager()

    # 수집 기간 확인
    start, end = manager.get_collection_period()
    print(f"수집 기간: {start} ~ {end}")

    # 실행 히스토리
    history = manager.get_execution_history()
    print(f"실행 히스토리: {len(history)}회")

    # 실행 시간 업데이트
    manager.update_last_execution()
