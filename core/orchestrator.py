"""
전체 흐름 조율 모듈 (Orchestrator)
각 콜렉터에는 aws로부터 바이너리를 이용 실행이 지원되고 각각 필요한 모듈들을 개별적으로 호출
"""
import os
from datetime import datetime, timezone
from pathlib import Path

# 콜렉터 임포트
from core.ai_chat_collector import AIChatCollector
from core.github_collector import GitHubCollector
from core.gemini_draft_generator import GeminiDraftGenerator

# 정책 임포트
from policies.collection_period import CollectionPeriodManager


class Orchestrator:
    """전체 흐름 조율 클래스"""

    def __init__(self):
        self.period_manager = CollectionPeriodManager()
        self.ai_chat_collector = AIChatCollector()
        self.github_collector = GitHubCollector()
        self.draft_generator = GeminiDraftGenerator()

    def run(self):
        """메인 실행 흐름"""
        print("="*50)
        print("LearningCollector 실행 시작")
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        print(f"실행 시간 (UTC): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)

        # 1. 수집 기간 계산
        start_date, end_date = self.period_manager.get_collection_period()
        print(f"\n수집 기간: {start_date} ~ {end_date}")

        # 2. AI Chat 수집 (다운로드 폴더 감시)
        print("\n[1/3] AI Chat 수집 중...")
        ai_chat_jsons = self.ai_chat_collector.collect(start_date, end_date)
        print(f"  → {len(ai_chat_jsons)}개의 AI Chat JSON 저장 완료")

        # 3. GitHub 수집 (GraphQL)
        print("\n[2/3] GitHub 수집 중...")
        baekjoon_jsons, commit_jsons = self.github_collector.collect(start_date, end_date)
        print(f"  → 백준: {len(baekjoon_jsons)}개, 개발: {len(commit_jsons)}개 JSON 저장 완료")

        # 4. Draft 생성 (Gemini)
        print("\n[3/3] 블로그 초안 생성 중...")
        drafts = self.draft_generator.generate_drafts(
            ai_chat_jsons,
            baekjoon_jsons,
            commit_jsons
        )
        print(f"  → {len(drafts)}개의 초안 생성 완료")

        # 5. 실행 시간 기록
        self.period_manager.update_last_execution()

        print("\n"+"="*50)
        print("LearningCollector 실행 완료")
        print("="*50)


def run_orchestrator():
    """Orchestrator 실행 함수"""
    orchestrator = Orchestrator()
    orchestrator.run()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_orchestrator()
