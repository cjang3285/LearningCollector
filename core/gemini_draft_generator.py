"""
Gemini Draft 생성 모듈 (메인 흐름)
지난 실행 시간 이후로 수집된 JSON을 참조하여 4가지 초안을 생성하고 VS Code로 연다

카테고리별 항목들은 여러 워커 스레드로 병렬 처리한다. 각 워커는 자기 전용의
AIClient(= 전용 claude CLI 영속 프로세스)를 가지고 있어서, 서로 다른 항목의
요청이 같은 claude 프로세스의 stdin/stdout에서 뒤섞이는 일이 없다. Gemini
일일 한도 초과 여부는 SharedFlag로 모든 워커가 공유하므로, 한 워커가 한도
초과를 확인하는 즉시 나머지 워커들도 바로 Claude Pro로만 처리하게 된다.
"""
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import List, Tuple

# API 모듈 임포트
from api.ai_client import AIClient, SharedFlag
from api.blog_api import BlogAPIClient

# 정책 모듈 임포트
from policies.storage.draft_saver import DraftSaver
from core import structured_logger as slog

DEFAULT_PARALLEL_WORKERS = 3


class GeminiDraftGenerator:
    """Gemini를 사용한 초안 생성 클래스 (병렬 워커 풀)"""

    def __init__(self):
        self.max_workers = int(os.getenv("CLAUDE_PARALLEL_WORKERS", str(DEFAULT_PARALLEL_WORKERS)))

        # Gemini 일일 한도 초과 여부는 모든 워커가 공유 (한 워커가 확인하면 전부 즉시 반영)
        self.gemini_exhausted_flag = SharedFlag()
        # Gemini + Claude Pro 둘 다 영구 실패 시 나머지 항목 전체를 포기하는 플래그
        self.quota_exhausted_flag = SharedFlag()

        self.ai_clients = [
            AIClient(gemini_exhausted_flag=self.gemini_exhausted_flag)
            for _ in range(self.max_workers)
        ]
        print(f"  [AI] Gemini 우선 + Claude Pro(claude CLI) 폴백 모드 (워커 {self.max_workers}개 병렬)")

        self.blog_client = BlogAPIClient()
        self.draft_saver = DraftSaver()
        self.editor_command = os.getenv("EDITOR_COMMAND", "nano")
        self._print_lock = threading.Lock()

    def close(self):
        """파이프라인 종료 시 워커별 claude CLI 영속 프로세스 정리"""
        for ai_client in self.ai_clients:
            ai_client.close()

    def _print(self, message: str):
        """여러 워커 스레드가 동시에 출력해도 줄이 안 섞이도록"""
        with self._print_lock:
            print(message)

    def generate_drafts(
        self,
        ai_chat_jsons: List[str],
        baekjoon_jsons: List[str],
        commit_jsons: List[str],
        pr_jsons: List[str] = None
    ) -> Tuple[List[str], List[str]]:
        """
        4가지 초안 생성
        1. 백준 풀이 초안
        2. 개발 진척 초안
        3. AI 대화 공부 초안
        4. PR 요약 초안

        Returns:
            Tuple[List[str], List[str]]:
                - 생성된 draft 파일 경로 리스트
                - 초안 생성에 성공한 JSON 파일명 리스트
        """
        pr_jsons = pr_jsons or []
        all_drafts = []
        all_succeeded_jsons = []

        # 1. 백준 풀이 초안 작성
        if baekjoon_jsons:
            print(f"  백준 풀이 초안 생성 중... ({len(baekjoon_jsons)}개)")
            baekjoon_drafts, succeeded = self._generate_drafts_parallel(
                baekjoon_jsons, "algorithm", "알고리즘_풀이_포스팅_프롬프트.md", "백준"
            )
            all_drafts.extend(baekjoon_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(baekjoon_drafts)}개 생성 완료")

        # 2. 개발 진척 초안 작성
        if commit_jsons:
            print(f"  개발 진척 초안 생성 중... ({len(commit_jsons)}개)")
            dev_drafts, succeeded = self._generate_drafts_parallel(
                commit_jsons, "dev", "프로젝트_진척_및_의사결정_요약_프롬프트.md", "개발 커밋"
            )
            all_drafts.extend(dev_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(dev_drafts)}개 생성 완료")

        # 3. AI 대화 공부 초안 작성
        if ai_chat_jsons:
            print(f"  AI 대화 공부 초안 생성 중... ({len(ai_chat_jsons)}개)")
            study_drafts, succeeded = self._generate_drafts_parallel(
                ai_chat_jsons, "study", "당일_공부_요약_프롬프트.md", "AI Chat"
            )
            all_drafts.extend(study_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(study_drafts)}개 생성 완료")

        # 4. PR 요약 초안 작성
        if pr_jsons:
            print(f"  PR 요약 초안 생성 중... ({len(pr_jsons)}개)")
            pr_drafts, succeeded = self._generate_drafts_parallel(
                pr_jsons, "pr", "PR_리뷰_및_병합_요약_프롬프트.md", "PR"
            )
            all_drafts.extend(pr_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(pr_drafts)}개 생성 완료")

        # 5. 블로그 포스팅 (초안 생성 직후)
        if all_drafts:
            print(f"\n  블로그 포스팅 중... ({len(all_drafts)}개)")
            self._post_to_blog(all_drafts)

        # 6. 에디터로 열기 (맨 마지막)
        if all_drafts:
            self._open_in_editor(all_drafts)

        return all_drafts, all_succeeded_jsons

    def _generate_drafts_parallel(
        self, json_files: List[str], draft_type: str, prompt_filename: str, label: str
    ) -> Tuple[List[str], List[str]]:
        """
        카테고리 하나(백준/개발/AI대화/PR)의 항목들을 워커 풀로 병렬 생성

        Returns:
            Tuple[List[str], List[str]]: (draft 파일 경로 리스트, 성공한 JSON 파일명 리스트)
        """
        drafts = []
        succeeded_jsons = []
        duplicates = []

        self._print(f"    총 {len(json_files)}개의 {label} JSON 발견")

        # 중복 체크는 순수 파일 I/O라 미리 순차 처리 (병렬 대상에서 제외)
        pending = []
        for json_file in json_files:
            if self.draft_saver.is_duplicate_draft(json_file, draft_type):
                duplicates.append(json_file)
                succeeded_jsons.append(json_file)
            else:
                pending.append(json_file)

        if pending:
            prompt = self._load_prompt(prompt_filename)
            task_queue: "queue.Queue[str]" = queue.Queue()
            for json_file in pending:
                task_queue.put(json_file)

            results_lock = threading.Lock()

            def worker(ai_client: AIClient):
                while True:
                    try:
                        json_file = task_queue.get_nowait()
                    except queue.Empty:
                        return

                    try:
                        if self.quota_exhausted_flag.get():
                            self._print(f"    한도 초과로 스킵: {json_file}")
                            continue

                        self._print(f"    처리 중: {json_file}")
                        slog.draft_start(draft_type, json_file)

                        json_content = self._load_json(json_file)
                        draft_content = ai_client.generate_draft(prompt, json_content)

                        if draft_content is None:
                            if ai_client.last_error_permanent:
                                self.quota_exhausted_flag.set()
                                slog.draft_failure(draft_type, json_file,
                                                   "all_ai_providers_permanently_failed")
                                self._print(f"    ⚠️  AI API 한도 초과. 나머지 {label} draft 생성 중단")
                            else:
                                slog.draft_failure(draft_type, json_file, "transient_ai_failure")
                                self._print(f"    ⚠️  일시적 오류로 실패, 다음 항목 계속 진행: {json_file}")
                            continue

                        draft_path = self.draft_saver.save_draft(
                            draft_type=draft_type,
                            content=draft_content,
                            source_json=json_file,
                        )
                        with results_lock:
                            drafts.append(draft_path)
                            succeeded_jsons.append(json_file)
                        slog.draft_success(draft_type, json_file, draft_path)
                        self._print(f"    ✅ 성공: {draft_path}")
                    finally:
                        task_queue.task_done()

            threads = [
                threading.Thread(target=worker, args=(self.ai_clients[i],), daemon=True)
                for i in range(self.max_workers)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # 중복 로깅
        if duplicates:
            print(f"    ⚠️  중복 제외: {len(duplicates)}개 (이미 draft 생성됨)")
            for dup in duplicates:
                print(f"      - {dup}")

        slog.draft_summary(draft_type, total=len(json_files),
                           success=len(drafts), failed=len(pending) - len(drafts),
                           duplicates=len(duplicates))

        return drafts, succeeded_jsons

    def _load_prompt(self, prompt_filename: str) -> str:
        """프롬프트 파일 로드"""
        prompt_path = Path(__file__).parent.parent / "prompts" / prompt_filename
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_json(self, json_filename: str) -> str:
        """JSON 파일 로드"""
        # data/ 폴더에서 JSON 파일 찾기
        data_dir = Path(__file__).parent.parent / "data"

        # baekjoon, commits, ai_chat, prs 폴더에서 검색
        for subdir in ["baekjoon", "commits", "ai_chat", "prs"]:
            json_path = data_dir / subdir / json_filename
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    return f.read()

        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_filename}")

    def _open_in_editor(self, draft_paths: List[str]):
        """생성된 초안들을 에디터로 열기"""
        if not draft_paths:
            return

        try:
            # nano는 한 번에 여러 파일 지원하지 않으므로 첫 번째 파일만 열기
            if self.editor_command == "nano":
                print(f"\n  에디터로 첫 번째 파일 열기: {draft_paths[0]}")
                subprocess.run([self.editor_command, draft_paths[0]])
            else:
                # code, vim 등은 여러 파일 지원
                subprocess.run([self.editor_command] + draft_paths, check=True)
                print(f"\n  에디터로 {len(draft_paths)}개 파일 열기 완료")
        except subprocess.CalledProcessError as e:
            print(f"  에디터 실행 실패: {str(e)}")
        except FileNotFoundError:
            print(f"  에디터를 찾을 수 없습니다: {self.editor_command}")

    def _post_to_blog(self, draft_paths: List[str]):
        """블로그에 포스팅"""
        for draft_path in draft_paths:
            try:
                # Draft 파일에서 메타데이터 추출 (H1 제목, 첫 문단 등)
                result = self.blog_client.create_post_from_draft(draft_path)

                if result.get("success"):
                    print(f"    ✅ 블로그 포스팅 완료: {result.get('title', 'Unknown')}")
                    if result.get("url"):
                        print(f"       URL: {result['url']}")
                else:
                    slog.blog_post_failure(draft_path,
                                           result.get("message", "Unknown error"))
                    print(f"    ❌ 블로그 포스팅 실패: {draft_path}")
                    print(f"       오류: {result.get('message', 'Unknown error')}")

            except Exception as e:
                slog.blog_post_failure(draft_path, str(e))
                print(f"    ❌ 블로그 포스팅 예외 발생: {draft_path} - {str(e)}")

    def _extract_title(self, markdown_content: str) -> str:
        """마크다운에서 제목 추출"""
        lines = markdown_content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "제목 없음"


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    generator = GeminiDraftGenerator()
    generator.generate_drafts(
        ai_chat_jsons=["example_chat.json"],
        baekjoon_jsons=["example_baekjoon.json"],
        commit_jsons=["example_commit.json"]
    )
