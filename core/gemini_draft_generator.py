"""
Draft 생성 모듈 (메인 흐름, Claude Pro 전용)
지난 실행 시간 이후로 수집된 JSON을 참조하여 4가지 초안을 생성하고 VS Code로 연다

카테고리별 항목들은 여러 워커 스레드로 병렬 처리한다. 각 워커는 자기 전용의
AIClient(= 전용 claude CLI 영속 프로세스)를 가지고 있어서, 서로 다른 항목의
요청이 같은 claude 프로세스의 stdin/stdout에서 뒤섞이는 일이 없다. Claude Pro
사용량 한도 초과 여부는 SharedFlag로 모든 워커가 공유하므로, 한 워커가 한도
초과를 확인하는 즉시 나머지 워커들도 바로 나머지 항목 처리를 중단하게 된다.
"""
import json
import os
import queue
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# API 모듈 임포트
from api.ai_client import AIClient, SharedFlag
from api.blog_api import BlogAPIClient

# 정책 모듈 임포트
from policies.storage.draft_saver import DraftSaver
from core import structured_logger as slog

DEFAULT_PARALLEL_WORKERS = 3

# 모든 글에 다 붙을 법한 의미 없는 메타 태그. 프롬프트에서도 피하라고 안내하지만
# AI가 100% 지키지는 않아서 저장 직전에 한 번 더 걸러낸다.
BANNED_GENERIC_TAGS = {"본인", "학습", "커밋"}

# 블로그 포스팅을 작업 시간순으로 내보내기 위해 draft 종류별로 참조할 소스 JSON의
# 시간 필드. dev는 커밋 시각, pr은 병합 시각(진행 중인 PR은 애초에 수집 대상이
# 아니라 항상 존재). study(AI 채팅)엔 "작업 시간" 개념이 없어 export 시각으로 대체.
# algorithm(백준)은 매핑이 없어 시간 미상 취급 — 현재 백준 수집 자체가 비활성화라
# 실질적으로 영향 없음.
WORK_TIMESTAMP_FIELDS = {
    "dev": "커밋_날짜",
    "pr": "병합일",
    "study": "Exported_시간",
}


def _extract_work_timestamp(json_content: str, draft_type: str) -> str:
    """포스팅 정렬용 작업 시각 문자열을 소스 JSON에서 추출. 없으면 빈 문자열."""
    field = WORK_TIMESTAMP_FIELDS.get(draft_type)
    if not field:
        return ""
    try:
        data = json.loads(json_content)
    except (json.JSONDecodeError, TypeError):
        return ""
    return data.get(field) or ""


