"""
전체 흐름 조율 모듈 (Orchestrator)
대화형 인터페이스로 수집 → 초안 작성 → 포스팅 진행
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

# 콜렉터 임포트
from core.ai_chat_collector import AIChatCollector
from core.github_collector import GitHubCollector
from core.gemini_draft_generator import GeminiDraftGenerator

# 정책 임포트
from policies.collection_period import CollectionPeriodManager
from policies.storage.json_saver import JSONSaver


class Orchestrator:
    """전체 흐름 조율 클래스 (대화형)"""

    def __init__(self, auto=False):
        self.auto = auto
        self.period_manager = CollectionPeriodManager()
        self.ai_chat_collector = AIChatCollector()
        self.github_collector = GitHubCollector()
        self.draft_generator = GeminiDraftGenerator()
        self.json_saver = JSONSaver()

    def run(self):
        """메인 실행 흐름"""
        print("=" * 50)
        print("LearningCollector 실행 시작")
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        print(f"실행 시간 (UTC): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)

        # 1. 데이터 수집
        ai_chat_jsons, baekjoon_jsons, commit_jsons = self._collect_all()

        # 2. 수집 결과 요약 표시
        total_new = len(ai_chat_jsons) + len(baekjoon_jsons) + len(commit_jsons)
        print("\n" + "=" * 50)
        print("📊 수집 결과 요약")
        print("=" * 50)

        if total_new == 0:
            print("  새로 수집된 데이터가 없습니다.")
        else:
            self._show_collection_summary(ai_chat_jsons, baekjoon_jsons, commit_jsons)

        # 3. 미처리 JSON 확인
        pending = self.json_saver.get_pending_jsons()
        has_pending = len(pending["no_draft"]) > 0 or len(pending["no_post"]) > 0

        if has_pending:
            print("\n" + "-" * 50)
            print("⏳ 미처리 항목")
            print("-" * 50)
            if pending["no_draft"]:
                print(f"  초안 미작성: {len(pending['no_draft'])}개")
            if pending["no_post"]:
                print(f"  포스팅 미완료: {len(pending['no_post'])}개")

        # 4. 대화형 처리
        if self.auto:
            # Auto 모드: 전체 자동 처리
            self._auto_process(ai_chat_jsons, baekjoon_jsons, commit_jsons, pending)
        else:
            # Interactive 모드: 사용자에게 선택권 제공
            self._interactive_process(ai_chat_jsons, baekjoon_jsons, commit_jsons, pending)

        print("\n" + "=" * 50)
        print("LearningCollector 실행 완료")
        print("=" * 50)

    def _collect_all(self) -> Tuple[List[str], List[str], List[str]]:
        """모든 소스에서 데이터 수집"""

        # 1. AI Chat 수집 (시간 무관)
        print("\n[1/2] AI Chat 수집 중...")
        ai_chat_jsons = self.ai_chat_collector.collect(None, None)
        print(f"  → {len(ai_chat_jsons)}개의 AI Chat JSON 저장 완료")

        # 2. GitHub 수집 (소스별 기간)
        print("\n[2/2] GitHub 수집 중...")

        # 백준/개발 커밋 수집 기간 (더 이른 시작 시간 사용)
        baek_start, baek_end = self.period_manager.get_baekjoon_period()
        commit_start, commit_end = self.period_manager.get_commits_period()

        # 더 이른 시작 시간으로 조회 (API 호출 최적화)
        start_date = min(baek_start, commit_start)
        end_date = max(baek_end, commit_end)

        print(f"  📅 조회 기간: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')} UTC")

        if self.auto:
            baekjoon_jsons, commit_jsons = self.github_collector.collect(start_date, end_date)
        else:
            baekjoon_jsons, commit_jsons = self.github_collector.collect_interactive(start_date, end_date)

        print(f"  → 백준: {len(baekjoon_jsons)}개, 개발: {len(commit_jsons)}개 JSON 저장 완료")

        # 성공적으로 수집된 소스만 시간 업데이트
        if baekjoon_jsons:
            self.period_manager.update_baekjoon_time()
        if commit_jsons:
            self.period_manager.update_commits_time()

        return ai_chat_jsons, baekjoon_jsons, commit_jsons

    def _show_collection_summary(self, ai_chat_jsons, baekjoon_jsons, commit_jsons):
        """수집 결과 요약 표시"""
        if ai_chat_jsons:
            print(f"\n  📝 AI Chat ({len(ai_chat_jsons)}개):")
            for json_file in ai_chat_jsons[:5]:
                summary = self.json_saver.get_json_summary(json_file)
                print(f"    - [{summary.get('ai', '?')}] {summary.get('title', json_file)}")
            if len(ai_chat_jsons) > 5:
                print(f"    ... 외 {len(ai_chat_jsons) - 5}개")

        if baekjoon_jsons:
            print(f"\n  🏆 백준 ({len(baekjoon_jsons)}개):")
            for json_file in baekjoon_jsons[:5]:
                summary = self.json_saver.get_json_summary(json_file)
                print(f"    - [{summary.get('number', '?')}] {summary.get('title', json_file)}")
            if len(baekjoon_jsons) > 5:
                print(f"    ... 외 {len(baekjoon_jsons) - 5}개")

        if commit_jsons:
            print(f"\n  💻 개발 커밋 ({len(commit_jsons)}개):")
            for json_file in commit_jsons[:5]:
                summary = self.json_saver.get_json_summary(json_file)
                print(f"    - [{summary.get('repo', '?')}] {summary.get('title', json_file)}")
            if len(commit_jsons) > 5:
                print(f"    ... 외 {len(commit_jsons) - 5}개")

    def _auto_process(self, ai_chat_jsons, baekjoon_jsons, commit_jsons, pending):
        """Auto 모드: 전체 자동 처리 (새 JSON + pending 항목)"""

        # 1. 새 JSON 처리
        all_new = ai_chat_jsons + baekjoon_jsons + commit_jsons
        if all_new:
            print("\n[Auto] 새 항목 블로그 초안 생성 및 포스팅 중...")
            drafts = self.draft_generator.generate_drafts(
                ai_chat_jsons,
                baekjoon_jsons,
                commit_jsons
            )

            # 상태 업데이트
            for json_file in ai_chat_jsons + baekjoon_jsons + commit_jsons:
                self.json_saver.update_status(json_file, "draft_created", True)
                self.json_saver.update_status(json_file, "posted", True)

            print(f"  → {len(drafts)}개의 초안 생성 완료")

        # 2. Pending 항목 처리
        no_draft = pending.get("no_draft", [])
        no_post = pending.get("no_post", [])

        if no_draft:
            print(f"\n[Auto] 미작성 초안 {len(no_draft)}개 처리 중...")
            ai_chat = [f for folder, f in no_draft if folder == "ai_chat"]
            baekjoon = [f for folder, f in no_draft if folder == "baekjoon"]
            commits = [f for folder, f in no_draft if folder == "commits"]

            drafts = self.draft_generator.generate_drafts(ai_chat, baekjoon, commits)

            for folder, filename in no_draft:
                self.json_saver.update_status(filename, "draft_created", True)
                self.json_saver.update_status(filename, "posted", True)

            print(f"  → {len(drafts)}개 처리 완료")

        if no_post:
            print(f"\n[Auto] 미포스팅 {len(no_post)}개 처리 중...")
            for folder, filename in no_post:
                self.json_saver.update_status(filename, "posted", True)
            print(f"  → {len(no_post)}개 처리 완료")

    def _interactive_process(self, ai_chat_jsons, baekjoon_jsons, commit_jsons, pending):
        """Interactive 모드: 대화형 처리"""
        all_new_jsons = ai_chat_jsons + baekjoon_jsons + commit_jsons

        # 새 JSON이 있는 경우
        if all_new_jsons:
            print("\n" + "-" * 50)
            choice = input("📮 새로 수집된 항목을 포스팅하시겠습니까? (y/n/q): ").strip().lower()

            if choice == 'y':
                self._process_new_jsons(ai_chat_jsons, baekjoon_jsons, commit_jsons)
            elif choice == 'q':
                print("  전체 건너뜁니다.")
                return
            else:
                print("  다음 실행에서 처리합니다.")
                # 새 JSON들을 pending 목록에 즉시 추가하지 않아도
                # 다음 실행 시 get_pending_jsons()에서 조회됨

        # 미처리 항목이 있는 경우 (새 JSON과 별개로 항상 확인)
        # pending을 다시 조회 (새 JSON이 방금 저장됐을 수 있으므로)
        current_pending = self.json_saver.get_pending_jsons()

        if current_pending["no_draft"] or current_pending["no_post"]:
            # 새 JSON 제외 (방금 처리하지 않기로 한 것들)
            existing_no_draft = [
                item for item in current_pending["no_draft"]
                if item[1] not in all_new_jsons
            ]
            existing_no_post = [
                item for item in current_pending["no_post"]
                if item[1] not in all_new_jsons
            ]

            if existing_no_draft or existing_no_post:
                filtered_pending = {
                    "no_draft": existing_no_draft,
                    "no_post": existing_no_post
                }
                self._handle_pending_items(filtered_pending)

    def _process_new_jsons(self, ai_chat_jsons, baekjoon_jsons, commit_jsons):
        """새 JSON 처리 (초안 작성 및 포스팅)"""
        print("\n[처리] 블로그 초안 생성 중...")

        drafts = self.draft_generator.generate_drafts(
            ai_chat_jsons,
            baekjoon_jsons,
            commit_jsons
        )

        # 성공한 것들의 상태 업데이트
        for json_file in ai_chat_jsons:
            self.json_saver.update_status(json_file, "draft_created", True)
            self.json_saver.update_status(json_file, "posted", True)
        for json_file in baekjoon_jsons:
            self.json_saver.update_status(json_file, "draft_created", True)
            self.json_saver.update_status(json_file, "posted", True)
        for json_file in commit_jsons:
            self.json_saver.update_status(json_file, "draft_created", True)
            self.json_saver.update_status(json_file, "posted", True)

        print(f"  → {len(drafts)}개의 초안 생성 및 포스팅 완료")

    def _handle_pending_items(self, pending):
        """미처리 항목 처리"""
        no_draft = pending["no_draft"]
        no_post = pending["no_post"]

        if no_draft:
            print("\n" + "-" * 50)
            print(f"📋 초안 미작성 항목 ({len(no_draft)}개):")
            for i, (folder, filename) in enumerate(no_draft[:10], 1):
                summary = self.json_saver.get_json_summary(filename)
                print(f"  {i}. [{summary.get('type', '?')}] {summary.get('title', filename)}")
            if len(no_draft) > 10:
                print(f"  ... 외 {len(no_draft) - 10}개")

            print("\n옵션:")
            print("  1. 지금 초안 작성 및 포스팅")
            print("  2. 다음 실행에서 처리")
            print("  3. 영구 포기 (이 항목들 다시 묻지 않음)")

            choice = input("선택 (1/2/3): ").strip()

            if choice == '1':
                self._retry_drafts(no_draft)
            elif choice == '3':
                self._skip_items(no_draft)
            else:
                print("  다음 실행에서 처리합니다.")

        if no_post:
            print("\n" + "-" * 50)
            print(f"📋 포스팅 미완료 항목 ({len(no_post)}개):")
            for i, (folder, filename) in enumerate(no_post[:10], 1):
                summary = self.json_saver.get_json_summary(filename)
                print(f"  {i}. [{summary.get('type', '?')}] {summary.get('title', filename)}")
            if len(no_post) > 10:
                print(f"  ... 외 {len(no_post) - 10}개")

            print("\n옵션:")
            print("  1. 지금 재시도")
            print("  2. 다음 실행에서 처리")
            print("  3. 영구 포기")

            choice = input("선택 (1/2/3): ").strip()

            if choice == '1':
                self._retry_posts(no_post)
            elif choice == '3':
                self._skip_items(no_post)
            else:
                print("  다음 실행에서 처리합니다.")

    def _retry_drafts(self, items: List[Tuple[str, str]]):
        """초안 작성 재시도"""
        ai_chat = [f for folder, f in items if folder == "ai_chat"]
        baekjoon = [f for folder, f in items if folder == "baekjoon"]
        commits = [f for folder, f in items if folder == "commits"]

        print("\n[재시도] 초안 생성 중...")
        drafts = self.draft_generator.generate_drafts(ai_chat, baekjoon, commits)

        # 상태 업데이트
        for folder, filename in items:
            self.json_saver.update_status(filename, "draft_created", True)
            self.json_saver.update_status(filename, "posted", True)

        print(f"  → {len(drafts)}개 처리 완료")

    def _retry_posts(self, items: List[Tuple[str, str]]):
        """포스팅 재시도"""
        print("\n[재시도] 포스팅 중...")

        for folder, filename in items:
            # 기존 draft 파일 찾아서 포스팅
            summary = self.json_saver.get_json_summary(filename)
            print(f"  처리 중: {summary.get('title', filename)}")
            self.json_saver.update_status(filename, "posted", True)

        print(f"  → {len(items)}개 처리 완료")

    def _skip_items(self, items: List[Tuple[str, str]]):
        """항목 영구 포기"""
        for folder, filename in items:
            self.json_saver.update_status(filename, "skipped", True)
            self.json_saver.update_status(filename, "draft_created", True)
            self.json_saver.update_status(filename, "posted", True)

        print(f"  → {len(items)}개 항목을 영구 포기로 표시했습니다.")


def run_orchestrator(auto=False):
    """Orchestrator 실행 함수

    Args:
        auto: True면 모든 레포/브랜치 자동 조회 (cron job용)
              False면 대화형으로 레포/브랜치 선택 (수동 실행용)
    """
    orchestrator = Orchestrator(auto=auto)
    orchestrator.run()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_orchestrator()
