"""
전체 흐름 조율 모듈 (Orchestrator)
대화형 인터페이스로 수집 → 번호 선택 → 초안 작성 → 포스팅
"""
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Tuple, Dict

# 콜렉터 임포트
from core.ai_chat_collector import AIChatCollector
from core.github_collector import GitHubCollector
from core.gemini_draft_generator import GeminiDraftGenerator
from core import structured_logger as slog

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
        collect_timer = slog.start_timer()
        ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons = self._collect_all()
        slog.info("collection_phase_end", "orchestrator",
                  ai_chat=len(ai_chat_jsons), baekjoon=len(baekjoon_jsons),
                  commits=len(commit_jsons), prs=len(pr_jsons),
                  total=len(ai_chat_jsons) + len(baekjoon_jsons) + len(commit_jsons) + len(pr_jsons),
                  duration_ms=slog.elapsed_ms(collect_timer))

        # 2. 이전 실행에서 실패한 pending 항목 병합
        ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons = self._merge_pending(
            ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons
        )

        # 3. 수집 결과 요약 및 처리
        total = len(ai_chat_jsons) + len(baekjoon_jsons) + len(commit_jsons) + len(pr_jsons)

        if total == 0:
            print("\n" + "=" * 50)
            print("📊 수집 결과")
            print("=" * 50)
            print("  처리할 데이터가 없습니다.")
        else:
            if self.auto:
                self._auto_process(ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons)
            else:
                self._interactive_process(ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons)

        print("\n" + "=" * 50)
        print("LearningCollector 실행 완료")
        print("=" * 50)

    def _collect_all(self) -> Tuple[List[str], List[str], List[str], List[str]]:
        """모든 소스에서 데이터 수집"""

        # 1. AI Chat 수집 (시간 무관)
        print("\n[1/2] AI Chat 수집 중...")
        slog.collection_start("ai_chat")
        ai_chat_timer = slog.start_timer()
        ai_chat_jsons = self.ai_chat_collector.collect(None, None)
        print(f"  → {len(ai_chat_jsons)}개의 AI Chat JSON 저장 완료")

        # ai_chat 수집 종료 로그 (collector 내부에서 detailed log를 남기므로 여기선 duration만)
        slog.collection_end("ai_chat", total_found=0, duplicates=0,
                            saved=len(ai_chat_jsons),
                            duration_ms=slog.elapsed_ms(ai_chat_timer))

        # 2. GitHub 수집 (소스별 기간)
        print("\n[2/2] GitHub 수집 중...")
        slog.collection_start("github")
        github_timer = slog.start_timer()

        # 백준 서비스 종료로 백준 커밋 수집 기간 계산은 비활성화함 (github_collector가
        # 백준 레포 커밋을 더 이상 수집하지 않으므로 여기서도 조회할 필요가 없음)
        # baek_start, baek_end = self.period_manager.get_baekjoon_period()
        commit_start, commit_end = self.period_manager.get_commits_period()

        start_date = commit_start
        end_date = commit_end

        # UTC와 KST 둘 다 표시
        start_kst = start_date + timedelta(hours=9)
        end_kst = end_date + timedelta(hours=9)
        print(f"  📅 조회 기간(UTC): {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"  📅 조회 기간(KST): {start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%Y-%m-%d %H:%M')}")

        if self.auto:
            baekjoon_jsons, commit_jsons, pr_jsons = self.github_collector.collect(start_date, end_date)
        else:
            baekjoon_jsons, commit_jsons, pr_jsons = self.github_collector.collect_interactive(start_date, end_date)

        print(f"  → 백준허브: {len(baekjoon_jsons)}개, 개발사항: {len(commit_jsons)}개, PR: {len(pr_jsons)}개 JSON 저장 완료")
        slog.collection_end("github", total_found=0, duplicates=0,
                            saved=len(baekjoon_jsons) + len(commit_jsons) + len(pr_jsons),
                            duration_ms=slog.elapsed_ms(github_timer),
                            baekjoon=len(baekjoon_jsons),
                            commits=len(commit_jsons),
                            prs=len(pr_jsons))

        # 성공적으로 수집된 소스만 시간 업데이트
        # (백준은 서비스 종료로 비활성화 - baekjoon_jsons는 항상 빈 리스트)
        # if baekjoon_jsons:
        #     self.period_manager.update_baekjoon_time()
        if commit_jsons:
            self.period_manager.update_commits_time()

        return ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons

    def _merge_pending(self, ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons):
        """이전 실행에서 초안 생성 실패한 pending 항목을 병합"""
        pending = self.json_saver.get_pending_jsons()
        no_draft = pending["no_draft"]  # [(subdir, filename), ...]

        if not no_draft:
            return ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons

        # 이번에 새로 수집된 파일명 (중복 방지)
        new_set = set(ai_chat_jsons + baekjoon_jsons + commit_jsons + pr_jsons)

        pending_count = 0
        for subdir, filename in no_draft:
            if filename in new_set:
                continue
            pending_count += 1
            if subdir == "ai_chat":
                ai_chat_jsons.append(filename)
            elif subdir == "baekjoon":
                baekjoon_jsons.append(filename)
            elif subdir == "commits":
                commit_jsons.append(filename)
            elif subdir == "prs":
                pr_jsons.append(filename)

        if pending_count > 0:
            print(f"\n  📋 이전 실행에서 미처리된 항목 {pending_count}개 발견 (재시도 대상)")

        return ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons

    def _auto_process(self, ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons):
        """Auto 모드: 새로 수집된 것 전체 자동 처리"""

        all_new = ai_chat_jsons + baekjoon_jsons + commit_jsons + pr_jsons

        print("\n[Auto] 새 항목 블로그 초안 생성 및 포스팅 중...")
        process_timer = slog.start_timer()
        drafts, succeeded_jsons = self.draft_generator.generate_drafts(
            ai_chat_jsons,
            baekjoon_jsons,
            commit_jsons,
            pr_jsons
        )

        # 상태 업데이트 (성공한 JSON만)
        succeeded_set = set(succeeded_jsons)
        for json_file in all_new:
            if json_file in succeeded_set:
                self.json_saver.update_status(json_file, "draft_created", True)
                self.json_saver.update_status(json_file, "posted", True)

        failed_count = len(all_new) - len(succeeded_set)
        slog.info("process_phase_end", "orchestrator",
                  mode="auto", total=len(all_new),
                  drafts_created=len(drafts), succeeded=len(succeeded_set),
                  failed=failed_count,
                  duration_ms=slog.elapsed_ms(process_timer))
        print(f"  → {len(drafts)}개의 초안 생성 완료")
        if failed_count > 0:
            print(f"  → {failed_count}개 항목 초안 생성 실패 (다음 실행에서 재시도)")

    def _interactive_process(self, ai_chat_jsons, baekjoon_jsons, commit_jsons, pr_jsons):
        """Interactive 모드: 번호 선택 방식"""

        # 전체 항목 리스트 생성 (번호 부여)
        all_items = []  # [(번호, 폴더, 파일명, 요약), ...]

        print("\n" + "=" * 50)
        print("📊 수집 결과 요약")
        print("=" * 50)

        idx = 1

        if ai_chat_jsons:
            print(f"\n  📝 AI Chat ({len(ai_chat_jsons)}개):")
            for json_file in ai_chat_jsons:
                summary = self.json_saver.get_json_summary(json_file)
                print(f"    {idx}. [{summary.get('ai', '?')}] {summary.get('title', json_file)[:40]}")
                all_items.append((idx, "ai_chat", json_file, summary))
                idx += 1

        if baekjoon_jsons:
            print(f"\n  🏆 백준허브 커밋 ({len(baekjoon_jsons)}개):")
            for json_file in baekjoon_jsons:
                summary = self.json_saver.get_json_summary(json_file)
                print(f"    {idx}. [{summary.get('number', '?')}] {summary.get('title', json_file)[:40]}")
                all_items.append((idx, "baekjoon", json_file, summary))
                idx += 1

        if commit_jsons:
            print(f"\n  💻 개발사항 커밋 ({len(commit_jsons)}개):")
            for json_file in commit_jsons:
                summary = self.json_saver.get_json_summary(json_file)
                print(f"    {idx}. [{summary.get('repo', '?')}] {summary.get('title', json_file)[:40]}")
                all_items.append((idx, "commits", json_file, summary))
                idx += 1

        if pr_jsons:
            print(f"\n  🔀 PR ({len(pr_jsons)}개):")
            for json_file in pr_jsons:
                summary = self.json_saver.get_json_summary(json_file)
                print(f"    {idx}. [{summary.get('repo', '?')}] {summary.get('title', json_file)[:40]}")
                all_items.append((idx, "prs", json_file, summary))
                idx += 1

        # 선택 입력
        print("\n" + "-" * 50)
        print("📮 초안 작성할 항목 번호 입력")
        print("   - 번호 입력 (쉼표 구분): 1,3,5")
        print("   - 전체 처리: all")
        print("   - 전체 포기: n (선택 안 한 항목은 영구 포기)")
        print("-" * 50)

        choice = input("선택: ").strip().lower()

        if choice == 'n' or choice == '':
            # 전체 영구 포기
            print("\n  ⏭️  전체 영구 포기 처리 중...")
            for _, folder, filename, _ in all_items:
                self.json_saver.update_status(filename, "skipped", True)
                self.json_saver.update_status(filename, "draft_created", True)
                self.json_saver.update_status(filename, "posted", True)
            print(f"  → {len(all_items)}개 항목 영구 포기 완료")
            return

        if choice == 'all':
            # 전체 처리
            selected_indices = set(range(1, len(all_items) + 1))
        else:
            # 번호 파싱
            try:
                selected_indices = set()
                for part in choice.split(','):
                    part = part.strip()
                    if '-' in part:
                        # 범위 (1-5)
                        start, end = part.split('-')
                        selected_indices.update(range(int(start), int(end) + 1))
                    else:
                        selected_indices.add(int(part))
            except ValueError:
                print("  ⚠️  잘못된 입력. 전체 영구 포기 처리합니다.")
                for _, folder, filename, _ in all_items:
                    self.json_saver.update_status(filename, "skipped", True)
                    self.json_saver.update_status(filename, "draft_created", True)
                    self.json_saver.update_status(filename, "posted", True)
                return

        # 선택된 항목과 포기 항목 분리
        selected_items = []
        skipped_items = []

        for item in all_items:
            if item[0] in selected_indices:
                selected_items.append(item)
            else:
                skipped_items.append(item)

        # 포기 항목 처리
        if skipped_items:
            for _, folder, filename, _ in skipped_items:
                self.json_saver.update_status(filename, "skipped", True)
                self.json_saver.update_status(filename, "draft_created", True)
                self.json_saver.update_status(filename, "posted", True)
            print(f"\n  ⏭️  {len(skipped_items)}개 항목 영구 포기")

        # 선택 항목 처리
        if selected_items:
            print(f"\n[처리] {len(selected_items)}개 항목 블로그 초안 생성 중...")

            # 폴더별로 분류
            ai_chat = [f for _, folder, f, _ in selected_items if folder == "ai_chat"]
            baekjoon = [f for _, folder, f, _ in selected_items if folder == "baekjoon"]
            commits = [f for _, folder, f, _ in selected_items if folder == "commits"]
            prs = [f for _, folder, f, _ in selected_items if folder == "prs"]

            drafts, succeeded_jsons = self.draft_generator.generate_drafts(ai_chat, baekjoon, commits, prs)

            # 상태 업데이트 (성공한 JSON만)
            succeeded_set = set(succeeded_jsons)
            for _, folder, filename, _ in selected_items:
                if filename in succeeded_set:
                    self.json_saver.update_status(filename, "draft_created", True)
                    self.json_saver.update_status(filename, "posted", True)

            failed_count = len(selected_items) - len(succeeded_set)
            print(f"  → {len(drafts)}개의 초안 생성 및 포스팅 완료")
            if failed_count > 0:
                print(f"  → {failed_count}개 항목 초안 생성 실패 (다음 실행에서 재시도)")


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