def _parse_timestamp(value: str) -> Optional[datetime]:
    """ISO 8601 문자열을 정렬 가능한 datetime으로 변환. 실패/빈 값이면 None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.rstrip("Z"))
    except ValueError:
        return None


# 구조적 중복 판정용 정규식. "Merge branch"는 dev/main 사이의 순수 병합이라
# PR과 짝지을 번호가 없어 커밋_메시지_목록 비교(패턴 B)에서만 잡음 제거 용도로 쓰고,
# "Merge pull request #N"만 특정 PR과 1:1로 묶을 수 있다(패턴 A).
_MERGE_MARKER_RE = re.compile(r"^Merge (pull request|branch)", re.IGNORECASE)
_MERGE_PR_NUM_RE = re.compile(r"^Merge pull request #(\d+) from", re.IGNORECASE)

_DRAFT_SOURCE_SUBDIR = {"dev": "commits", "pr": "prs", "study": "ai_chat", "algorithm": "baekjoon"}


def _first_line(text: str) -> str:
    return (text or "").strip().split("\n")[0].strip()


def _strip_banned_tags(content: str) -> str:
    """생성된 draft의 "**태그:**" 줄에서 BANNED_GENERIC_TAGS에 해당하는 태그를 제거."""
    lines = content.split("\n")
    tag_pattern = re.compile(r"^(\*\*태그:\*\*\s*)(.+)$")
    for i, line in enumerate(lines):
        match = tag_pattern.match(line.strip())
        if match:
            existing = [t.strip() for t in match.group(2).split(",") if t.strip()]
            filtered = [t for t in existing if t not in BANNED_GENERIC_TAGS]
            lines[i] = f"{match.group(1)}{', '.join(filtered)}"
            break
    return "\n".join(lines)


class GeminiDraftGenerator:
    """Claude Pro(claude CLI)를 사용한 초안 생성 클래스 (병렬 워커 풀)"""

    def __init__(self):
        self.max_workers = int(os.getenv("CLAUDE_PARALLEL_WORKERS", str(DEFAULT_PARALLEL_WORKERS)))

        # Claude Pro 사용량 한도 초과 시 나머지 항목 전체를 포기하는 플래그
        self.quota_exhausted_flag = SharedFlag()

        self.ai_clients = [AIClient() for _ in range(self.max_workers)]
        print(f"  [AI] Claude Pro(claude CLI) 전용 모드 (워커 {self.max_workers}개 병렬)")

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
                - 생성된 draft 파일 경로 리스트 (작업 시간순 정렬됨)
                - 초안 생성에 성공한 JSON 파일명 리스트
        """
        pr_jsons = pr_jsons or []
        all_timed_drafts: List[Tuple[str, str]] = []  # [(작업 시각, draft_path), ...]
        all_succeeded_jsons = []

        # 1. 백준 풀이 초안 작성
        if baekjoon_jsons:
            print(f"  백준 풀이 초안 생성 중... ({len(baekjoon_jsons)}개)")
            baekjoon_drafts, succeeded = self._generate_drafts_parallel(
                baekjoon_jsons, "algorithm", "알고리즘_풀이_포스팅_프롬프트.md", "백준"
            )
            all_timed_drafts.extend(baekjoon_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(baekjoon_drafts)}개 생성 완료")

        # 2. 개발 진척 초안 작성
        if commit_jsons:
            print(f"  개발 진척 초안 생성 중... ({len(commit_jsons)}개)")
            dev_drafts, succeeded = self._generate_drafts_parallel(
                commit_jsons, "dev", "프로젝트_진척_및_의사결정_요약_프롬프트.md", "개발 커밋"
            )
            all_timed_drafts.extend(dev_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(dev_drafts)}개 생성 완료")

        # 3. AI 대화 공부 초안 작성 (하나의 대화에 무관한 주제가 섞여 있으면 주제별로 분리해서 연재로 생성)
        if ai_chat_jsons:
            print(f"  AI 대화 공부 초안 생성 중... ({len(ai_chat_jsons)}개)")
            study_drafts, succeeded = self._generate_study_drafts_parallel(ai_chat_jsons)
            all_timed_drafts.extend(study_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(study_drafts)}개 생성 완료")

        # 4. PR 요약 초안 작성
        if pr_jsons:
            print(f"  PR 요약 초안 생성 중... ({len(pr_jsons)}개)")
            pr_drafts, succeeded = self._generate_drafts_parallel(
                pr_jsons, "pr", "PR_리뷰_및_병합_요약_프롬프트.md", "PR"
            )
            all_timed_drafts.extend(pr_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(pr_drafts)}개 생성 완료")

        # 5. 구조적 중복 제거. website 레포처럼 feature 브랜치 -> dev -> main으로
        # 승격하는 워크플로에서는 같은 작업이 이 배치 안에서 여러 번 draft가 될 수
        # 있다: (a) "Merge pull request #N" 커밋의 dev draft가 그 PR#N draft와
        # 같은 병합을 두 번 설명, (b) dev→main 승격처럼 여러 커밋을 묶는 PR draft가
        # 그 커밋들 각각의 개별 dev draft와 내용이 겹침. 둘 다 커밋 메시지 원문
        # 일치로 구조적으로 확인하고(제목 유사도 추측 아님), 겹치면 더 짧은/얕은
        # 쪽만 걸러낸다(본문은 남기고 포스팅만 스킵 — 다음 실행에서 재시도 안 하게
        # 소스 JSON은 이미 succeeded_jsons에 들어가 있어 posted 처리됨).
        if all_timed_drafts:
            before = len(all_timed_drafts)
            all_timed_drafts = self._dedupe_dev_pr_drafts(all_timed_drafts)
            dropped = before - len(all_timed_drafts)
            if dropped:
                print(f"\n  구조적 중복 제거: {dropped}개 draft 포스팅 제외")

        # 6. 작업 시간순 정렬 (병렬 생성이라 완료 순서가 뒤섞이므로, 포스팅 직전에
        # 커밋 시각/PR 병합 시각 기준으로 재정렬한다. 시각을 알 수 없는 항목은 뒤로 밀되
        # 그들끼리는 원래 순서(카테고리 순서)를 유지 — Python sort는 안정 정렬)
        all_timed_drafts.sort(key=lambda item: _parse_timestamp(item[0]) or datetime.max)
        all_drafts = [draft_path for _, draft_path in all_timed_drafts]

        # 7. 블로그 포스팅 (초안 생성 직후)
        if all_drafts:
            print(f"\n  블로그 포스팅 중... ({len(all_drafts)}개, 작업 시간순)")
            self._post_to_blog(all_drafts)

        # 8. 에디터로 열기 (맨 마지막)
        if all_drafts:
            self._open_in_editor(all_drafts)

        return all_drafts, all_succeeded_jsons

    def _generate_drafts_parallel(
        self, json_files: List[str], draft_type: str, prompt_filename: str, label: str
    ) -> Tuple[List[Tuple[str, str]], List[str]]:
        """
        카테고리 하나(백준/개발/AI대화/PR)의 항목들을 워커 풀로 병렬 생성

        Returns:
            Tuple[List[Tuple[str, str]], List[str]]:
                - (작업 시각, draft 파일 경로) 튜플 리스트 — 포스팅 순서 정렬용
                - 성공한 JSON 파일명 리스트
        """
        timed_drafts: List[Tuple[str, str]] = []
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
                            self._handle_ai_failure(ai_client, draft_type, json_file, label)
                            continue

                        draft_content = self._inject_identity_tags(draft_content, json_content, draft_type)
                        draft_content = _strip_banned_tags(draft_content)

                        draft_path = self.draft_saver.save_draft(
                            draft_type=draft_type,
                            content=draft_content,
                            source_json=json_file,
                        )
                        work_ts = _extract_work_timestamp(json_content, draft_type)
                        with results_lock:
                            timed_drafts.append((work_ts, draft_path))
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
                           success=len(timed_drafts), failed=len(pending) - len(timed_drafts),
                           duplicates=len(duplicates))

        return timed_drafts, succeeded_jsons

    def _generate_study_drafts_parallel(
        self, json_files: List[str]
    ) -> Tuple[List[Tuple[str, str]], List[str]]:
        """
        AI 대화 학습 초안 생성 (study 전용, 워커 풀로 병렬 생성)

        한 대화에 서로 무관한 학습 주제가 여러 개 섞여 있을 수 있으므로, 실제 초안을
        쓰기 전에 먼저 저렴한 모델로 주제를 분리해본다. 주제가 하나면 기존과 동일하게
        한 번의 요청으로 초안 하나를 생성하고, 여러 개면 주제별로 완전히 별도의 요청을
        보내 각각을 "(연재 N/M)" 표시가 붙은 별도 포스팅으로 생성한다.

        Returns:
            Tuple[List[Tuple[str, str]], List[str]]:
                - (작업 시각, draft 파일 경로) 튜플 리스트 — 포스팅 순서 정렬용
                  (연재로 분리된 파트들은 같은 대화의 export 시각을 공유)
                - 성공한 JSON 파일명 리스트
        """
        draft_type = "study"
        label = "AI Chat"
        timed_drafts: List[Tuple[str, str]] = []
        succeeded_jsons = []
        duplicates = []

        self._print(f"    총 {len(json_files)}개의 {label} JSON 발견")

        pending = []
        for json_file in json_files:
            if self.draft_saver.is_duplicate_draft(json_file, draft_type):
                duplicates.append(json_file)
                succeeded_jsons.append(json_file)
            else:
                pending.append(json_file)

        if pending:
            prompt = self._load_prompt("당일_공부_요약_프롬프트.md")
            segmentation_prompt = self._load_prompt("대화_주제_분리_프롬프트.md")
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

                        raw_json = self._load_json(json_file)
                        data = json.loads(raw_json)
                        conversation = data.get("모든_대화_내용", "")
                        work_ts = _extract_work_timestamp(raw_json, draft_type)

                        segments = self._split_into_segments(
                            ai_client, segmentation_prompt, conversation
                        )

                        if len(segments) <= 1:
                            draft_content = ai_client.generate_draft(prompt, raw_json)
                            if draft_content is None:
                                self._handle_ai_failure(ai_client, draft_type, json_file, label)
                                continue

                            draft_content = _strip_banned_tags(draft_content)
                            draft_path = self.draft_saver.save_draft(
                                draft_type=draft_type,
                                content=draft_content,
                                source_json=json_file,
                            )
                            with results_lock:
                                timed_drafts.append((work_ts, draft_path))
                                succeeded_jsons.append(json_file)
                            slog.draft_success(draft_type, json_file, draft_path)
                            self._print(f"    ✅ 성공: {draft_path}")
                            continue

                        # 서로 무관한 주제 여러 개로 분리됨 - 주제별로 완전히 별도 요청
                        total = len(segments)
                        saved_paths = []
                        failed = False

                        for idx, segment_text in enumerate(segments, start=1):
                            segment_data = dict(data)
                            segment_data["모든_대화_내용"] = segment_text
                            segment_json = json.dumps(segment_data, ensure_ascii=False)

                            part_content = ai_client.generate_draft(prompt, segment_json)
                            if part_content is None:
                                failed = True
                                break

                            part_content = self._mark_as_series_part(part_content, idx, total)
                            part_content = _strip_banned_tags(part_content)
                            saved_paths.append(
                                self.draft_saver.save_draft(
                                    draft_type=draft_type,
                                    content=part_content,
                                    source_json=json_file,
                                    part=idx,
                                )
                            )

                        if failed:
                            # 일부 파트만 저장된 채로 남으면 다음 실행에서 "이미 draft 있음"으로
                            # 오인되므로, 실패 시 이번에 저장한 파트는 지우고 다음 실행에서 처음부터 재시도
                            for saved_path in saved_paths:
                                Path(saved_path).unlink(missing_ok=True)
                            self._handle_ai_failure(ai_client, draft_type, json_file, label)
                            continue

                        with results_lock:
                            timed_drafts.extend((work_ts, saved_path) for saved_path in saved_paths)
                            succeeded_jsons.append(json_file)
                        for saved_path in saved_paths:
                            slog.draft_success(draft_type, json_file, saved_path)
                        self._print(f"    ✅ 성공 ({total}개 주제로 분리, 연재로 생성): {json_file}")
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

        if duplicates:
            print(f"    ⚠️  중복 제외: {len(duplicates)}개 (이미 draft 생성됨)")
            for dup in duplicates:
                print(f"      - {dup}")

        slog.draft_summary(draft_type, total=len(json_files),
                           success=len(succeeded_jsons) - len(duplicates),
                           failed=len(pending) - (len(succeeded_jsons) - len(duplicates)),
                           duplicates=len(duplicates))

        return timed_drafts, succeeded_jsons

    def _split_into_segments(
        self, ai_client: AIClient, segmentation_prompt: str, conversation: str
    ) -> List[str]:
        """
        대화 내용을 학습 주제 단위로 분리. 분리할 필요가 없거나 판단에 실패하면
        원본 전체를 담은 리스트(길이 1)를 반환해서 호출 측이 기존과 동일하게 동작하도록 한다.
        """
        if not conversation.strip():
            return [conversation]

        lines = conversation.split("\n")
        numbered = "\n".join(f"{i}: {line}" for i, line in enumerate(lines))

        topics = ai_client.split_topics(segmentation_prompt, numbered)
        if len(topics) < 2:
            return [conversation]

        start_lines = sorted({
            t["start_line"] for t in topics if 0 <= t["start_line"] < len(lines)
        })
        if len(start_lines) < 2 or start_lines[0] != 0:
            # 분리 지점이 신뢰할 수 없는 형태면 분리를 취소하고 원본 그대로 사용
            return [conversation]

        segments = []
        for i, start in enumerate(start_lines):
            end = start_lines[i + 1] if i + 1 < len(start_lines) else len(lines)
            segment = "\n".join(lines[start:end]).strip()
            if segment:
                segments.append(segment)

        return segments if len(segments) >= 2 else [conversation]

    def _mark_as_series_part(self, content: str, idx: int, total: int) -> str:
        """여러 포스팅으로 분리된 초안에 연재 표시(제목)와 공통 태그를 붙인다"""
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if line.strip().startswith("# "):
                lines[i] = f"{line.rstrip()} (연재 {idx}/{total})"
                break

        tag_pattern = re.compile(r"^(\*\*태그:\*\*\s*)(.+)$")
        for i, line in enumerate(lines):
            match = tag_pattern.match(line.strip())
            if match:
                lines[i] = f"{match.group(1)}{match.group(2)}, 연재"
                break

        return "\n".join(lines)

    def _inject_identity_tags(self, content: str, json_content: str, draft_type: str) -> str:
        """
        협업자가 작성한 커밋/PR에는 작성자 이름을 태그로 결정적으로 주입.

        AI가 "**태그:**" 줄을 만들 때 작성자를 신뢰성 있게 반영해준다는 보장이
        없어서(작성자 구분을 프롬프트로 강제하기 어려움), 소스 JSON의 "작성자"
        필드를 코드에서 직접 읽어 협업자 커밋일 때만 태그로 강제 추가한다.
        서버 사이드 author 필터로 이미 본인 커밋/PR만 수집되므로, 본인 작성
        건에는 "본인"/"커밋" 같은 정보값 없는 태그를 붙이지 않는다.
        algorithm/study는 항상 본인 활동이라 구분이 필요 없으므로 건드리지 않는다.
        """
        if draft_type not in ("dev", "pr"):
            return content

        try:
            data = json.loads(json_content)
        except (json.JSONDecodeError, TypeError):
            return content

        author = data.get("작성자") or ""
        my_username = os.getenv("GITHUB_USERNAME", "")
        is_mine = bool(author) and bool(my_username) and author.lower() == my_username.lower()

        if is_mine:
            return content

        identity_tag = author or "협업"
        new_tags = ["PR", identity_tag] if draft_type == "pr" else [identity_tag]

        lines = content.split("\n")
        tag_pattern = re.compile(r"^(\*\*태그:\*\*\s*)(.+)$")

        for i, line in enumerate(lines):
            match = tag_pattern.match(line.strip())
            if match:
                existing = [t.strip() for t in match.group(2).split(",") if t.strip()]
                for new_tag in new_tags:
                    if new_tag not in existing:
                        existing.append(new_tag)
                lines[i] = f"{match.group(1)}{', '.join(existing)}"
                return "\n".join(lines)

        # AI가 태그 줄을 안 만들었으면 새로 추가
        lines.append(f"**태그:** {', '.join(new_tags)}")
        return "\n".join(lines)

    def _handle_ai_failure(
        self, ai_client: AIClient, draft_type: str, json_file: str, label: str
    ):
        """AI 초안 생성 실패 시 공통 처리 (영구 실패면 이번 실행 나머지를 포기)"""
        if ai_client.last_error_permanent:
            self.quota_exhausted_flag.set()
            slog.draft_failure(draft_type, json_file, "all_ai_providers_permanently_failed")
            self._print(f"    ⚠️  AI API 한도 초과. 나머지 {label} draft 생성 중단")
        else:
            slog.draft_failure(draft_type, json_file, "transient_ai_failure")
            self._print(f"    ⚠️  일시적 오류로 실패, 다음 항목 계속 진행: {json_file}")

    def _source_json_for_draft(self, draft_path: str):
        """draft 파일 경로에서 draft_saver가 저장할 때 쓴 이름 규칙을 거꾸로 풀어
        원본 소스 JSON을 로드. 매칭 안 되면 (None, None)."""
        path = Path(draft_path)
        draft_type = path.parent.name
        subdir = _DRAFT_SOURCE_SUBDIR.get(draft_type)
        if not subdir:
            return None, None

        m = re.match(rf"^{re.escape(draft_type)}_(.+)\.md$", path.name)
        if not m:
            return None, None
        source_name = re.sub(r"_part\d+$", "", m.group(1))

        json_path = Path(__file__).parent.parent / "data" / subdir / f"{source_name}.json"
        if not json_path.exists():
            return None, None
        try:
            return json.loads(json_path.read_text(encoding="utf-8")), draft_type
        except (json.JSONDecodeError, OSError):
            return None, None

    def _draft_body_len(self, draft_path: str) -> int:
        try:
            return len(Path(draft_path).read_text(encoding="utf-8"))
        except OSError:
            return 0

    def _dedupe_dev_pr_drafts(self, all_timed_drafts):
        """
        이번 배치에서 새로 만들어진 dev/pr draft끼리 구조적 중복을 걸러낸다.
        판정 기준은 커밋 메시지 원문 일치(제목 유사도 추측 아님)와, 겹칠 때
        본문이 더 짧은/얕은 쪽을 제외하는 것 — 기존에 이미 올라간 381개 포스트를
        정리할 때 쓴 것과 같은 방법론이다.

        패턴 A: "Merge pull request #N" dev draft와 그 PR#N draft가 같이 있으면
                같은 병합 이벤트를 두 번 설명하는 것이므로 더 짧은 쪽 제외.
        패턴 B: PR draft가 담은 커밋_메시지_목록 중 이번 배치의 다른 dev draft와
                겹치는 게 있으면(즉 이미 개별 포스트가 따로 생김) 롤업 중복으로
                보고, PR이 겹치는 개별 글 중 가장 긴 것보다 짧거나 같으면 제외.
                PR이 더 길면(더 넓은 맥락을 담고 있다는 뜻) 자동으로 지우지 않고
                둘 다 남겨서 사람이 보게 한다.
        """
        dev_entries = []
        pr_entries = []
        passthrough = []
        for ts, path in all_timed_drafts:
            data, draft_type = self._source_json_for_draft(path)
            if draft_type == "dev" and data:
                dev_entries.append((ts, path, data))
            elif draft_type == "pr" and data:
                pr_entries.append((ts, path, data))
            else:
                passthrough.append((ts, path))

        drop = set()

        # 패턴 A
        for ts, path, data in dev_entries:
            fl = _first_line(data.get("커밋_메시지", ""))
            m = _MERGE_PR_NUM_RE.match(fl)
            if not m:
                continue
            pr_num, repo = m.group(1), data.get("레포지토리", "")
            for pts, ppath, pdata in pr_entries:
                if str(pdata.get("PR_번호")) == pr_num and pdata.get("레포지토리") == repo:
                    dev_len = self._draft_body_len(path)
                    pr_len = self._draft_body_len(ppath)
                    loser = path if pr_len >= dev_len else ppath
                    if loser not in drop:
                        drop.add(loser)
                        self._print(f"    중복 제외(같은 머지 이벤트 {repo}#{pr_num}): {Path(loser).name}")
                    break

        # 패턴 B
        dev_msg_to_path = {}
        for ts, path, data in dev_entries:
            fl = _first_line(data.get("커밋_메시지", ""))
            if fl and not _MERGE_MARKER_RE.match(fl):
                dev_msg_to_path[fl] = path

        for ts, path, data in pr_entries:
            if path in drop:
                continue
            overlap_paths = []
            for msg in data.get("커밋_메시지_목록", []):
                fl = _first_line(msg)
                if fl and not _MERGE_MARKER_RE.match(fl):
                    dpath = dev_msg_to_path.get(fl)
                    if dpath and dpath not in overlap_paths:
                        overlap_paths.append(dpath)
            if not overlap_paths:
                continue
            pr_len = self._draft_body_len(path)
            max_individual_len = max(self._draft_body_len(p) for p in overlap_paths)
            if pr_len <= max_individual_len:
                drop.add(path)
                repo = data.get("레포지토리", "")
                pr_num = data.get("PR_번호", "?")
                self._print(
                    f"    중복 제외(롤업 {repo}#{pr_num}, 겹치는 개별 글 {len(overlap_paths)}개): "
                    f"{Path(path).name}"
                )

        kept = [(ts, path) for ts, path in all_timed_drafts if path not in drop]
        return kept

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
